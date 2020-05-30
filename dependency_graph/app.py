import logging
import os.path
import random

from Qt import QtCore, QtWidgets
from pxr import Usd, Sdf

import utils
from vendor.nodz import nodz_main


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
        logger.info('DependencyWalker'.center(40, '-'))
        logger.info('loading usd file: {}'.format(self.usdfile))
        self.nodes = []
        self.edges = []
        self.children = {}
    
    
    def start(self):
        self.nodes = []
        self.edges = []
        
        stage = Usd.Stage.Open(self.usdfile)
        rootLayer = stage.GetRootLayer()
        
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
        # print 'SUBLAYERS'
        # print layer.subLayerPaths
        
        for x in layer.GetExternalReferences():
            print id, os.path.normpath(os.path.join(layer_basepath, x))
            # if you wanna construct a full path yourself
            # you can manually load a SdfLayer like this
            # layer = Sdf.Layer.Find(os.path.normpath(os.path.join(layer_basepath, x)))
            
            # or you can use FindRelativeToLayer to do the dirty work
            # more robust
            sub_layer = Sdf.Layer.FindRelativeToLayer(layer, x)
            if sub_layer:
                count += 1
                child_count = self.walkStageLayers(sub_layer, level=level + 1)
                subfile = os.path.normpath(os.path.join(layer_basepath, x))
                if not subfile in self.nodes:
                    self.nodes.append(subfile)
                self.edges.append([layer_path, subfile])
                self.children[subfile] = child_count
        return count


def find_node(node_coll, attr_name, attr_value):
    for x in node_coll:
        node = node_coll[x]
        if getattr(node, attr_name) == attr_value:
            return node


@QtCore.Slot(str, object)
def on_nodeMoved(nodeName, nodePos):
    print('node {0} moved to {1}'.format(nodeName, nodePos))


class Arranger(object):
    def __init__(self, start_node, hspace=400, vspace=100, ):
        self.voffset = 0
        self.hspace = hspace
        self.vspace = vspace
        
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
        rect = scene.sceneRect()
        
        pad = 300
        rect.setLeft(self.bbmin[0] - pad)
        rect.setBottom(self.bbmin[1] - pad)
        rect.setRight(self.bbmax[0] + pad)
        rect.setTop(self.bbmax[1] + pad)
        scene.setSceneRect(rect)
        
        return pos
    
    
    def get_max_child_count(self, node):
        """
        Maximum
        :param node:
        :return:
        """
        ret = 0
        for conn in node.sockets['ref'].connections:
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
        for i, conn in enumerate(start_node.sockets['ref'].connections):
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


def manualOpen(startPath=None):
    """
    Manual open method for manually opening the manually opened files.
    """
    multipleFilters = "USD Files (*.usd *.usda *.usdc) (*.usd *.usda *.usdc);;All Files (*.*) (*.*)"
    filename = QtWidgets.QFileDialog.getOpenFileName(
        QtWidgets.QApplication.activeWindow(), 'Open File', startPath or '/', multipleFilters,
        None, QtWidgets.QFileDialog.DontUseNativeDialog)
    if filename[0]:
        print filename
        return filename[0]


def main(usdfile):
    usdfile = utils.sanitize_path(usdfile)
    # usdfile = usdfile.encode('unicode_escape')
    # TODO: find proper scene centre
    center = [1000, 1000]
    
    x = DependencyWalker(usdfile)
    x.start()
    win = QtWidgets.QApplication.activeWindow()
    
    dialog = QtWidgets.QDialog(parent=win)
    lay = QtWidgets.QVBoxLayout()
    dialog.setLayout(lay)
    toolBar = QtWidgets.QToolBar()
    lay.addWidget(toolBar)
    
    openAction = QtWidgets.QAction('Open...', dialog)
    openAction.setShortcut('Ctrl+o')
    openAction.triggered.connect(manualOpen)
    
    toolBar.addAction(openAction)
    
    logger.info('building nodes')
    configPath = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'nodz_config.json')
    
    nodz = nodz_main.Nodz(None, configPath=configPath)
    lay.addWidget(nodz)
    nodz.initialize()
    dialog.show()
    
    node_label = os.path.basename(usdfile)
    root_node = nodz.createNode(name=node_label, preset='node_preset_1',
                                position=QtCore.QPointF(center[0] + 400, center[1]))
    nodz.createAttribute(node=root_node, name='ref', index=-1, preset='attr_preset_1',
                         plug=True, socket=True, dataType=int, socketMaxConnections=-1)
    
    nds = []
    for i, node in enumerate(x.nodes):
        # print node
        rnd = random.seed(i)
        
        pos = QtCore.QPointF((random.random() - 0.5) * 1000 + center[0], (random.random() - 0.5) * 1000 + center[1])
        node_label = os.path.basename(node)
        
        if not node_label in nds:
            nodeA = nodz.createNode(name=node_label, preset='node_preset_1', position=pos)
            if nodeA:
                nodz.createAttribute(node=nodeA, name='ref', index=-1, preset='attr_preset_1',
                                     plug=True, socket=True, dataType=int, socketMaxConnections=-1)
            nds.append(node_label)
    nodz.signal_NodeMoved.connect(on_nodeMoved)
    
    node_coll = nodz.scene().nodes
    for edge in x.edges:
        start = os.path.basename(edge[0])
        end = os.path.basename(edge[1])
        nodz.createConnection(end, 'ref', start, 'ref')
    
    Arranger(root_node).arrange()
    
    root_node.scene().updateScene()
