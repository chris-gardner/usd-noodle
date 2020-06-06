#!/usr/bin/env python
# coding: utf-8

from Qt import QtGui, QtCore, QtWidgets

import math
import os

rad = 50


class WindowClass(QtWidgets.QMainWindow):
    def __init__(self, parent):
        super(WindowClass, self).__init__(parent)
        self.view = ViewClass()
        self.setCentralWidget(self.view)


class DialogClass(QtWidgets.QDialog):
    def __init__(self, parent):
        super(DialogClass, self).__init__(parent)
        self.view = ViewClass()
        self.centralLayout = QtWidgets.QVBoxLayout(self)
        self.centralLayout.setContentsMargins(0, 0, 0, 0)
        self.centralLayout.addWidget(self.view)


class ViewClass(QtWidgets.QGraphicsView):
    def __init__(self, scene=None):
        super(ViewClass, self).__init__()
        
        # Mouse Interaction
        # self.setCacheMode(QtWidgets.QGraphicsView.CacheBackground)
        self.setRenderHint(QtGui.QPainter.Antialiasing)
        self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        
        if scene:
            self.scene = scene
        else:
            self.scene = SceneClass(view=self)
        self.setScene(self.scene)
        self.lastMousePos = None
        
        if self.scene.nodeColl:
            lastNode = self.scene.nodeColl[0]
            lastNodePos = QtCore.QPoint(lastNode.x(), lastNode.y())
            self.centerOn(lastNodePos)
    
    
    def frameBounds(self, bounds):
        """
        Frames a given bounding rectangle within the viewport.
        """
        if bounds.isEmpty():
            return
        widthAdjust = bounds.width() * 0.2
        heightAdjust = bounds.height() * 0.2
        bounds.adjust(-widthAdjust, -heightAdjust, widthAdjust, heightAdjust)
        self.fitInView(bounds, QtCore.Qt.KeepAspectRatio)
    
    
    def frameNodes(self, itemList, extraPadding=False):
        """
        Frames a bunch of nodes in the viewport
        """
        
        if itemList:
            bounds = QtCore.QRectF()
            for item in itemList:
                bounds |= item.sceneBoundingRect()
            if extraPadding:
                bounds.setX(bounds.x() - (bounds.width() / 2))
                bounds.setY(bounds.y() - (bounds.height() / 2))
                bounds.setWidth(bounds.width() * 1.5)
                bounds.setHeight(bounds.height() * 1.5)
            
            self.frameBounds(bounds)
    
    
    def keyPressEvent(self, event):
        """
        Stifles autorepeat and handles a few shortcut keys that aren't
        registered as functions in the main window.
        """
        # This widget will never process auto-repeating keypresses so ignore 'em all
        if event.isAutoRepeat():
            return
        
        # Frame selected/all items
        if event.key() == QtCore.Qt.Key_F:
            itemList = list()
            if self.scene.selectedItems():
                itemList = self.scene.selectedItems()
            else:
                itemList = self.scene.items()
            self.frameNodes(itemList)
        
        if event.key() == QtCore.Qt.Key_A:
            itemList = self.scene.items()
            self.frameNodes(itemList)
    
    
    def keyReleaseEvent(self, event):
        """
        Stifle auto-repeats and handle letting go of the space bar.
        """
        # Ignore auto-repeats
        if event.isAutoRepeat():
            return
    
    
    def wheelEvent(self, event):
        """
        Zooming.
        """
        self.scaleView(math.pow(2.0, event.delta() / 240.0))
    
    
    def scaleView(self, scaleFactor):
        """
        Zoom helper function.
        """
        factor = self.matrix().scale(scaleFactor, scaleFactor).mapRect(QtCore.QRectF(0, 0, 1, 1)).width()
        if factor > 100:
            return
        self.scale(scaleFactor, scaleFactor)
    
    
    def mousePressEvent(self, event):
        if event.buttons() & QtCore.Qt.LeftButton:
            self.scene.clearSelection()
            QtWidgets.QGraphicsView.mousePressEvent(self, event)
        else:
            # MMB / RMB
            sel = self.scene.selectedItems()
            for item in sel:
                item.setSelected(True)
            event.accept()
    
    
    def mouseMoveEvent(self, event):
        """
        Panning the viewport around and CTRL+mouse drag behavior.
        """
        
        if not self.lastMousePos:
            self.lastMousePos = event.pos()
        currentScale = self.matrix().m11()
        delta = event.pos() - self.lastMousePos
        if event.modifiers() & QtCore.Qt.AltModifier:
            
            # Panning
            if event.buttons() & QtCore.Qt.RightButton:
                
                # ALT + RMB zoom
                self.setDragMode(QtWidgets.QGraphicsView.NoDrag)
                
                dx = math.pow(2.0, delta.x() / 240.0)
                self.scaleView(dx)
                event.accept()
            
            elif event.buttons() & QtCore.Qt.MiddleButton:
                # ALT + MMB PAN
                self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)
                
                self.translate(delta.x() * currentScale, delta.y() * currentScale)
                event.accept()
        
        elif event.buttons() & QtCore.Qt.MiddleButton:
            # MMB PAN
            self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)
            
            self.translate(delta.x() * currentScale, delta.y() * currentScale)
            event.accept()
        
        elif event.buttons() & QtCore.Qt.RightButton:
            # ALT + RMB zoom
            self.setDragMode(QtWidgets.QGraphicsView.NoDrag)
            
            dx = math.pow(2.0, delta.x() / 240.0)
            self.scaleView(dx)
            event.accept()
        else:
            # LMB
            self.setDragMode(QtWidgets.QGraphicsView.RubberBandDrag)
        
        self.lastMousePos = event.pos()
        QtWidgets.QGraphicsView.mouseMoveEvent(self, event)


class SceneClass(QtWidgets.QGraphicsScene):
    def __init__(self, view=None):
        super(SceneClass, self).__init__()
        # self.setSceneRect(-1000, -1000, 2000, 2000)
        self.grid = 30
        self.it = None
        self.node = None
        self.view = view
        self.nodeColl = []
        self.edgeColl = []
        
    
    
    def populate(self):
        dir = 'O:/projects/alt_ResearchDevelopment_2019_4942/sequences/shots/rnd/setups/maya/scenes/anim/elements/ball/'
        
        width = 300
        height = 100
        hpad = 100
        vpad = 50
        
        totalx = 0
        totaly = 0
        x = 0
        
        for majorver in os.listdir(dir):
            totalx = x
            if majorver[0] == '.':
                continue
            print majorver
            
            label = Label(title=majorver)
            label.moveBy(x * (width + hpad), -0.5 * (height + vpad))
            self.addItem(label)
            
            majorpath = os.path.join(dir, majorver)
            y = 0
            for minorver in os.listdir(majorpath):
                if minorver[0] == '.':
                    continue
                minorpath = os.path.join(majorpath, minorver).replace("\\", '/')
                
                print minorpath
                node = Node(title=minorver, filepath=minorpath, width=width, height=height)
                print x, y, node.width, node.height
                node.moveBy(x * (width + hpad), y * (height + vpad))
                print node.x(), node.y()
                self.addItem(node)
                if y > totaly:
                    totaly = y
                self.nodeColl.append(node)
                
                y += 1
            x += 1
        pad = 300
        rect = self.sceneRect()
        rect.setLeft(rect.left() - pad)
        rect.setTop(rect.top() - pad)
        rect.setRight(rect.right() + pad)
        rect.setBottom(rect.bottom() + pad)
        self.setSceneRect(rect)
    
    
    def drawBackground(self, painter, rect):
        
        painter.fillRect(rect, QtGui.QColor(30, 30, 30))
        left = int(rect.left()) - int((rect.left()) % self.grid)
        top = int(rect.top()) - int((rect.top()) % self.grid)
        right = int(rect.right())
        bottom = int(rect.bottom())
        lines = []
        for x in range(left, right, self.grid):
            lines.append(QtCore.QLine(x, top, x, bottom))
        for y in range(top, bottom, self.grid):
            lines.append(QtCore.QLine(left, y, right, y))
        painter.setPen(QtGui.QPen(QtGui.QColor(50, 50, 50)))
        painter.drawLines(lines)
    
    
    def keyPressEvent(self, event):
        view_pos = self.view.mapFromGlobal(QtGui.QCursor().pos())
        scene_pos = self.view.mapToScene(view_pos)
        
        # if event.key() == Qt.Key_Q:
        #     node = Node(None, 0)
        #     node.moveBy(scene_pos.x(), scene_pos.y())
        #     self.addItem(node)
        
        super(SceneClass, self).keyPressEvent(event)


class Label(QtWidgets.QGraphicsItem):
    def __init__(self, title=None):
        super(Label, self).__init__()
        
        self.title = title or 'blahblah'
        
        self.width = 300
        self.height = 100
        self.radius = 15
        
        self.setZValue(1)
        # self.setFlag(QGraphicsItem.ItemIsMovable)
    
    
    def boundingRect(self):
        """
        Defines the clickable hit-box.  Simply returns a rectangle instead of
        a rounded rectangle for speed purposes.
        """
        adjust = 2.0
        return QtCore.QRectF(0, 0, self.width + 3 + adjust, self.height + 3 + adjust)
    
    
    def paint(self, painter, option, widget):
        # Text (none for dot nodes)
        textRect = QtCore.QRectF(4, 4, self.boundingRect().width() - 4, 20)
        font = painter.font()
        font.setPointSize(20)
        painter.setFont(font)
        painter.setPen(QtCore.Qt.lightGray)
        painter.drawText(textRect, QtCore.Qt.AlignCenter, self.title)


class Node(QtWidgets.QGraphicsItem):
    def __init__(self, title=None, filepath=None, width=300, height=100):
        super(Node, self).__init__()
        
        self.title = title or 'blahblah'
        self.filepath = filepath
        
        self.width = 300
        self.height = 100
        self.radius = 15
        
        self.edges = []
        self.source_edges = []
        self.dest_edges = []
        
        self.setZValue(1)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable)
        self.setFlag(QtWidgets.QGraphicsItem.ItemSendsGeometryChanges)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable)
        self.setCacheMode(self.DeviceCoordinateCache)
    
    
    def __repr__(self):
        return '<Node "%s">' % (self.title)
    
    
    def mouseDoubleClickEvent(self, event):
        print 'mouseDoubleClickEvent'
        super(Node, self).mouseDoubleClickEvent()
    
    
    def upstream_nodes(self, node, level=0):
        ret = []
        for edge in node.source_edges:
            edge_node = edge.source
            ret.append(edge_node)
            ret.extend(self.upstream_nodes(edge_node, level=level + 1))
        return ret
    
    
    def downstream_nodes(self, node, level=0):
        ret = []
        for edge in node.dest_edges:
            edge_node = edge.dest
            ret.append(edge_node)
            ret.extend(self.downstream_nodes(edge_node, level=level + 1))
        return ret
    
    
    def select_upstream(self):
        nodes = self.upstream_nodes(self)
        for node in nodes:
            node.setSelected(True)
    
    
    def select_downstream(self):
        nodes = self.downstream_nodes(self)
        
        for node in nodes:
            node.setSelected(True)
    
    
    def mousePressEvent(self, event):
        if event.modifiers() == QtCore.Qt.ShiftModifier:
            self.select_upstream()
            event.accept()
        
        elif event.modifiers() == QtCore.Qt.ControlModifier:
            self.select_downstream()
            event.accept()
        else:
            super(Node, self).mousePressEvent(event)
            sel_nodes = self.scene().selectedItems()
            print sel_nodes
            for node in sel_nodes:
                node.setSelected(True)
    
    
    def mouseMoveEvent(self, event):
        super(Node, self).mouseMoveEvent(event)
    
    
    def contextMenuEvent(self, event):
        self.setSelected(True)
        menu = QtWidgets.QMenu()
        # menu.addAction("Open")
        
        info_act = menu.addAction("Info...")
        info_act.triggered.connect(self.info)
        
        trace_act = menu.addAction("Trace...")
        trace_act.triggered.connect(self.trace)
        
        position = QtGui.QCursor.pos()
        menu.exec_(position)
        
        # this will tell the parent graphicsView not to use the event
        event.setAccepted(True)
    
    
    def info(self):
        print self.filepath
    
    
    def _trace_nodes(self, node, level=0):
        for edge in node.source_edges:
            edge_node = edge.source
            print ('-' * level) + str(edge_node)
            self._trace_nodes(edge_node, level=level + 1)
    
    
    def trace(self):
        print 'my source edges:'.center(40, '-')
        for edge in self.source_edges:
            print edge
        
        print 'my dest edges:'.center(40, '-')
        for edge in self.dest_edges:
            print edge
        
        print 'trace:'.center(40, '-')
        self._trace_nodes(self)
        print 'done:'.center(40, '-')
    
    
    def boundingRect(self):
        """
        Defines the clickable hit-box.  Simply returns a rectangle instead of
        a rounded rectangle for speed purposes.
        """
        
        adjust = 2.0
        return QtCore.QRectF(0, 0, self.width + 3 + adjust, self.height + 3 + adjust)
    
    
    def itemChange(self, change, value):
        """
        If the node has been moved, update all of its draw edges.
        """
        
        if change == QtWidgets.QGraphicsItem.ItemPositionHasChanged:
            for edge in self.source_edges:
                edge.adjust()
            for edge in self.dest_edges:
                edge.adjust()
        return QtWidgets.QGraphicsItem.itemChange(self, change, value)
    
    
    def paint(self, painter, option, widget):
        """
        Draw the node, whether it's in the highlight list, selected or
        unselected, is currently executable, and its name.  Also draws a
        little light denoting if it already has data present and/or if it is
        in a "stale" state.
        """
        
        inputsFulfilled = None
        
        bgColor = QtGui.QColor.fromRgbF(0.75, 0.75, 0.75)
        pen = QtGui.QPen(QtCore.Qt.black, 0)
        pen.setWidth(1)
        
        if option.state & QtWidgets.QStyle.State_Selected:
            bgColor = QtGui.QColor.fromRgbF(1, 0.6, 0.2)
            pen = QtGui.QPen(QtCore.Qt.white, 0)
            pen.setWidth(3)
        
        painter.setPen(pen)
        painter.setBrush(bgColor)
        fullRect = QtCore.QRectF(0, 0, self.width, self.height)
        painter.drawRoundedRect(fullRect, self.radius, self.radius)
        
        painter.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0), 0.25))
        painter.setBrush(QtGui.QBrush(QtGui.QColor(255, 0, 0)))
        
        painter.drawRect(QtCore.QRectF(self.radius, self.radius, 10, 10))
        
        # Text (none for dot nodes)
        textRect = QtCore.QRectF(self.radius, self.radius, self.boundingRect().width() - self.radius, 20)
        font = painter.font()
        font.setPointSize(12)
        painter.setFont(font)
        painter.setPen(QtCore.Qt.black)
        painter.drawText(textRect, QtCore.Qt.AlignCenter, self.title)


class Edge(QtWidgets.QGraphicsItem):
    """
    A QGraphicsItem representing a connection between two DAG nodes.  These can
    be clicked and dragged to change, add, or remove connections between nodes.
    """
    
    TwoPi = 2.0 * math.pi
    Type = QtWidgets.QGraphicsItem.UserType + 2
    
    
    def __init__(self, sourceDrawNode, destDrawNode, scene=None):
        """
        """
        QtWidgets.QGraphicsItem.__init__(self)
        
        self.scene = scene
        
        self.width = 4
        self.arrowSize = 10.0
        self.sourcePoint = QtCore.QPointF()
        self.destPoint = QtCore.QPointF()
        self.horizontalConnectionOffset = 0.0
        self.setAcceptedMouseButtons(QtCore.Qt.LeftButton)
        
        self.setZValue(-2)
        
        self.source = sourceDrawNode
        self.dest = destDrawNode
        
        self.adjust()
        
        # MouseMoved is a little hack to get around a bug where clicking the mouse and not dragging caused an error
        self.mouseMoved = False
        self.dragging = False
    
    
    def __repr__(self):
        return '<Edge "%s" -> "%s">' % (self.source.title, self.dest.title)
    
    
    def type(self):
        """
        Assistance for the QT windowing toolkit.
        """
        return Edge.Type
    
    
    def adjust(self):
        """
        Recompute where the line is pointing.
        """
        
        view = self.scene.view
        line = QtCore.QLineF(QtCore.QPointF(self.source.x() + self.source.width, self.source.y()),
                             QtCore.QPointF(self.dest.x(), self.dest.y()), )
        
        length = line.length()
        
        if length == 0.0:
            return
        
        radius = 3
        
        sourceOffset = 35 + radius
        destOffset = 35 + radius
        
        self.prepareGeometryChange()
        self.sourcePoint = line.p1() + QtCore.QPointF(radius, sourceOffset)
        if self.dest:
            self.destPoint = line.p2() + QtCore.QPointF(-radius, destOffset)
        else:
            self.destPoint = line.p2()
    
    
    def boundingRect(self):
        """
        Hit box assistance.  Only let the user click on the tip of the line.
        """
        if not self.source:  # or not self.dest:
            return QtCore.QRectF()
        penWidth = 1
        extra = (penWidth + self.arrowSize) / 2.0
        return QtCore.QRectF(self.sourcePoint,
                             QtCore.QSizeF(self.destPoint.x() - self.sourcePoint.x(),
                                           self.destPoint.y() - self.sourcePoint.y())).normalized().adjusted(-extra,
                                                                                                             -extra,
                                                                                                             extra,
                                                                                                             extra)
    
    
    def shape(self):
        """
        The QT shape function.
        """
        
        # Setup and stroke the line
        path = QtGui.QPainterPath(self.sourcePoint)
        path.lineTo(self.destPoint)
        stroker = QtGui.QPainterPathStroker()
        stroker.setWidth(4)
        stroked = stroker.createStroke(path)
        # Add a square at the tip
        stroked.addRect(self.destPoint.x() - 10, self.destPoint.y() - 10, 20, 20)
        return stroked
    
    
    def paint(self, painter, option, widget):
        """
        Draw a line with an arrow at the end.
        """
        if not self.source:  # or not self.dest:
            return
        
        # get the scene that this widget is drawn into to get the scale
        # to compensate the width
        scene = self.scene.views()[0]
        xform = scene.transform()
        scene_scale = xform.m11()
        
        # Draw the line
        line = QtCore.QLineF(self.sourcePoint, self.destPoint)
        if line.length() == 0.0:
            return
        painter.setPen(
            QtGui.QPen(QtCore.Qt.white, min(self.width / scene_scale, 0.5), QtCore.Qt.SolidLine, QtCore.Qt.RoundCap,
                       QtCore.Qt.RoundJoin))
        # painter.drawLine(line)
        
        path = QtGui.QPainterPath()
        path.moveTo(self.sourcePoint)
        path.cubicTo(self.sourcePoint + QtCore.QPoint(50, 0), self.destPoint + QtCore.QPoint(-50, 0), self.destPoint)
        painter.drawPath(path)
        # print path.slopeAtPercent(0.5)
        
        # Draw the arrows if there's enough room.
        angle = math.acos(line.dx() / line.length())
        if line.dy() >= 0:
            angle = Edge.TwoPi - angle
        destArrowP1 = self.destPoint + QtCore.QPointF(math.sin(angle - math.pi / 3) * self.arrowSize,
                                                      math.cos(angle - math.pi / 3) * self.arrowSize)
        destArrowP2 = self.destPoint + QtCore.QPointF(math.sin(angle - math.pi + math.pi / 3) * self.arrowSize,
                                                      math.cos(angle - math.pi + math.pi / 3) * self.arrowSize)
        painter.setBrush(QtCore.Qt.white)
        painter.drawPolygon(QtGui.QPolygonF([line.p2(), destArrowP1, destArrowP2]))


def main(parent):
    wd = DialogClass(parent=parent)
    wd.show()


if __name__ == '__main__':
    app = QtCore.QApplication([])
    wd = WindowClass()
    wd.show()
    app.exec_()
