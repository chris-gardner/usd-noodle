import logging
import os.path
import random

from Qt import QtCore, QtWidgets, QtGui
from pxr import Usd, Sdf, Ar

import utils
# from vendor.nodz import nodz_main
import derp
reload(derp)

logger = logging.getLogger('usd-dependency-graph')
logger.setLevel(logging.DEBUG)
if not len(logger.handlers):
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    logger.addHandler(ch)
logger.propagate = False


class DependencyWalker(object):
    def __init__(self, usdfile):
        self.usdfile = usdfile
        self.stage = None
        
        logger.info('DependencyWalker'.center(40, '-'))
        logger.info('loading usd file: {}'.format(self.usdfile))
        self.nodes = []
        self.edges = []
        self.children = {}
    
    
    def start(self):
        self.nodes = []
        self.edges = []
        self.stage = None
        
        self.stage = Usd.Stage.Open(self.usdfile)
        rootLayer = self.stage.GetRootLayer()
        
        self.walkStageLayers(rootLayer)
    
    
    def walkStageLayers(self, layer, level=1):
        """
        Recursive function to loop through a layer's external references
        
        :param layer: SdfLayer
        :param level: current recursion depth
        """
        
        id = '-' * (level)
        layer_path = layer.realPath
        # print id, 'layer: ', layer_path
        layer_basepath = os.path.dirname(layer_path)
        # print id, 'references:'
        
        count = 0
        
        for ref in layer.GetExternalReferences():
            print id, os.path.normpath(os.path.join(layer_basepath, ref))
            if self.stage.IsLayerMuted(ref):
                print 'muted layer'
            
            # if you wanna construct a full path yourself
            # you can manually load a SdfLayer like this
            # layer = Sdf.Layer.Find(os.path.normpath(os.path.join(layer_basepath, x)))
            
            # or you can use FindRelativeToLayer to do the dirty work
            # more robust
            sub_layer = Sdf.Layer.FindRelativeToLayer(layer, ref)
            if sub_layer:
                
                child_count = self.walkStageLayers(sub_layer, level=level + 1)
                subfile = os.path.normpath(os.path.join(layer_basepath, ref))
                if not subfile in self.nodes:
                    count += 1
                    self.nodes.append(subfile)
                if not [layer_path, subfile] in self.edges:
                    self.edges.append([layer_path, subfile])
                self.children[subfile] = child_count
            else:
                print "NOT ONLINE", ref
        
        print 'SUBLAYERS'
        print layer.subLayerPaths
        for ref in layer.subLayerPaths:
            if self.stage.IsLayerMuted(ref):
                print 'muted layer'
            sub_layer = Sdf.Layer.FindRelativeToLayer(layer, ref)
            if sub_layer:
                child_count = self.walkStageLayers(sub_layer, level=level + 1)
                subfile = os.path.normpath(os.path.join(layer_basepath, ref))
                if not subfile in self.nodes:
                    count += 1
                    self.nodes.append(subfile)
                if not [layer_path, subfile] in self.edges:
                    self.edges.append([layer_path, subfile])
                self.children[subfile] = child_count
            else:
                print "NOT ONLINE", ref
        
        return count
    
    
    def layerprops(self, layer):
        print 'layer props'.center(40, '-')
        
        for prop in ['anonymous', 'colorConfiguration', 'colorManagementSystem', 'comment', 'customLayerData',
                     'defaultPrim', 'dirty', 'documentation', 'empty', 'endTimeCode', 'expired', 'externalReferences',
                     'fileExtension', 'framePrecision',
                     'framesPerSecond', 'hasOwnedSubLayers', 'identifier', 'owner', 'permissionToEdit',
                     'permissionToSave', 'pseudoRoot', 'realPath', 'repositoryPath', 'rootPrimOrder', 'rootPrims',
                     'sessionOwner', 'startTimeCode', 'subLayerOffsets', 'subLayerPaths', 'timeCodesPerSecond',
                     'version']:
            print prop, getattr(layer, prop)
        print ''.center(40, '-')
        
        defaultprim = layer.defaultPrim
        if defaultprim:
            print defaultprim, type(defaultprim)


def find_node(node_coll, attr_name, attr_value):
    for x in node_coll:
        node = node_coll[x]
        if getattr(node, attr_name) == attr_value:
            return node


@QtCore.Slot(str, object)
def on_nodeMoved(nodeName, nodePos):
    print('node {0} moved to {1}'.format(nodeName, nodePos))


class Arranger(object):
    def __init__(self, start_node, scene, hspace=400, vspace=100, padding=300):
        self.voffset = 0
        self.hspace = hspace
        self.vspace = vspace
        self.padding = padding
        
        self.start_node = start_node
        self.scene = scene
        
        rect = self.scene.sceneRect()
        self.cx = rect.right()
        self.cy = rect.bottom()
        
        self.bbmin = [999999999, 999999999]
        self.bbmax = [-999999999, -999999999]
        
        self.visited_nodes = []
    
    
    def arrange(self):
        self.visited_nodes = []
        
        pos = self.adjuster(self.start_node)
        
        
        # gotta adjust the scene bounding box to fit all the nodes in
        # plus some padding around it
        rect = self.scene.sceneRect()
        rect.setLeft(self.bbmin[0] - self.padding)
        rect.setBottom(self.bbmin[1] - self.padding)
        rect.setRight(self.bbmax[0] + self.padding)
        rect.setTop(self.bbmax[1] + self.padding)
        self.scene.setSceneRect(rect)
        
        # updateScene() forces the graph edges to redraw after the nodes have been moved
        #self.scene.updateScene()
        
        return pos
    

    
    def adjust_bbox(self, pos):
        if pos.x() < self.bbmin[0]:
            self.bbmin[0] = pos.x()
        if pos.x() > self.bbmax[0]:
            self.bbmax[0] = pos.x()
        
        if pos.y() < self.bbmin[1]:
            self.bbmin[1] = pos.y()
        if pos.y() > self.bbmax[1]:
            self.bbmax[1] = pos.y()
    
    
    def adjuster(self, start_node, depth=0):
        
        start_voffset = self.voffset
        connected_nodes = []
        
        for i, edge in enumerate(start_node.dest_edges):
            source_node = edge.source
            connected_nodes.append(source_node)
        
        if connected_nodes:
            # it has children. average it's position vertically
            avg = 0
            for node in connected_nodes:
                if node not in self.visited_nodes:
                    avg += self.adjuster(node, depth=depth + 1)
                    self.visited_nodes.append(node)
            avg /= len(connected_nodes)
            
            if len(connected_nodes) == 1:
                # if just one child node, copy the vertical position
                pos = QtCore.QPointF(self.cx - depth * self.hspace, connected_nodes[0].pos().y())
            else:
                # more than one child - use the average
                pos = QtCore.QPointF(self.cx - depth * self.hspace, self.cy - avg * self.vspace)
            
            start_node.setPos(pos)
            self.adjust_bbox(pos)
        
        else:
            if start_node not in self.visited_nodes:
                # nothing connected. stack it's position vertically
                pos = QtCore.QPointF(self.cx - depth * self.hspace, self.cy - (self.voffset) * self.vspace)
                start_node.setPos(pos)
                self.voffset += 1
                self.adjust_bbox(pos)
                self.visited_nodes.append(start_node)
        
        # if depth == 0:
        #     # redraw all the connections and stuff
        #     start_node.scene().updateScene()
        
        return start_voffset + (self.voffset - start_voffset) * 0.5


class NodeGraphWindow(QtWidgets.QDialog):
    def __init__(self, usdfile=None, parent=None):
        self.usdfile = usdfile
        self.root_node = None
        
        super(NodeGraphWindow, self).__init__(parent)
        self.settings = QtCore.QSettings("chrisg", "usd-dependency-graph")
        
        self.build_ui()
        if self.usdfile:
            self.load_file()
    
    
    def build_ui(self):
        
        if self.settings.value("geometry"):
            self.restoreGeometry(self.settings.value("geometry"))
        else:
            self.resize(600, 400)
        
        lay = QtWidgets.QVBoxLayout()
        self.setLayout(lay)
        self.toolBar = QtWidgets.QToolBar('Main')
        self.toolBar.setToolButtonStyle(QtCore.Qt.ToolButtonTextOnly)
        lay.addWidget(self.toolBar)
        
        openAction = QtWidgets.QAction('Open...', self)
        openAction.setShortcut('Ctrl+o')
        openAction.triggered.connect(self.manualOpen)
        
        self.toolBar.addAction(openAction)
        
        logger.info('building nodes')
        configPath = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'nodz_config.json')
        
        # self.nodz = nodz_main.Nodz(None, configPath=configPath)
        # lay.addWidget(self.nodz)
        # self.nodz.initialize()
        self.nodegraph = derp.ViewClass()
        lay.addWidget(self.nodegraph)
    
    
    def load_file(self):
        
        if not os.path.isfile(self.usdfile):
            raise RuntimeError("Cannot find file: %s" % self.usdfile)
        
        derp_scene = self.nodegraph.scene
        
        #self.nodz.clearGraph()
        self.root_node = None
        self.setWindowTitle(self.usdfile)
        
        x = DependencyWalker(self.usdfile)
        x.start()
        
        # nodz_scene = self.nodz.scene()
        # rect = nodz_scene.sceneRect()
        # center = [rect.center().x(), rect.center().y()]
        center = [500, 500]
        node_label = os.path.basename(self.usdfile)
        # self.root_node = self.nodz.createNode(name=node_label, preset='node_preset_1',
        #                                       position=QtCore.QPointF(center[0] + 400, center[1]))
        # self.nodz.createAttribute(node=self.root_node, name='layers', index=-1, preset='attr_preset_1',
        #                           plug=True, socket=True, dataType=int, socketMaxConnections=-1)
        # self.nodz.createAttribute(node=self.root_node, name='clips', index=-1, preset='attr_preset_2',
        #                           plug=True, socket=True, dataType=int, socketMaxConnections=-1)
        # self.nodz.createAttribute(node=self.root_node, name='poo', index=0, preset='attr_preset_2',
        #                           plug=False, socket=False)
        
        self.root_node = derp.Node(title=node_label, filepath=self.usdfile)
        derp_scene.addItem(self.root_node)
        derp_scene.nodeColl.append(self.root_node)
        
        nds = []
        for i, node in enumerate(x.nodes):
            # print node
            rnd = random.seed(i)
            
            pos = QtCore.QPointF((random.random() - 0.5) * 1000 + center[0],
                                 (random.random() - 0.5) * 1000 + center[1])
            node_label = os.path.basename(node)
            
            if not node in nds:
                #print 'adding node', node_label, node
                node = derp.Node(title=node_label, filepath=node)
                derp_scene.addItem(node)
                derp_scene.nodeColl.append(node)
    
        
        # create all the node connections
        for edge in x.edges:
            start = os.path.basename(edge[0])
            end = os.path.basename(edge[1])
            start_node = self.findNode(edge[0])
            end_node = self.findNode(edge[1])
            print start_node, end_node
            
            edge = derp.Edge(end_node, start_node, scene=derp_scene)
            derp_scene.addItem(edge)
            derp_scene.edgeColl.append(edge)
            end_node.source_edges.append(edge)
            start_node.dest_edges.append(edge)

        # layout nodes!
        Arranger(self.root_node, derp_scene).arrange()


    def findNode(self, filepath):
        derp_scene = self.nodegraph.scene

        for sceneNode in derp_scene.nodeColl:
            #print sceneNode, filepath
            if sceneNode.filepath == filepath:
                return sceneNode


    def manualOpen(self):
        """
        Manual open method for manually opening the manually opened files.
        """
        startPath = None
        if self.usdfile:
            startPath = os.path.dirname(self.usdfile)
        
        multipleFilters = "USD Files (*.usd *.usda *.usdc) (*.usd *.usda *.usdc);;All Files (*.*) (*.*)"
        filename = QtWidgets.QFileDialog.getOpenFileName(
            QtWidgets.QApplication.activeWindow(), 'Open File', startPath or '/', multipleFilters,
            None, QtWidgets.QFileDialog.DontUseNativeDialog)
        if filename[0]:
            print filename[0]
            self.usdfile = filename[0]
            self.load_file()
    
    
    def closeEvent(self, *args, **kwargs):
        """
        Window close event. Saves preferences. Impregnates your dog.
        """
        
        self.settings.setValue("geometry", self.saveGeometry())
        super(NodeGraphWindow, self).closeEvent(*args)


def main(usdfile=None):
    # usdfile = utils.sanitize_path(usdfile)
    # usdfile = usdfile.encode('unicode_escape')
    
    par = QtWidgets.QApplication.activeWindow()
    win = NodeGraphWindow(usdfile=usdfile, parent=par)
    win.show()


def test(usdfile):
    print 'test'.center(40, '-')
    stage = Usd.Stage.Open(usdfile)
    
    for prim in stage.Traverse():
        print(prim.GetPath())
        
        """
        this doesn't quite work
        https://groups.google.com/d/msg/usd-interest/s4AM0v60uBI/sYltgp7OAgAJ
        """
        if prim.HasPayload():
            print 'payloads'.center(40, '-')
            # this is apparently hacky, but it works, yah?
            # https://groups.google.com/d/msg/usd-interest/s4AM0v60uBI/q-okjU2RCAAJ
            payloads = prim.GetMetadata("payload")
            # so there's lots of lists
            for x in dir(payloads):
                if x.endswith('Items'):
                    print x, getattr(payloads, x)
            
            for payload in payloads.appendedItems:
                pathToResolve = payload.assetPath
                print 'assetPath:', pathToResolve
                primSpec = prim.GetPrimStack()[0]
                # get the layer from the prim
                anchorPath = primSpec.layer.identifier
                
                with Ar.ResolverContextBinder(stage.GetPathResolverContext()):
                    resolver = Ar.GetResolver()
                    # relative to layer path?
                    pathToResolve = resolver.AnchorRelativePath(anchorPath, pathToResolve)
                    print 'pathToResolve', pathToResolve
                    
                    # this should probably work, but no
                    resolvedPath = resolver.Resolve(pathToResolve)
                    print 'resolvedPath', resolvedPath
        
        if prim.HasAuthoredPayloads():
            payloads = prim.GetPayloads()
            # print payloads
            """
            There is currently no facility for listing the currently authored payloads on a prim...
            the problem is somewhat ill-defined, and requires some thought.
            """
        
        # does this prim have variant sets?
        if prim.HasVariantSets():
            print 'variantsets'.center(30, '-')
            
            # list all the variant sets avalable on this prim
            sets = prim.GetVariantSets()
            
            # you can't iterate over the sets.
            # you have to get the name and do a GetVariantSet(<<set name>>)
            # TypeError: 'VariantSets' object is not iterable
            # maybe USD 20?
            for varset in sets.GetNames():
                print 'variant set name:', varset
                # get the variant set by name
                thisvarset = prim.GetVariantSet(varset)
                
                # the available variants
                print thisvarset.GetVariantNames()
                # the current variant
                print thisvarset.GetVariantSelection()
                print varset
        
        # gotta get a clip on each prim and then test it for paths?
        clips = Usd.ClipsAPI(prim)
        if clips.GetClipAssetPaths():
            print 'CLIPS'.center(30, '-')
            # dict of clip info. full of everything
            # key is the clip *name*
            print clips.GetClips()
            # this is a good one - resolved asset paths too
            for path in clips.GetClipAssetPaths():
                print path, type(path)
                print path.resolvedPath
    
    print 'end test'.center(40, '-')
