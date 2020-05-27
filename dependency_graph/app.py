from vendor.nodz import nodz_main
from Qt import QtCore, QtWidgets
import hou

import sys
from pxr import Usd, UsdUtils, Sdf, Ar
import os.path
import logging
import random


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
        logger.info('usd file: {}'.format(self.usdfile))
        self.nodes = []
        self.edges = []
    
    
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
        for x in layer.GetExternalReferences():
            print id, os.path.normpath(os.path.join(layer_basepath, x))
            # if you wanna construct a full path yourself
            # you can manually load a SdfLayer like this
            # layer = Sdf.Layer.Find(os.path.normpath(os.path.join(layer_basepath, x)))
            
            # or you can use FindRelativeToLayer to do the dirty work
            # more robust
            sub_layer = Sdf.Layer.FindRelativeToLayer(layer, x)
            if sub_layer:
                self.walkStageLayers(sub_layer, level=level + 1)
                subfile = os.path.normpath(os.path.join(layer_basepath, x))
                if not subfile in self.nodes:
                    self.nodes.append(subfile)
                self.edges.append([layer_path, subfile])
    
    
    def getRefs(self, layer, stage, level=0, parent=None):
        """
        yes, it's real nasty. but it fucking works for now.
        
        :param layer:
        :param stage:
        :return:
        """
        # number of sublayers this ref has
        refcount = 0
        
        for y, ref in enumerate(layer.GetExternalReferences()):
            
            subfile = stage.ResolveIdentifierToEditTarget(ref)
            refcount += 1
            
            if os.path.isfile(subfile):
                if not subfile in self.nodes:
                    # logger.debug('{} {}'.format(('-' * level), subfile))
                    
                    dir, filename = os.path.split(subfile)
                    
                    substage = Usd.Stage.Open(subfile)
                    sublayers = substage.GetLayerStack(includeSessionLayers=False)
                    if sublayers:
                        for sublayer in sublayers:
                            logger.debug('{} layer: {}'.format(('-' * level), sublayer))
                            
                            c = self.getRefs(sublayer, substage, level=level + 1, parent=subfile)
                    self.nodes.append(subfile)
                self.edges.append([parent, subfile])
        return refcount


def find_node(node_coll, attr_name, attr_value):
    for x in node_coll:
        node = node_coll[x]
        if getattr(node, attr_name) == attr_value:
            return node


@QtCore.Slot(str, object)
def on_nodeMoved(nodeName, nodePos):
    print('node {0} moved to {1}'.format(nodeName, nodePos))


def arrange(start_node, depth=0):
    center = [1000, 1000]
    
    for conn in start_node.sockets['ref'].connections:
        node_coll = [x for x in start_node.scene().nodes.values() if x.name == conn.plugNode]
        connected_node = node_coll[0]
        
        pos = QtCore.QPointF(center[0] - depth * 400, center[1])
        connected_node.setPos(pos)
        print conn.plugNode, connected_node.name, depth
        arrange(connected_node, depth=depth + 1)


def main(usdfile):
    center = [1000, 1000]
    x = DependencyWalker(usdfile)
    x.start()
    
    win = hou.qt.mainWindow()
    
    dialog = QtWidgets.QDialog(parent=win)
    lay = QtWidgets.QHBoxLayout()
    dialog.setLayout(lay)
    
    print 'starting'
    nodz = nodz_main.Nodz(None)
    lay.addWidget(nodz)
    nodz.initialize()
    dialog.show()
    
    node_label = os.path.basename(usdfile)
    root_node = nodz.createNode(name=node_label, preset='node_preset_1',
                                position=QtCore.QPointF(center[0] + 400, center[1]))
    nodz.createAttribute(node=root_node, name='ref', index=-1, preset='attr_preset_1',
                         plug=True, socket=True, dataType=int, socketMaxConnections=-1)
    
    for i, node in enumerate(x.nodes):
        # print node
        rnd = random.seed(i)
        
        pos = QtCore.QPointF((random.random() - 0.5) * 1000 + center[0], (random.random() - 0.5) * 1000 + center[1])
        node_label = os.path.basename(node)
        
        nodeA = nodz.createNode(name=node_label, preset='node_preset_1', position=pos)
        nodeA.fuck = node
        nodz.createAttribute(node=nodeA, name='ref', index=-1, preset='attr_preset_1',
                             plug=True, socket=True, dataType=int, socketMaxConnections=-1)
    
    nodz.signal_NodeMoved.connect(on_nodeMoved)
    
    node_coll = nodz.scene().nodes
    for edge in x.edges:
        start = os.path.basename(edge[0])
        end = os.path.basename(edge[1])
        nodz.createConnection(end, 'ref', start, 'ref')
    
    # loop over ref socket connections
    # for conn in root_node.sockets['ref'].connections:
    #     print conn.plugNode
    # arrange(root_node)
