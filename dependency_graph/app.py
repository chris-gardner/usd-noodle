import logging
import os.path
import random
import fnmatch
from functools import partial

from Qt import QtCore, QtWidgets, QtGui
from pxr import Usd, Sdf, Ar

import utils
from vendor.nodz import nodz_main
from . import text_view

import re


digitSearch = re.compile(r'\b\d+\b')

reload(text_view)

reload(nodz_main)

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
        self.nodes = {}
        self.edges = []
    
    
    def start(self):
        self.nodes = {}
        self.edges = []
        self.stage = None
        
        self.stage = Usd.Stage.Open(self.usdfile)
        rootLayer = self.stage.GetRootLayer()
        
        info = {}
        info['mute'] = False
        info['online'] = os.path.isfile(self.usdfile)
        info['path'] = self.usdfile
        info['type'] = 'layer'
        self.nodes[self.usdfile] = info
        
        self.walkStageLayers(rootLayer)
        self.walkStagePrims(self.usdfile)
    
    
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
        # print 'refs', layer.GetExternalReferences()
        count = 0
        
        for ref in layer.GetExternalReferences():
            if not ref:
                # sometimes a ref can be a zero length string. whyyyyyyyyy?
                # seeing this in multiverse esper_room example
                continue
            
            refpath = os.path.normpath(os.path.join(layer_basepath, ref))
            # print id, refpath
            # if self.stage.IsLayerMuted(ref):
            #     print 'muted layer'
            # print 'anon?', Sdf.Layer.IsAnonymousLayerIdentifier(ref)
            
            # if you wanna construct a full path yourself
            # you can manually load a SdfLayer like this
            sub_layer = Sdf.Layer.Find(refpath)
            
            # or you can use FindRelativeToLayer to do the dirty work
            # seems to operate according to the composition rules (variants blah blah)
            # ie, it *may* not return a layer if the stage is set to not load that layer
            # sub_layer = Sdf.Layer.FindRelativeToLayer(layer, ref)
            
            online = True
            if sub_layer:
                child_count = self.walkStageLayers(sub_layer, level=level + 1)
            if not os.path.isfile(refpath):
                online = False
                # print "NOT ONLINE", ref
            
            if not refpath in self.nodes:
                count += 1
                info = {}
                info['mute'] = self.stage.IsLayerMuted(ref)
                info['online'] = online
                info['path'] = refpath
                info['type'] = 'layer'
                
                self.nodes[refpath] = info
            
            if not [layer_path, refpath] in self.edges:
                self.edges.append([layer_path, refpath])
        
        # print 'SUBLAYERS'
        # print layer.subLayerPaths
        for ref in layer.subLayerPaths:
            if not ref:
                # going to guard against zero length strings here too
                continue
            
            refpath = os.path.normpath(os.path.join(layer_basepath, ref))
            
            # if self.stage.IsLayerMuted(ref):
            #     print 'muted layer'
            sub_layer = Sdf.Layer.Find(refpath)
            online = True
            if sub_layer:
                child_count = self.walkStageLayers(sub_layer, level=level + 1)
            if not os.path.isfile(refpath):
                online = False
                # print "NOT ONLINE", ref
            
            if not refpath in self.nodes:
                count += 1
                info = {}
                info['mute'] = self.stage.IsLayerMuted(ref)
                info['online'] = online
                info['path'] = refpath
                info['type'] = 'sublayer'
                
                self.nodes[refpath] = info
            
            if not [layer_path, refpath] in self.edges:
                self.edges.append([layer_path, refpath])
        
        return count
    
    
    def walkStagePrims(self, usdfile):
        # print 'test'.center(40, '-')
        stage = Usd.Stage.Open(usdfile)
        
        for prim in stage.Traverse():
            # print(prim.GetPath())
            
            """
            this doesn't quite work
            https://groups.google.com/d/msg/usd-interest/s4AM0v60uBI/sYltgp7OAgAJ
            """
            if prim.HasPayload():
                # print 'payloads'.center(40, '-')
                # this is apparently hacky, but it works, yah?
                # https://groups.google.com/d/msg/usd-interest/s4AM0v60uBI/q-okjU2RCAAJ
                payloads = prim.GetMetadata("payload")
                # so there's lots of lists that end in "items"
                # probably better to access them manually
                for x in dir(payloads):
                    if x.endswith('Items'):
                        pass
                
                for payload in payloads.appendedItems:
                    pathToResolve = payload.assetPath
                    # print 'assetPath:', pathToResolve
                    primSpec = prim.GetPrimStack()[0]
                    # get the layer from the prim
                    anchorPath = primSpec.layer.identifier
                    
                    with Ar.ResolverContextBinder(stage.GetPathResolverContext()):
                        resolver = Ar.GetResolver()
                        # relative to layer path?
                        pathToResolve = resolver.AnchorRelativePath(anchorPath, pathToResolve)
                        # print 'pathToResolve', pathToResolve
                        
                        # this should probably work, but no
                        resolvedPath = resolver.Resolve(pathToResolve)
                        # print 'resolvedPath', resolvedPath
                        if resolvedPath:
                            # sometimes the resolved paths are zero length strings
                            if not resolvedPath in self.nodes:
                                info = {}
                                info['online'] = os.path.isfile(resolvedPath)
                                info['path'] = resolvedPath
                                info['type'] = 'payload'
                                
                                self.nodes[resolvedPath] = info
                            
                            if not [anchorPath, resolvedPath] in self.edges:
                                self.edges.append([anchorPath, resolvedPath])
            
            # does this prim have variant sets?
            if prim.HasVariantSets():
                # print 'variantsets'.center(30, '-')
                
                # list all the variant sets avalable on this prim
                sets = prim.GetVariantSets()
                
                # you can't iterate over the sets.
                # you have to get the name and do a GetVariantSet(<<set name>>)
                # TypeError: 'VariantSets' object is not iterable
                # maybe USD 20?
                for varset in sets.GetNames():
                    # print 'variant set name:', varset
                    # get the variant set by name
                    thisvarset = prim.GetVariantSet(varset)
                    
                    # the available variants
                    # print thisvarset.GetVariantNames()
                    # the current variant
                    # print thisvarset.GetVariantSelection()
                    # print varset
            
            # gotta get a clip on each prim and then test it for paths?
            clips = Usd.ClipsAPI(prim)
            if clips.GetClipAssetPaths():
                # print 'CLIPS'.center(30, '-')
                # dict of clip info. full of everything
                # key is the clip *name*
                clip_dict = clips.GetClips()
                # print clip_dict
                
                # don't use resolved path in case either the first or last file is missing from disk
                firstFile = str(clips.GetClipAssetPaths()[0].path)
                lastFile = str(clips.GetClipAssetPaths()[-1].path)
                firstFileNum = digitSearch.findall(firstFile)[-1]
                lastFileNum = digitSearch.findall(lastFile)[-1]
                digitRange = str(firstFileNum + '-' + lastFileNum)
                nodeName = ''
                
                firstFileParts = firstFile.split(firstFileNum)
                for i in range(len(firstFileParts) - 1):
                    nodeName += str(firstFileParts[i])
                
                nodeName += digitRange
                nodeName += firstFileParts[-1]
                
                allFilesFound = True
                for path in clips.GetClipAssetPaths():
                    if (path.resolvedPath == ''):
                        allFilesFound = False
                        break
                
                # TODO : make more efficient - looping over everything currently
                # TODO: validate presence of all files in the clip seq. bg thread?
                
                # print 'GetClipManifestAssetPath', clips.GetClipManifestAssetPath().resolvedPath
                # this is a good one - resolved asset paths too
                for path in clips.GetClipAssetPaths():
                    # print path, type(path)
                    # print path.resolvedPath
                    
                    layer = clips.GetClipManifestAssetPath().resolvedPath
                    if not nodeName in self.nodes:
                        info = {}
                        info['online'] = allFilesFound
                        info['path'] = nodeName
                        info['type'] = 'clip'
                        
                        self.nodes[nodeName] = info
                    
                    if not [layer, nodeName] in self.edges:
                        self.edges.append([layer, nodeName])
        
        # print 'end test'.center(40, '-')
    
    
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
    def __init__(self, start_node, hspace=400, vspace=100, padding=300):
        self.voffset = 0
        self.hspace = hspace
        self.vspace = vspace
        self.padding = padding
        
        self.start_node = start_node
        
        rect = start_node.scene().sceneRect()
        self.cx = rect.right()
        self.cy = rect.bottom()
        
        self.bbmin = [999999999, 999999999]
        self.bbmax = [-999999999, -999999999]
        
        self.visited_nodes = []
    
    
    def arrange(self):
        self.visited_nodes = []
        
        pos = self.adjuster(self.start_node)
        
        scene = self.start_node.scene()
        
        # gotta adjust the scene bounding box to fit all the nodes in
        for node in self.visited_nodes:
            node.checkIsWithinSceneRect()
        
        # updateScene() forces the graph edges to redraw after the nodes have been moved
        scene.updateScene()
        
        return pos
    
    
    def get_max_child_count(self, node):
        """
        Maximum
        :param node:
        :return:
        """
        ret = 0
        for conn in node.sockets['layers'].connections:
            ret += 1
            node_coll = [x for x in node.scene().nodes.values() if x.name == conn.plugNode]
            connected_node = node_coll[0]
            
            ret += self.get_max_child_count(connected_node)
        
        return ret
    
    
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
        for i, conn in enumerate(start_node.sockets['layers'].connections):
            node_coll = [x for x in start_node.scene().nodes.values() if x.name == conn.plugNode]
            connected_nodes.append(node_coll[0])
        for i, conn in enumerate(start_node.sockets['clips'].connections):
            node_coll = [x for x in start_node.scene().nodes.values() if x.name == conn.plugNode]
            connected_nodes.append(node_coll[0])
        
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
        
        if depth == 0:
            # redraw all the connections and stuff
            start_node.scene().updateScene()
        
        return start_voffset + (self.voffset - start_voffset) * 0.5


class FindNodeWindow(QtWidgets.QDialog):
    def __init__(self, nodz, parent=None):
        self.nodz = nodz
        super(FindNodeWindow, self).__init__(parent)
        self.setWindowFlags(QtCore.Qt.Tool | QtCore.Qt.WindowStaysOnTopHint)
        
        self.build_ui()
    
    
    def search(self):
        search_text = self.searchTxt.text()
        
        self.foundNodeList.clear()
        if search_text == '':
            return
        
        for x in self.nodz.scene().nodes:
            if fnmatch.fnmatch(x.lower(), '*%s*' % search_text.lower()):
                self.foundNodeList.addItem(QtWidgets.QListWidgetItem(x))
    
    
    def item_selected(self, *args):
        items = self.foundNodeList.selectedItems()
        if items:
            sel = [x.text() for x in items]
            
            for x in self.nodz.scene().nodes:
                node = self.nodz.scene().nodes[x]
                if x in sel:
                    node.setSelected(True)
                else:
                    node.setSelected(False)
            self.nodz._focus()
    
    
    def build_ui(self):
        lay = QtWidgets.QVBoxLayout()
        self.setLayout(lay)
        self.searchTxt = QtWidgets.QLineEdit()
        self.searchTxt.textChanged.connect(self.search)
        lay.addWidget(self.searchTxt)
        
        self.foundNodeList = QtWidgets.QListWidget()
        self.foundNodeList.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.foundNodeList.itemSelectionChanged.connect(self.item_selected)
        lay.addWidget(self.foundNodeList)


class NodeGraphWindow(QtWidgets.QDialog):
    def __init__(self, usdfile=None, parent=None):
        self.usdfile = usdfile
        self.root_node = None
        
        super(NodeGraphWindow, self).__init__(parent)
        self.settings = QtCore.QSettings("chrisg", "usd-dependency-graph")
        
        self.nodz = None
        
        self.find_win = None
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
        
        findAction = QtWidgets.QAction('Find...', self)
        findAction.setShortcut('Ctrl+F')
        findAction.triggered.connect(self.findWindow)
        self.toolBar.addAction(findAction)
        
        logger.info('building nodes')
        configPath = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'nodz_config.json')
        
        self.nodz = nodz_main.Nodz(None, configPath=configPath)
        # self.nodz.editEnabled = False
        lay.addWidget(self.nodz)
        self.nodz.initialize()
        self.nodz.signal_NodeMoved.connect(on_nodeMoved)
        self.nodz.signal_NodeContextMenuEvent.connect(self.node_context_menu)
    
    
    def findWindow(self):
        if self.find_win:
            self.find_win.close()
        
        self.find_win = FindNodeWindow(self.nodz, parent=self)
        self.find_win.show()
    
    
    def get_node_from_name(self, node_name):
        return self.nodz.scene().nodes[node_name]
    
    
    def node_path(self, node_name):
        node = self.get_node_from_name(node_name)
        userdata = node.userData
        print userdata.get('path')
    
    
    def view_usdfile(self, node_name):
        node = self.get_node_from_name(node_name)
        userdata = node.userData
        path = userdata.get('path')
        if path.endswith(".usda"):
            win = text_view.TextViewer(path, parent=self)
            win.show()
        else:
            print 'can only view usd ascii files'
    
    
    def node_context_menu(self, event, node):
        menu = QtWidgets.QMenu()
        menu.addAction("print path", partial(self.node_path, node))
        menu.addAction("View USD file...", partial(self.view_usdfile, node))
        
        menu.exec_(event.globalPos())
    
    
    def load_file(self):
        
        if not os.path.isfile(self.usdfile):
            raise RuntimeError("Cannot find file: %s" % self.usdfile)
        
        self.nodz.clearGraph()
        self.root_node = None
        self.setWindowTitle(self.usdfile)
        
        x = DependencyWalker(self.usdfile)
        x.start()
        
        nodz_scene = self.nodz.scene()
        rect = nodz_scene.sceneRect()
        center = [rect.center().x(), rect.center().y()]
        
        nds = []
        for i, node in enumerate(x.nodes):
            
            info = x.nodes[node]
            # print node
            rnd = random.seed(i)
            
            pos = QtCore.QPointF((random.random() - 0.5) * 1000 + center[0],
                                 (random.random() - 0.5) * 1000 + center[1])
            node_label = os.path.basename(node)
            
            if not node_label in nds:
                nodeA = self.nodz.createNode(name=node_label, preset='node_preset_1', position=pos)
                if self.usdfile == node:
                    self.root_node = nodeA
                
                if nodeA:
                    self.nodz.createAttribute(node=nodeA, name='out', index=0, preset='attr_preset_1',
                                              plug=True, socket=False, dataType=int, socketMaxConnections=-1)
                    
                    self.nodz.createAttribute(node=nodeA, name='layers', index=-1, preset='attr_preset_1',
                                              plug=False, socket=True, dataType=int, socketMaxConnections=-1)
                    self.nodz.createAttribute(node=nodeA, name='clips', index=-1, preset='attr_preset_3',
                                              plug=False, socket=True, dataType=int, socketMaxConnections=-1)
                    nodeA.userData = info
                    
                    if info['online'] is False:
                        self.nodz.createAttribute(node=nodeA, name='OFFLINE', index=0, preset='attr_preset_2',
                                                  plug=False, socket=False)
                
                nds.append(node_label)
        
        # print x.nodes.keys()
        # print 'wiring nodes'.center(40, '-')
        # create all the node connections
        for edge in x.edges:
            start = os.path.basename(edge[0])
            node_type = x.nodes[edge[1]].get("type", "layer")
            # print 'node_type', node_type
            port = 'layers'
            if node_type == 'clip':
                port = 'clips'
            elif node_type == ' payload':
                port = 'payloads'
            end = os.path.basename(edge[1])
            self.nodz.createConnection(end, 'out', start, port)
        
        # layout nodes!
        Arranger(self.root_node, vspace=150).arrange()
        # self.nodz.autoLayoutGraph()
        self.nodz._focus()
    
    
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
        if self.find_win:
            self.find_win.close()
        
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
    
    print 'GetUsedLayers'.center(40, '-')
    # things that are in use, apparntly
    for x in stage.GetUsedLayers(includeClipLayers=True):
        print x
    
    print 'stage.Traverse'.center(40, '-')
    for prim in stage.Traverse():
        print(prim.GetPath())
        
        """Return a list of PrimSpecs that provide opinions for this prim (i.e.
        the prim's metadata fields, including composition metadata).
         specs are ordered from strongest to weakest opinion."""
        # print prim.GetPrimStack()
        
        if prim.HasAuthoredReferences():
            primSpec = stage.GetEditTarget().GetPrimSpecForScenePath(prim.GetPath())
            if primSpec:
                refList = primSpec.referenceList
                if refList:
                    print 'referenceList'.center(40, '-')
                    for ref in refList.GetAddedOrExplicitItems():
                        if ref.assetPath:
                            print ref.assetPath
        
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
