import os
import re
import json
import copy

from Qt import QtGui, QtCore, QtWidgets
import nodz_utils as utils
import nodz_extra


defaultConfigPath = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'default_config.json')


class VariantAnimation(QtCore.QVariantAnimation):
    def updateCurrentValue(self, value):
        pass


class ConnectionInfo():
    def __init__(self, connectionItem):
        # Storage.
        self.socketNode = connectionItem.socketNode
        self.socketAttr = connectionItem.socketAttr
        self.plugNode = connectionItem.plugNode
        self.plugAttr = connectionItem.plugAttr


class Nodz(QtWidgets.QGraphicsView):
    """
    The main view for the node graph representation.

    The node view implements a state pattern to control all the
    different user interactions.

    """
    
    # if we want to be more generic, should use pre and post signals, and fetch whatever in Layout side, but this is not resilient to nested calls :/
    # some calls have not been handled via those methodes : createNode (handled via nodeCreator overload), editNode, deleteNode, createAttribute, editAttribute, deleteAttribute : they are not called directly by LayoutEditor, but encapsulated via nodeCreator, loadGraph, etc. We issue less events if handling the top level action issueing this
    # all undo calls start with emitter nodzInstance
    signal_UndoRedoModifySelection = QtCore.Signal(object, object,
                                                   object)  # node id list before, node id list after. signal_NodeSelected does not send previous selection
    signal_UndoRedoDeleteSelectedNodes = QtCore.Signal(object,
                                                       object)  # list of deleted nodes (user data copies). signal_NodeDeleted does only send deleted node names, too late to get their userData for redo
    # # signal_UndoRedoEditNodeName = QtCore.Signal(object, str, str) # node name before, node name after UNUSED
    signal_UndoRedoAddNode = QtCore.Signal(object,
                                           object)  # node added user data. For consistency with signal_UndoRedoDeleteSelectedNodes (we may actually store undo via signal_NodeCreated, but would be called a lot of time from loadGraph)
    signal_UndoRedoMoveNodes = QtCore.Signal(object, object, object,
                                             object)  # node name list, fromPos list, toPos list. signal_NodeMoved does not send previous position
    signal_UndoRedoConnectNodes = QtCore.Signal(object, object,
                                                object)  # list of removed ConnectionInfo (potentially due to addition), list of new ConnectionInfo. Could deal with it with plug/socket connected / disconnected but would be tedious with a lot of calls
    
    signal_dropOnNode = QtCore.Signal(object, object)  # nodzInst, nodeItem
    
    signal_StartCompoundInteraction = QtCore.Signal(object)  # starts user interaction on a nodz
    signal_EndCompoundInteraction = QtCore.Signal(object, bool)  # end user interaction on a nodz
    
    signal_NodeCreated = QtCore.Signal(object)
    signal_NodePreDeleted = QtCore.Signal(object)
    signal_NodeDeleted = QtCore.Signal(object)
    signal_NodeEdited = QtCore.Signal(object, object)
    signal_NodeSelected = QtCore.Signal(object)
    signal_NodeMoved = QtCore.Signal(str, object)
    # signal_NodeRightClicked = QtCore.Signal(str)
    signal_NodeDoubleClicked = QtCore.Signal(str)
    
    signal_ViewContextMenuEvent = QtCore.Signal(object)  # view context menu event
    signal_NodeContextMenuEvent = QtCore.Signal(object, str)  # node context menu event, node name
    
    signal_AttrCreated = QtCore.Signal(object, object)
    signal_AttrDeleted = QtCore.Signal(object, object)
    signal_AttrEdited = QtCore.Signal(object, object, object)
    
    signal_PlugConnected = QtCore.Signal(object, object, object, object)
    signal_PlugDisconnected = QtCore.Signal(object, object, object, object)
    signal_SocketConnected = QtCore.Signal(object, object, object, object)
    signal_SocketDisconnected = QtCore.Signal(object, object, object, object)
    
    signal_GraphSaved = QtCore.Signal()
    signal_GraphLoaded = QtCore.Signal()
    signal_GraphCleared = QtCore.Signal()
    signal_GraphEvaluated = QtCore.Signal()
    
    signal_KeyPressed = QtCore.Signal(object)
    signal_Dropped = QtCore.Signal()
    
    signal_dragEvent = QtCore.Signal(object, object)  # dragDropEvent, nodzInst
    signal_dragMoveEvent = QtCore.Signal(object, object)  # dragDropEvent, nodzInst
    signal_dropEvent = QtCore.Signal(object, object)  # dragDropEvent, nodzInst
    
    
    def __init__(self, parent, configPath=defaultConfigPath):
        """
        Initialize the graphics view.

        """
        super(Nodz, self).__init__(parent)
        
        # Load nodz configuration.
        self.config = None
        self.loadConfig(configPath)
        
        # General data.
        self.gridVisToggle = True
        self.gridSnapToggle = False
        self._nodeSnap = False
        self.selectedNodes = list()
        
        # Connections data.
        self.drawingConnection = False
        self.currentHoveredNodeForConnection = None
        self.currentHoveredNodeForDrop = None
        self.currentHoveredAttribute = None
        self.currentHoveredLink = None
        self.sourceSlot = None
        self.allowLoop = True
        
        self.editEnabled = True
        
        # Display options.
        self.currentState = 'DEFAULT'
        self.pressedKeys = list()
        
        # Node creation helper
        self.nodeCreationPopup = None
        self.nodeCreationPopupKeyEvent = None
        
        # drag n drop data to set when event called
        self.dragAccept = False
        self.dragMoveAccept = False
        self.dropAccept = False
        
        self.cutTool = None
        
        self.setRenderHints(
            QtGui.QPainter.Antialiasing | QtGui.QPainter.SmoothPixmapTransform | QtGui.QPainter.HighQualityAntialiasing)
    
    
    def setEnableDrop(self, enabled):
        self.setAcceptDrops(enabled and self.editEnabled)
        # self.setDropIndicatorShown(enabled)
    
    
    def dragEnterEvent(self, e):
        if (self.editEnabled):
            self.signal_dragEvent.emit(e, self)
            if self.dragAccept:
                e.accept()
            else:
                e.ignore()
        else:
            e.ignore()
    
    
    def dragMoveEvent(self, e):
        if (self.editEnabled):
            self.signal_dragMoveEvent.emit(e, self)
            if self.dragMoveAccept:
                e.accept()
            else:
                e.ignore()
        else:
            e.ignore()
    
    
    def dropEvent(self, e):
        if (self.editEnabled):
            self.signal_dropEvent.emit(e, self)
            if self.dropAccept:
                e.accept()
            else:
                e.ignore()
        else:
            e.ignore()
    
    
    def event(self, event):
        if (
                self.editEnabled and event.type() == QtCore.QEvent.KeyPress):  # bypass QWidget behaviors which is to checks for Tab and Shift+Tab and tries to move the focus appropriately
            self.keyPressEvent(event)
            return True
        
        return super(Nodz, self).event(event)
    
    
    def wheelEvent(self, event):
        """
        Zoom in the view with the mouse wheel.

        """
        self.currentState = 'ZOOM_VIEW'
        self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        
        inFactor = 1.15
        outFactor = 1 / inFactor
        
        if event.angleDelta().y() > 0:
            zoomFactor = inFactor
        else:
            zoomFactor = outFactor
        
        self.scale(zoomFactor, zoomFactor)
        self.currentState = 'DEFAULT'
    
    
    def contextMenuEvent(self, event):
        if (event.modifiers() & QtCore.Qt.AltModifier) or (event.modifiers() & QtCore.Qt.ControlModifier) or (
                not self.editEnabled):
            return
        
        p = event.pos()
        item = self.itemAt(p.x(), p.y())
        if item is not None:
            item.contextMenuEvent(event)
            return
        self.signal_ViewContextMenuEvent.emit(event)
    
    
    def mousePressEvent(self, event):
        """
        Initialize tablet zoom, drag canvas and the selection.

        """
        # Tablet zoom
        if (event.button() == QtCore.Qt.RightButton and
                (event.modifiers() & QtCore.Qt.AltModifier)):
            self.currentState = 'ZOOM_VIEW'
            self.initMousePos = event.pos()
            self.zoomInitialPos = event.pos()
            self.initMouse = QtGui.QCursor.pos()
            self.setInteractive(False)
        
        
        # Drag view
        elif (event.button() == QtCore.Qt.MiddleButton and
              (event.modifiers() & QtCore.Qt.AltModifier)):
            self.currentState = 'DRAG_VIEW'
            self.prevPos = event.pos()
            self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)
            self.setCursor(QtCore.Qt.ClosedHandCursor)
            self.setInteractive(False)
        
        
        # Rubber band selection
        elif (event.button() == QtCore.Qt.LeftButton and
              (event.modifiers() == QtCore.Qt.NoModifier) and
              self.scene().itemAt(self.mapToScene(event.pos()), QtGui.QTransform()) is None):
            self.currentState = 'SELECTION'
            self._initRubberband(event.pos())
            self.setInteractive(False)
        
        # Drag Item
        elif (self.editEnabled and
              event.button() == QtCore.Qt.LeftButton and
              (event.modifiers() == QtCore.Qt.NoModifier) and
              isinstance(self.scene().itemAt(self.mapToScene(event.pos()), QtGui.QTransform()), NodeItem)):
            self.currentState = 'DRAG_ITEM'
            self.setInteractive(True)
        
        # Add selection
        elif (event.button() == QtCore.Qt.LeftButton and
              (event.modifiers() & QtCore.Qt.ShiftModifier) and
              (event.modifiers() & QtCore.Qt.ControlModifier)):
            self.currentState = 'ADD_SELECTION'
            self._initRubberband(event.pos())
            self.setInteractive(False)
        
        
        # Subtract selection
        elif (event.button() == QtCore.Qt.LeftButton and
              (event.modifiers() & QtCore.Qt.ControlModifier)):
            self.currentState = 'SUBTRACT_SELECTION'
            self._initRubberband(event.pos())
            self.setInteractive(False)
        
        
        # Toggle selection
        elif (event.button() == QtCore.Qt.LeftButton and
              (event.modifiers() & QtCore.Qt.ShiftModifier)):
            self.currentState = 'TOGGLE_SELECTION'
            self._initRubberband(event.pos())
            self.setInteractive(False)
        
        # Cut tool Golaem
        elif (self.editEnabled and
              event.button() == QtCore.Qt.LeftButton and
              (event.modifiers() & QtCore.Qt.AltModifier) and
              self.scene().itemAt(self.mapToScene(event.pos()), QtGui.QTransform()) is None):
            self.currentState = 'CUT_LINK'
            self._initCutTool(event.pos())
            self.setCursor(QtCore.Qt.CrossCursor)
            self.setInteractive(True)
        
        else:
            self.currentState = 'DEFAULT'
        
        super(Nodz, self).mousePressEvent(event)
    
    
    def mouseMoveEvent(self, event):
        """
        Update tablet zoom, canvas dragging and selection.

        """
        # Zoom.
        if self.currentState == 'ZOOM_VIEW':
            offset = self.zoomInitialPos.x() - event.pos().x()
            
            if offset > self.previousMouseOffset:
                self.previousMouseOffset = offset
                self.zoomDirection = -1
                self.zoomIncr -= 1
            
            elif offset == self.previousMouseOffset:
                self.previousMouseOffset = offset
                if self.zoomDirection == -1:
                    self.zoomDirection = -1
                else:
                    self.zoomDirection = 1
            
            else:
                self.previousMouseOffset = offset
                self.zoomDirection = 1
                self.zoomIncr += 1
            
            if self.zoomDirection == 1:
                zoomFactor = 1.03
            else:
                zoomFactor = 1 / 1.03
            
            # Perform zoom and re-center on initial click position.
            pBefore = self.mapToScene(self.initMousePos)
            self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorViewCenter)
            self.scale(zoomFactor, zoomFactor)
            pAfter = self.mapToScene(self.initMousePos)
            diff = pAfter - pBefore
            
            self.setTransformationAnchor(QtWidgets.QGraphicsView.NoAnchor)
            self.translate(diff.x(), diff.y())
        
        # Drag canvas.
        elif self.currentState == 'DRAG_VIEW':
            offset = self.prevPos - event.pos()
            self.prevPos = event.pos()
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() + offset.y())
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() + offset.x())
        
        # cutTool Golaem
        elif self.currentState == 'CUT_LINK':
            scenePos = self.mapToScene(event.pos())
            deltaLine = scenePos - self.cutToolStartScenePos
            self.cutTool.setLine(self.cutToolStartScenePos.x(), self.cutToolStartScenePos.y(),
                                 self.cutToolStartScenePos.x() + deltaLine.x(),
                                 self.cutToolStartScenePos.y() + deltaLine.y())
        
        # RuberBand selection.
        elif (self.currentState == 'SELECTION' or
              self.currentState == 'ADD_SELECTION' or
              self.currentState == 'SUBTRACT_SELECTION' or
              self.currentState == 'TOGGLE_SELECTION'):
            self.rubberband.setGeometry(QtCore.QRect(self.origin, event.pos()).normalized())
        
        super(Nodz, self).mouseMoveEvent(event)
    
    
    def mouseReleaseEvent(self, event):
        """
        Apply tablet zoom, dragging and selection.

        """
        
        self.setDragMode(QtWidgets.QGraphicsView.NoDrag)
        
        # Zoom the View.
        if self.currentState == '.ZOOM_VIEW':
            self.offset = 0
            self.zoomDirection = 0
            self.zoomIncr = 0
            self.setInteractive(True)
        
        # Drag View.
        elif self.currentState == 'DRAG_VIEW':
            self.setCursor(QtCore.Qt.ArrowCursor)
            self.setInteractive(True)
        
        # Selection.
        elif self.currentState == 'SELECTION':
            self.rubberband.setGeometry(QtCore.QRect(self.origin,
                                                     event.pos()).normalized())
            painterPath = self._releaseRubberband()
            self.setInteractive(True)
            self.scene().setSelectionArea(painterPath)
        
        
        # Add Selection.
        elif self.currentState == 'ADD_SELECTION':
            self.rubberband.setGeometry(QtCore.QRect(self.origin,
                                                     event.pos()).normalized())
            painterPath = self._releaseRubberband()
            self.setInteractive(True)
            for item in self.scene().items(painterPath):
                item.setSelected(True)
        
        
        # Subtract Selection.
        elif self.currentState == 'SUBTRACT_SELECTION':
            self.rubberband.setGeometry(QtCore.QRect(self.origin,
                                                     event.pos()).normalized())
            painterPath = self._releaseRubberband()
            self.setInteractive(True)
            for item in self.scene().items(painterPath):
                item.setSelected(False)
        
        
        # Toggle Selection
        elif self.currentState == 'TOGGLE_SELECTION':
            self.rubberband.setGeometry(QtCore.QRect(self.origin,
                                                     event.pos()).normalized())
            painterPath = self._releaseRubberband()
            self.setInteractive(True)
            for item in self.scene().items(painterPath):
                if item.isSelected():
                    item.setSelected(False)
                else:
                    item.setSelected(True)
        
        # Cut tool Golaem
        elif self.currentState == 'CUT_LINK':
            scenePos = self.mapToScene(event.pos())
            deltaLine = scenePos - self.cutToolStartScenePos
            self.cutTool.setLine(self.cutToolStartScenePos.x(), self.cutToolStartScenePos.y(),
                                 self.cutToolStartScenePos.x() + deltaLine.x(),
                                 self.cutToolStartScenePos.y() + deltaLine.y())
            painterPath = self._releaseCutTool()
            
            removedConnections = list()
            addedConnections = list()
            
            self.setInteractive(True)
            for item in self.scene().items(painterPath):
                if (isinstance(item, ConnectionItem)):
                    removedConnections.append(ConnectionInfo(item))
                    item._remove()
            self.setCursor(QtCore.Qt.ArrowCursor)
            
            if len(removedConnections) > 0:
                self.signal_UndoRedoConnectNodes.emit(self, removedConnections, addedConnections)
        
        self.currentState = 'DEFAULT'
        
        super(Nodz, self).mouseReleaseEvent(event)
        
        if (self.editEnabled and event.button() == QtCore.Qt.RightButton and not event.isAccepted()):
            self.signal_ViewRightClicked.emit()
    
    
    def keyPressEvent(self, event):
        """
        Save pressed key and apply shortcuts.

        Shortcuts are:
        DEL - Delete the selected nodes
        F - Focus view on the selection

        """
        if event.key() not in self.pressedKeys:
            self.pressedKeys.append(event.key())
        
        if (self.editEnabled):
            if event.key() in (QtCore.Qt.Key_Delete, QtCore.Qt.Key_Backspace):
                self._deleteSelectedNodes()
            
            if event.key() == self.nodeCreationPopupKeyEvent:
                self.nodeCreationPopup.popup()
            
            if event.key() == QtCore.Qt.Key_Escape:
                self.nodeCreationPopup.popdown()
        
        if event.key() == QtCore.Qt.Key_F:
            self._focus()
        
        if event.key() == QtCore.Qt.Key_A:
            itemsArea = self.scene().itemsBoundingRect()
            self.fitInView(itemsArea, QtCore.Qt.KeepAspectRatio)
        
        if event.key() == QtCore.Qt.Key_S:
            self._nodeSnap = True
        
        # Emit signal.
        self.signal_KeyPressed.emit(event.key())
    
    
    def keyReleaseEvent(self, event):
        """
        Clear the key from the pressed key list.

        """
        if event.key() == QtCore.Qt.Key_S:
            self._nodeSnap = False
        
        if event.key() in self.pressedKeys:
            self.pressedKeys.remove(event.key())
    
    
    def _initRubberband(self, position):
        """
        Initialize the rubber band at the given position.

        """
        self.rubberBandStart = position
        self.origin = position
        self.rubberband.setGeometry(QtCore.QRect(self.origin, QtCore.QSize()))
        self.rubberband.show()
    
    
    def _releaseRubberband(self):
        """
        Hide the rubber band and return the path.

        """
        painterPath = QtGui.QPainterPath()
        rect = self.mapToScene(self.rubberband.geometry())
        painterPath.addPolygon(rect)
        self.rubberband.hide()
        return painterPath
    
    
    def _initCutTool(self, position):
        """
        Initialize the cut tool at the given position.

        """
        if (self.cutTool is None):
            self.cutTool = QtWidgets.QGraphicsLineItem()
            self.cutTool.setZValue(65535)
            pen = QtGui.QPen(QtCore.Qt.red, 2, QtCore.Qt.DashLine)
            self.cutTool.setPen(pen)
            self.cutTool.hide()
            self.scene().addItem(self.cutTool)
        
        self.cutToolStartScenePos = self.mapToScene(position)
        self.cutTool.setPos(0, 0)
        self.cutTool.setLine(self.cutToolStartScenePos.x(), self.cutToolStartScenePos.y(),
                             self.cutToolStartScenePos.x(), self.cutToolStartScenePos.y())
        self.cutTool.show()
    
    
    def _releaseCutTool(self):
        """
        Hide the cut tool

        """
        painterPath = self.cutTool.shape()
        self.cutTool.hide()
        return painterPath
    
    
    def animFitInView(self, end_rect):
        start_rect = self._getVisibleRect()
        anim = VariantAnimation()
        anim.setDuration = 3000
        anim.setStartValue(start_rect)
        anim.setEndValue(end_rect)
        anim.setParent(self)
        anim.valueChanged.connect(lambda x: self.fitInView(x, QtCore.Qt.KeepAspectRatio))
        anim.start()
    
    
    def _focus(self):
        """
        Center on selected nodes or all of them if no active selection.

        """
        if self.scene().selectedItems():
            itemsArea = self._getSelectionBoundingbox()
            # pad out the bounding box a bit
            itemsArea.adjust(-50, -50, 50, 50)
            self.animFitInView(itemsArea)
        else:
            itemsArea = self.scene().itemsBoundingRect()
            self.animFitInView(itemsArea)
    
    
    def _getVisibleRect(self):
        """
        Visible QRectF of a QGraphicsView
        https://stackoverflow.com/a/17924010

        :param view: QGraphicsView
        :return: Visible QRectF
        """
        
        viewport_rect = QtCore.QRect(0, 0, self.viewport().width(), self.viewport().height())
        visible_scene_rect = QtCore.QRectF(self.mapToScene(viewport_rect).boundingRect())
        return visible_scene_rect
    
    
    def _getSelectionBoundingbox(self):
        """
        Return the bounding box of the selection.

        """
        bbx_min = None
        bbx_max = None
        bby_min = None
        bby_max = None
        bbw = 0
        bbh = 0
        for item in self.scene().selectedItems():
            pos = item.scenePos()
            x = pos.x()
            y = pos.y()
            w = x + item.boundingRect().width()
            h = y + item.boundingRect().height()
            
            # bbx min
            if bbx_min is None:
                bbx_min = x
            elif x < bbx_min:
                bbx_min = x
            # end if
            
            # bbx max
            if bbx_max is None:
                bbx_max = w
            elif w > bbx_max:
                bbx_max = w
            # end if
            
            # bby min
            if bby_min is None:
                bby_min = y
            elif y < bby_min:
                bby_min = y
            # end if
            
            # bby max
            if bby_max is None:
                bby_max = h
            elif h > bby_max:
                bby_max = h
            # end if
        # end if
        bbw = bbx_max - bbx_min
        bbh = bby_max - bby_min
        return QtCore.QRectF(QtCore.QRect(bbx_min, bby_min, bbw, bbh))
    
    
    def _resetScale(self):
        """
        Resets the scale of the graphics view

        """
        originalTransform = self.transform()
        self.resetTransform()
        self.translate(originalTransform.dx(), originalTransform.dy())
    
    
    def _deleteSelectedNodes(self):
        """
        Delete selected nodes.

        """
        # self.signal_UndoRedoPreDeleteSelectedNodes.emit()
        removedConnections = list()
        deletedNodesUserData = list()
        
        # iterate on nodes first, will delete single connections after getting back selected items
        selected_nodes = list()
        
        if len(self.scene().selectedItems()) == 0:
            return
        
        for node in self.scene().selectedItems():
            if type(node) is NodeItem:
                # NodeItem
                selected_nodes.append(node.name)
        
        nodzInst = self.scene().views()[0]
        nodzInst.signal_StartCompoundInteraction.emit(nodzInst)
        
        if len(selected_nodes) > 0:
            self.signal_NodePreDeleted.emit(selected_nodes)
        
        for node in self.scene().selectedItems():
            if type(node) is NodeItem:
                # NodeItem
                selected_nodes.append(node.name)
                if node.scene() is not None:  # else already deleted by a previous node
                    # stack all sockets connections.
                    for socket in node.sockets.values():
                        for iCon in range(0, len(socket.connections)):
                            removedConnections.append(ConnectionInfo(socket.connections[iCon]))
                    
                    # stack all plugs connections.
                    for plug in node.plugs.values():
                        for iCon in range(0, len(plug.connections)):
                            removedConnections.append(ConnectionInfo(plug.connections[iCon]))
                    
                    deletedNodesUserData.append(copy.deepcopy(node.userData))
                node._remove()
        
        # scene should be refreshed with deleted items absent of selection now, just process remaining single connectionItems
        for node in self.scene().selectedItems():
            if type(node) is ConnectionItem:
                # connectionItem
                removedConnections.append(ConnectionInfo(node))
                node._remove()
        
        if len(removedConnections) > 0:
            addedConnections = list()
            self.signal_UndoRedoConnectNodes.emit(self, removedConnections, addedConnections)
        
        nodzInst.signal_EndCompoundInteraction.emit(nodzInst, True)
        
        # Emit signal.
        if len(selected_nodes) > 0:
            self.signal_NodeDeleted.emit(selected_nodes)
            self.signal_UndoRedoDeleteSelectedNodes.emit(self, deletedNodesUserData)
    
    
    def _returnSelection(self):
        """
        Wrapper to return selected items.

        """
        
        # self.selectedNodes
        # self.signal_UndoRedoPreModifySelection.emit()
        oldSelectedNodes = self.selectedNodes
        
        self.selectedNodes = list()
        if self.scene().selectedItems():
            for node in self.scene().selectedItems():
                if type(node) is NodeItem:
                    self.selectedNodes.append(node.name)
        
        # Emit signal.
        self.signal_NodeSelected.emit(self.selectedNodes)
        
        # self.selectedNodes
        if (oldSelectedNodes != self.selectedNodes):
            self.signal_UndoRedoModifySelection.emit(self, oldSelectedNodes, self.selectedNodes)
    
    
    ##################################################################
    # API
    ##################################################################
    
    def loadConfig(self, filePath):
        """
        Set a specific configuration for this instance of Nodz.

        :type  filePath: str.
        :param filePath: The path to the config file that you want to
                         use.

        """
        self.config = utils._loadConfig(filePath)
    
    
    def initialize(self):
        """
        Setup the view's behavior.

        """
        # Setup view.
        config = self.config
        self.setRenderHint(QtGui.QPainter.Antialiasing, config['antialiasing'])
        self.setRenderHint(QtGui.QPainter.TextAntialiasing, config['antialiasing'])
        self.setRenderHint(QtGui.QPainter.HighQualityAntialiasing, config['antialiasing_boost'])
        self.setRenderHint(QtGui.QPainter.SmoothPixmapTransform, config['smooth_pixmap'])
        self.setRenderHint(QtGui.QPainter.NonCosmeticDefaultPen, True)
        self.setViewportUpdateMode(QtWidgets.QGraphicsView.FullViewportUpdate)
        self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.rubberband = QtWidgets.QRubberBand(QtWidgets.QRubberBand.Rectangle, self)
        
        # Setup scene.
        scene = NodeScene(self)
        sceneWidth = config['scene_width']
        sceneHeight = config['scene_height']
        scene.setSceneRect(0, 0, sceneWidth, sceneHeight)
        self.setScene(scene)
        # Connect scene node moved signal
        scene.signal_NodeMoved.connect(self.signal_NodeMoved)
        
        # Tablet zoom.
        self.previousMouseOffset = 0
        self.zoomDirection = 0
        self.zoomIncr = 0
        
        # Connect signals.
        self.scene().selectionChanged.connect(self._returnSelection)
    
    
    def initNodeCreationHelper(self, completerNodeList=[], nodeCreatorCallback=None, keyEvent=QtCore.Qt.Key_Tab):
        """
        Setup the node's creation helper that is available from the tab key

        """
        self.nodeCreationPopupKeyEvent = keyEvent
        self.nodeCreationPopup = nodz_extra.QtPopupLineEditWidget(self.scene().views()[0])
        self.nodeCreationPopup.setNodesList(completerNodeList)
        if nodeCreatorCallback is not None:
            self.nodeCreationPopup.nodeCreator = nodeCreatorCallback
    
    
    # NODES
    def createNode(self, name='default', preset='node_default', position=None, alternate=True):
        """
        Create a new node with a given name, position and color.

        :type  name: str.
        :param name: The name of the node. The name has to be unique
                     as it is used as a key to store the node object.

        :type  preset: str.
        :param preset: The name of graphical preset in the config file.

        :type  position: QtCore.QPoint.
        :param position: The position of the node once created. If None,
                         it will be created at the center of the scene.

        :type  alternate: bool.
        :param alternate: The attribute color alternate state, if True,
                          every 2 attribute the color will be slightly
                          darker.

        :return : The created node

        """
        # print("create node {} at creaetNode pos {}".format(name, position))
        # Check for name clashes
        if name in self.scene().nodes.keys():
            print 'A node with the same name already exists : {0}'.format(name)
            print 'Node creation aborted !'
            return
        else:
            nodeItem = NodeItem(name=name, alternate=alternate, preset=preset,
                                config=self.config)
            
            # Store node in scene.
            self.scene().nodes[name] = nodeItem
            
            if position is None:
                # Get the center of the view.
                position = self.mapToScene(self.viewport().rect().center())
            
            # Set node position.
            self.scene().addItem(nodeItem)
            nodeItem.setPos(position - nodeItem.nodeCenter)
            
            nodeItem.checkIsWithinSceneRect()
            
            # Emit signal.
            self.signal_NodeCreated.emit(name)
            
            return nodeItem
    
    
    def deleteNode(self, node):
        """
        Delete the specified node from the view.

        :type  node: class.
        :param node: The node instance that you want to delete.

        """
        if not node in self.scene().nodes.values():
            print 'Node object does not exist !'
            print 'Node deletion aborted !'
            return
        
        if node in self.scene().nodes.values():
            nodeName = node.name
            
            # Should handle UndoRedo here, but deleteNode is not used anywhere in our code
            
            removedConnections = list()
            addedConnections = list()
            selected_nodes = list()
            selected_nodes.append(node)
            
            # stack all sockets connections.
            for socket in node.sockets.values():
                if len(socket.connections) > 0:
                    for socketConnection in socket.connections:
                        removedConnections.append(ConnectionInfo(socketConnection))
            
            # stack all plugs connections.
            for plug in node.plugs.values():
                if len(plug.connections) > 0:
                    for plugConnection in plug.connections:
                        removedConnections.append(ConnectionInfo(plugConnection))
            
            self.signal_NodePreDeleted.emit([nodeName])
            
            node._remove()
            
            # Emit signal.
            self.signal_NodeDeleted.emit([nodeName])
            self.signal_UndoRedoConnectNodes.emit(self, removedConnections, addedConnections)
            self.signal_UndoRedoDeleteSelectedNodes.emit(self, selected_nodes)
    
    
    def editNode(self, node, newName=None):
        """
        Rename an existing node.

        :type  node: class.
        :param node: The node instance that you want to delete.

        :type  newName: str.
        :param newName: The new name for the given node.

        """
        if not node in self.scene().nodes.values():
            print 'Node object does not exist !'
            print 'Node edition aborted !'
            return
        
        oldName = node.name
        
        if newName is not None:
            # Check for name clashes
            if newName in self.scene().nodes.keys():
                print 'A node with the same name already exists : {0}'.format(newName)
                print 'Node edition aborted !'
                return
            else:
                # oldName = node.name
                
                node.name = newName
                
                # Replace node data.
                self.scene().nodes[newName] = self.scene().nodes[oldName]
                self.scene().nodes.pop(oldName)
                
                # Store new node name in the connections
                if node.sockets:
                    for socket in node.sockets.values():
                        for connection in socket.connections:
                            connection.socketNode = newName
                
                if node.plugs:
                    for plug in node.plugs.values():
                        for connection in plug.connections:
                            connection.plugNode = newName
                
                node.update()
                
                # Emit signal.
                self.signal_NodeEdited.emit(oldName, newName)
                # editNode ot used in golaem, else needs an event
                # self.signal_UndoRedoEditNodeName.emit(self, oldName, newName)
    
    
    # ATTRS
    def createAttribute(self, node, name='default', index=-1, preset='attr_default', plug=True, socket=True,
                        dataType=None, plugMaxConnections=-1, socketMaxConnections=1):
        """
        Create a new attribute with a given name.

        :type  node: class.
        :param node: The node instance that you want to delete.

        :type  name: str.
        :param name: The name of the attribute. The name has to be
                     unique as it is used as a key to store the node
                     object.

        :type  index: int.
        :param index: The index of the attribute in the node.

        :type  preset: str.
        :param preset: The name of graphical preset in the config file.

        :type  plug: bool.
        :param plug: Whether or not this attribute can emit connections.

        :type  socket: bool.
        :param socket: Whether or not this attribute can receive
                       connections.

        :type  dataType: type.
        :param dataType: Type of the data represented by this attribute
                         in order to highlight attributes of the same
                         type while performing a connection.

        :type  plugMaxConnections: int.
        :param plugMaxConnections: The maximum connections that the plug can have (-1 for infinite).

        :type  socketMaxConnections: int.
        :param socketMaxConnections: The maximum connections that the socket can have (-1 for infinite).

        """
        if not node in self.scene().nodes.values():
            print 'Node object does not exist !'
            print 'Attribute creation aborted !'
            return
        
        if name in node.attrs:
            print 'An attribute with the same name already exists : {0}'.format(name)
            print 'Attribute creation aborted !'
            return
        
        node._createAttribute(name=name, index=index, preset=preset, plug=plug, socket=socket, dataType=dataType,
                              plugMaxConnections=plugMaxConnections, socketMaxConnections=socketMaxConnections)
        
        # Emit signal.
        self.signal_AttrCreated.emit(node.name, index)
    
    
    def deleteAttribute(self, node, index):
        """
        Delete the specified attribute.

        :type  node: class.
        :param node: The node instance that you want to delete.

        :type  index: int.
        :param index: The index of the attribute in the node.

        """
        if not node in self.scene().nodes.values():
            print 'Node object does not exist !'
            print 'Attribute deletion aborted !'
            return
        
        node._deleteAttribute(index)
        
        # Emit signal.
        self.signal_AttrDeleted.emit(node.name, index)
    
    
    def editAttribute(self, node, index, newName=None, newIndex=None):
        """
        Edit the specified attribute.

        :type  node: class.
        :param node: The node instance that you want to delete.

        :type  index: int.
        :param index: The index of the attribute in the node.

        :type  newName: str.
        :param newName: The new name for the given attribute.

        :type  newIndex: int.
        :param newIndex: The index for the given attribute.

        """
        if not node in self.scene().nodes.values():
            print 'Node object does not exist !'
            print 'Attribute creation aborted !'
            return
        
        if newName is not None:
            if newName in node.attrs:
                print 'An attribute with the same name already exists : {0}'.format(newName)
                print 'Attribute edition aborted !'
                return
            else:
                oldName = node.attrs[index]
            
            # Rename in the slot item(s).
            if node.attrsData[oldName]['plug']:
                node.plugs[oldName].attribute = newName
                node.plugs[newName] = node.plugs[oldName]
                node.plugs.pop(oldName)
                for connection in node.plugs[newName].connections:
                    connection.plugAttr = newName
            
            if node.attrsData[oldName]['socket']:
                node.sockets[oldName].attribute = newName
                node.sockets[newName] = node.sockets[oldName]
                node.sockets.pop(oldName)
                for connection in node.sockets[newName].connections:
                    connection.socketAttr = newName
            
            # Replace attribute data.
            node.attrsData[oldName]['name'] = newName
            node.attrsData[newName] = node.attrsData[oldName]
            node.attrsData.pop(oldName)
            node.attrs[index] = newName
        
        if isinstance(newIndex, int):
            utils._swapListIndices(node.attrs, index, newIndex)
            
            # Refresh connections.
            for plug in node.plugs.values():
                plug.update()
                if plug.connections:
                    for connection in plug.connections:
                        if isinstance(connection.source, PlugItem):
                            connection.source = plug
                            connection.source_point = plug.center()
                        else:
                            connection.target = plug
                            connection.target_point = plug.center()
                        if newName:
                            connection.plugAttr = newName
                        connection.updatePath()
            
            for socket in node.sockets.values():
                socket.update()
                if socket.connections:
                    for connection in socket.connections:
                        if isinstance(connection.source, SocketItem):
                            connection.source = socket
                            connection.source_point = socket.center()
                        else:
                            connection.target = socket
                            connection.target_point = socket.center()
                        if newName:
                            connection.socketAttr = newName
                        connection.updatePath()
            
            self.scene().update()
        
        node.update()
        
        # Emit signal.
        if newIndex:
            self.signal_AttrEdited.emit(node.name, index, newIndex)
        else:
            self.signal_AttrEdited.emit(node.name, index, index)
    
    
    # GRAPH
    def autoLayoutGraph(self, nodes=None, margin=50):
        """
        Auto set nodes positions in the graph according to their connections.

        """
        nodeWidth = 300  # default value, will be replaced by node.baseWidth + margin when iterating on the first node
        sceneNodes = self.scene().nodes.keys()
        if (nodes is None) or len(nodes) == 0:
            nodes = sceneNodes
        rootNodes = []
        alreadyVisitedNodes = []
        
        # root nodes (without connection on the plug)
        for nodeName in sceneNodes:
            node = self.scene().nodes[nodeName]
            if node is not None:
                nodeWidth = node.baseWidth + margin
                isRoot = True
                for plug in node.plugs.values():
                    isRoot &= (len(plug.connections) == 0)
                if isRoot:
                    rootNodes.append(node)
        
        maxGraphWidth = 0
        rootGraphs = [[[0 for _x in range(0)] for _y in range(0)] for _z in range(0)]
        for rootNode in rootNodes:
            rootGraph = [[0 for _x in range(0)] for _y in range(0)]
            rootGraph.append([rootNode])
            
            currentGraphLevel = 0
            doNextGraphLevel = True
            while (doNextGraphLevel):
                doNextGraphLevel = False
                for nodeI in range(len(rootGraph[currentGraphLevel])):
                    currentNode = rootGraph[currentGraphLevel][nodeI]
                    for attr in currentNode.attrs:
                        if attr in currentNode.sockets:
                            socket = currentNode.sockets[attr]
                            for connection in socket.connections:
                                connectedNode = connection.plugItem.parentItem()
                                if (connectedNode not in alreadyVisitedNodes):
                                    alreadyVisitedNodes.append(connectedNode)
                                    
                                    if len(rootGraph) <= (currentGraphLevel + 1):
                                        emptyArray = []
                                        rootGraph.append(emptyArray)
                                    rootGraph[currentGraphLevel + 1].append(connection.plugItem.parentItem())
                                    doNextGraphLevel = True
                currentGraphLevel += 1
            
            graphWidth = len(rootGraph) * (nodeWidth + margin)
            maxGraphWidth = max(graphWidth, maxGraphWidth)
            rootGraphs.append(rootGraph)
        
        # update scene rect if needed
        if maxGraphWidth > self.scene().width():
            sceneRect = self.scene().sceneRect()
            sceneRect.setWidth(maxGraphWidth)
            self.scene().setSceneRect(sceneRect)
        
        alreadyVisitedNodes = []
        baseYpos = margin
        
        nodesMovedList = list()
        fromPosList = list()
        toPosList = list()
        
        for rootGraph in rootGraphs:
            # set positions...
            currentXpos = max(0, 0.5 * (
                    self.scene().width() - maxGraphWidth)) + maxGraphWidth - nodeWidth  # middle of the view
            nextBaseYpos = baseYpos
            for nodesAtLevel in rootGraph:
                currentYpos = baseYpos
                for node in nodesAtLevel:
                    if len(node.plugs) > 0:
                        if len(node.plugs.values()[0].connections) > 0:
                            parentPosition = node.plugs.values()[0].connections[0].socketItem.parentItem().pos()
                            currentXpos = parentPosition.x() - nodeWidth
                            # currentYpos = parentPosition.y()
                    if (node not in alreadyVisitedNodes) and (node.name in nodes):
                        alreadyVisitedNodes.append(node)
                        node_pos = QtCore.QPointF(currentXpos, currentYpos)
                        # check scene dimensions
                        shouldResize = False
                        sceneRect = self.scene().sceneRect()
                        if node_pos.x() < nodeWidth:
                            sceneRect.setWidth(self.scene().width() - node_pos.x() + nodeWidth + margin)
                            node_pos.setX(nodeWidth + margin)
                            shouldResize = True
                        if node_pos.x() + nodeWidth > self.scene().width():
                            sceneRect.setWidth(node_pos.x() + nodeWidth + margin)
                            shouldResize = True
                        if node_pos.y() < node.height:
                            sceneRect.setHeight(self.scene().height() - node_pos.y() + node.height + margin)
                            node_pos.setY(node.height + margin)
                            shouldResize = True
                        if node_pos.y() + node.height > self.scene().height():
                            sceneRect.setHeight(node_pos.y() + node.height + margin)
                            shouldResize = True
                        
                        if shouldResize:
                            self.scene().setSceneRect(sceneRect)
                        
                        if node_pos.x() < 0 or node_pos.x() > self.scene().width() or node_pos.y() < 0 or node_pos.y() > self.scene().height():
                            print "Warning: {0}: Invalid node position : ({1} ; {2}), frame dimension: ({3} ; {4}).".format(
                                node.name, node_pos.x(), node_pos.y(), self.scene().width(), self.scene().height())
                        
                        nodesMovedList.append(node.name)
                        fromPosList.append(node.pos())
                        node.setPos(node_pos)
                        node.checkIsWithinSceneRect()
                        # Emit signal.
                        self.signal_NodeMoved.emit(node.name, node.pos())
                        toPosList.append(node.pos())
                    
                    currentYpos += node.height + margin
                    nextBaseYpos = max(nextBaseYpos, currentYpos)
                currentXpos -= nodeWidth
            baseYpos = nextBaseYpos
        
        self.scene().updateScene()
        self.signal_UndoRedoMoveNodes.emit(self, nodesMovedList, fromPosList, toPosList)
    
    
    def saveGraph(self, filePath='path'):
        """
        Get all the current graph infos and store them in a .json file
        at the given location.

        :type  filePath: str.
        :param filePath: The path where you want to save your graph at.

        """
        data = dict()
        
        # Store nodes data.
        data['NODES'] = dict()
        
        nodes = self.scene().nodes.keys()
        for node in nodes:
            nodeInst = self.scene().nodes[node]
            preset = nodeInst.nodePreset
            nodeAlternate = nodeInst.alternate
            
            data['NODES'][node] = {'preset': preset,
                                   'position': [nodeInst.pos().x(), nodeInst.pos().y()],
                                   'alternate': nodeAlternate,
                                   'attributes': []}
            
            attrs = nodeInst.attrs
            for attr in attrs:
                attrData = nodeInst.attrsData[attr]
                
                # serialize dataType if needed.
                if isinstance(attrData['dataType'], type):
                    attrData['dataType'] = str(attrData['dataType'])
                
                data['NODES'][node]['attributes'].append(attrData)
        
        # Store connections data.
        data['CONNECTIONS'] = self.evaluateGraph()
        
        # Save data.
        try:
            utils._saveData(filePath=filePath, data=data)
        except:
            print 'Invalid path : {0}'.format(filePath)
            print 'Save aborted !'
            return False
        
        # Emit signal.
        self.signal_GraphSaved.emit()
    
    
    def loadGraph(self, filePath='path'):
        """
        Get all the stored info from the .json file at the given location
        and recreate the graph as saved.

        :type  filePath: str.
        :param filePath: The path where you want to load your graph from.

        """
        # Load data.
        if os.path.exists(filePath):
            data = utils._loadData(filePath=filePath)
        else:
            print 'Invalid path : {0}'.format(filePath)
            print 'Load aborted !'
            return False
        
        # Apply nodes data.
        nodesData = data['NODES']
        nodesName = nodesData.keys()
        
        for name in nodesName:
            preset = nodesData[name]['preset']
            position = nodesData[name]['position']
            position = QtCore.QPointF(position[0], position[1])
            alternate = nodesData[name]['alternate']
            
            node = self.createNode(name=name,
                                   preset=preset,
                                   position=position,
                                   alternate=alternate)
            
            # Apply attributes data.
            attrsData = nodesData[name]['attributes']
            
            for attrData in attrsData:
                index = attrsData.index(attrData)
                name = attrData['name']
                plug = attrData['plug']
                socket = attrData['socket']
                preset = attrData['preset']
                dataType = attrData['dataType']
                plugMaxConnections = 1  # default before plugMaxConnections
                if ('plugMaxConnections' in attrData):
                    plugMaxConnections = attrData['plugMaxConnections']
                socketMaxConnections = -1
                if ('socketMaxConnections' in attrData):
                    socketMaxConnections = attrData['socketMaxConnections']
                
                # un-serialize data type if needed
                if (isinstance(dataType, unicode) and dataType.find('<') == 0):
                    dataType = eval(str(dataType.split('\'')[1]))
                
                self.createAttribute(node=node,
                                     name=name,
                                     index=index,
                                     preset=preset,
                                     plug=plug,
                                     socket=socket,
                                     dataType=dataType,
                                     plugMaxConnections=plugMaxConnections,
                                     socketMaxConnections=socketMaxConnections
                                     )
        
        # Apply connections data.
        connectionsData = data['CONNECTIONS']
        
        for connection in connectionsData:
            source = connection[0]
            sourceNode = source.split('.')[0]
            sourceAttr = source.split('.')[1]
            
            target = connection[1]
            targetNode = target.split('.')[0]
            targetAttr = target.split('.')[1]
            
            plugItem = self.scene().nodes[sourceNode].plugs[sourceAttr]
            socketItem = self.scene().nodes[targetNode].sockets[targetAttr]
            
            if (socketItem.accepts(plugItem)):
                self.createConnection(sourceNode, sourceAttr,
                                      targetNode, targetAttr)
        
        self.scene().update()
        
        # Emit signal.
        self.signal_GraphLoaded.emit()
    
    
    def removeConnectionByInfo(self, connectionInfo):
        for item in self.scene().items():
            if (isinstance(item, ConnectionItem)):
                if (
                        item.plugNode == connectionInfo.plugNode and item.plugAttr == connectionInfo.plugAttr and item.socketNode == connectionInfo.socketNode and item.socketAttr == connectionInfo.socketAttr):
                    item._remove()
    
    
    def createConnectionByInfo(self, connectionInfo):
        self.createConnection(connectionInfo.plugNode, connectionInfo.plugAttr, connectionInfo.socketNode,
                              connectionInfo.socketAttr)
    
    
    def createConnection(self, sourceNode, sourceAttr, targetNode, targetAttr):
        """
        Create a manual connection.

        :type  sourceNode: str.
        :param sourceNode: Node that emits the connection.

        :type  sourceAttr: str.
        :param sourceAttr: Attribute that emits the connection.

        :type  targetNode: str.
        :param targetNode: Node that receives the connection.

        :type  targetAttr: str.
        :param targetAttr: Attribute that receives the connection.

        """
        plug = self.scene().nodes[sourceNode].plugs[sourceAttr]
        socket = self.scene().nodes[targetNode].sockets[targetAttr]
        
        connection = ConnectionItem(plug.center(), socket.center(), plug, socket)
        
        connection.plugNode = plug.parentItem().name
        connection.plugAttr = plug.attribute
        connection.socketNode = socket.parentItem().name
        connection.socketAttr = socket.attribute
        
        plug.connect(socket, connection)
        socket.connect(plug, connection)
        
        connection.updatePath()
        
        self.scene().addItem(connection)
        
        return connection
    
    
    def evaluateGraph(self):
        """
        Create a list of connection tuples.
        [("sourceNode.attribute", "TargetNode.attribute"), ...]

        """
        scene = self.scene()
        
        data = list()
        
        for item in scene.items():
            if isinstance(item, ConnectionItem):
                connection = item
                
                data.append(connection._outputConnectionData())
        
        # Emit Signal
        self.signal_GraphEvaluated.emit()
        
        return data
    
    
    def clearGraph(self):
        """
        Clear the graph.

        """
        self.cutTool = None
        self.scene().clear()
        self.scene().nodes = dict()
        
        # Emit signal.
        self.signal_GraphCleared.emit()
    
    ##################################################################
    # END API
    ##################################################################


class NodeScene(QtWidgets.QGraphicsScene):
    """
    The scene displaying all the nodes.

    """
    signal_NodeMoved = QtCore.Signal(str, object)
    
    
    def __init__(self, parent):
        """
        Initialize the class.

        """
        super(NodeScene, self).__init__(parent)
        
        # General.
        self.gridSize = parent.config['grid_size']
        
        map = QtGui.QPixmap(self.gridSize, self.gridSize)
        gridBGColor = utils._convertDataToColor(parent.config['grid_background_color'])
        map.fill(gridBGColor)
        painter = QtGui.QPainter()
        painter.begin(map)
        gridColor = utils._convertDataToColor(parent.config['grid_color'])
        painter.setPen(gridColor)
        painter.drawRect(QtCore.QRectF(0, 0, self.gridSize, self.gridSize))
        painter.end()
        
        self.parent().setDragMode(QtWidgets.QGraphicsView.NoDrag)
        # self.setDragMode(QtWidgets.QGraphicsView.NoDrag)
        
        self.gridBrush = QtGui.QBrush()
        self.gridBrush.setTexture(map)
        
        # Nodes storage.
        self.nodes = dict()
        self.userData = None  # handled by user, won't be read nor written by Nodz
    
    
    def dragEnterEvent(self, event):
        """
        Make the dragging of nodes into the scene possible.

        """
        if (self.parent().editEnabled):
            event.setDropAction(QtCore.Qt.MoveAction)
        event.accept()
    
    
    def dragMoveEvent(self, event):
        """
        Make the dragging of nodes into the scene possible.

        """
        if (self.parent().editEnabled):
            event.setDropAction(QtCore.Qt.MoveAction)
        event.accept()
    
    
    def dropEvent(self, event):
        """
        Create a node from the dropped item.

        """
        # Emit signal.
        if (self.parent().editEnabled):
            self.signal_Dropped.emit(event.scenePos())
        event.accept()
    
    
    def drawBackground(self, painter, rect):
        """
        Draw a grid in the background.

        """
        if self.views()[0].gridVisToggle:
            
            nodzInst = self.parent()
            
            painter.save()
            backgroundRect = QtCore.QRectF(nodzInst.viewport().rect())
            
            painterTransform = painter.transform()
            painter.resetTransform()
            
            painterTranslation = QtCore.QPointF(painterTransform.dx(), painterTransform.dy())
            
            # Translate the painter during the scrollHandDrag mode only. Note : Glitches when starting zooming
            if (nodzInst.dragMode() == QtWidgets.QGraphicsView.ScrollHandDrag):
                painter.translate(painterTranslation)
                backgroundRect.translate(-painterTranslation)
            
            painter.fillRect(backgroundRect, self.gridBrush)
            
            painter.restore()
            
            # nodzInst = self.parent() #.views()[0]
            # # config = nodzInst.config
            
            # viewport_rect = QtCore.QRect(
            #     0, 0, nodzInst.viewport().width(), nodzInst.viewport().height())
            # visible_scene_rect = nodzInst.mapToScene(viewport_rect).boundingRect()
            
            # gridSize = self.gridSize * visible_scene_rect.width() / viewport_rect.width()
            
            # leftLine = rect.left() - rect.left() % gridSize
            # topLine = rect.top() - rect.top() % gridSize
            # lines = list()
            
            # i = int(leftLine)
            # while i < int(rect.right()):
            #     lines.append(QtCore.QLineF(i, rect.top(), i, rect.bottom()))
            #     i += gridSize
            
            # u = int(topLine)
            # while u < int(rect.bottom()):
            #     lines.append(QtCore.QLineF(rect.left(), u, rect.right(), u))
            #     u += gridSize
            
            # self.pen = QtGui.QPen()
            # config = self.parent().config
            # self.pen.setColor(utils._convertDataToColor(config['grid_color']))
            # self.pen.setWidth(0)
            # painter.setPen(self.pen)
            # painter.drawLines(lines)
    
    
    def updateScene(self):
        """
        Update the connections position.

        """
        for connection in [i for i in self.items() if isinstance(i, ConnectionItem)]:
            connection.target_point = connection.target.center()
            connection.source_point = connection.source.center()
            connection.updatePath()


class NodeItem(QtWidgets.QGraphicsItem):
    """
    A graphic representation of a node containing attributes.

    """
    
    
    def __init__(self, name, alternate, preset, config):
        """
        Initialize the class.

        :type  name: str.
        :param name: The name of the node. The name has to be unique
                     as it is used as a key to store the node object.

        :type  alternate: bool.
        :param alternate: The attribute color alternate state, if True,
                          every 2 attribute the color will be slightly
                          darker.

        :type  preset: str.
        :param preset: The name of graphical preset in the config file.

        """
        super(NodeItem, self).__init__()
        
        self.baseZValue = 1
        self.setZValue(self.baseZValue)
        
        # Storage
        self.name = name
        self.alternate = alternate
        self.nodePreset = preset
        self.attrPreset = None
        
        # Attributes storage.
        self.attrs = list()
        self.attrsData = dict()
        self.attrCount = 0
        self.currentDataType = None
        self.userData = None  # handled by user, won't be read nor written by Nodz
        
        self.plugs = dict()
        self.sockets = dict()
        
        self.attributeBeingPlugged = None
        self.lastMousePressPos = None
        self.acceptNodeDrop = False
        
        self.icon = None
        self.scaledIcon = None
        self.usingSquareDisplay = False
        
        # Methods.
        self._createStyle(config)
    
    
    @property
    def height(self):
        """
        Increment the final height of the node every time an attribute
        is created.

        """
        aHeight = self.baseHeight
        if self.attrCount > 0:
            aHeight += self.attrHeight * self.attrCount + self.border + 0.5 * self.radius
        
        if (self.usingSquareDisplay):
            aHeight = max(self.baseWidth, aHeight)
        
        return aHeight
    
    
    @property
    def pen(self):
        """
        Return the pen based on the selection state of the node.

        """
        nodzInst = self.scene().views()[0]
        if self.isSelected():
            return self._penSel
        elif self is nodzInst.currentHoveredNodeForDrop:
            return self._penHover
        else:
            return self._pen
    
    
    def _createStyle(self, config):
        """
        Read the node style from the configuration file.

        """
        self.setAcceptHoverEvents(True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable)
        
        # Dimensions.
        self.baseWidth = config['node_width']
        self.baseHeight = config['node_height']
        self.attrHeight = config['node_attr_height']
        self.border = config['node_border']
        self.radius = config['node_radius']
        
        self.nodeCenter = QtCore.QPointF()
        self.nodeCenter.setX(self.baseWidth / 2.0)
        self.nodeCenter.setY(self.height / 2.0)
        
        self._brush = QtGui.QBrush()
        self._brush.setStyle(QtCore.Qt.SolidPattern)
        self._brush.setColor(utils._convertDataToColor(config[self.nodePreset]['bg']))
        
        self._pen = QtGui.QPen()
        self._pen.setStyle(QtCore.Qt.SolidLine)
        self._pen.setWidth(self.border)
        self._pen.setColor(utils._convertDataToColor(config[self.nodePreset]['border']))
        
        self._penSel = QtGui.QPen()
        self._penSel.setStyle(QtCore.Qt.SolidLine)
        self._penSel.setWidth(self.border)
        self._penSel.setColor(utils._convertDataToColor(config[self.nodePreset]['border_sel']))
        
        # make link highlit
        self._penHover = QtGui.QPen()
        self._penHover.setStyle(QtCore.Qt.SolidLine)
        self._penHover.setWidth(self.border)
        self._penHover.setColor(utils._convertDataToColor(config[self.nodePreset]['border_sel']))
        
        self._textPen = QtGui.QPen()
        self._textPen.setStyle(QtCore.Qt.SolidLine)
        self._textPen.setColor(utils._convertDataToColor(config[self.nodePreset]['text']))
        
        self._nodeTextFont = QtGui.QFont(config['node_font'], config['node_font_size'], QtGui.QFont.Bold)
        self._attrTextFont = QtGui.QFont(config['attr_font'], config['attr_font_size'], QtGui.QFont.Normal)
        
        self._attrAlign = QtCore.Qt.AlignCenter
        self._attrVAlign = QtCore.Qt.AlignVCenter
        
        self._attrBrush = QtGui.QBrush()
        self._attrBrush.setStyle(QtCore.Qt.SolidPattern)
        
        self._attrBrushAlt = QtGui.QBrush()
        self._attrBrushAlt.setStyle(QtCore.Qt.SolidPattern)
        
        self._attrPen = QtGui.QPen()
        self._attrPen.setStyle(QtCore.Qt.SolidLine)
    
    
    def _createAttribute(self, name, index, preset, plug, socket, dataType, plugMaxConnections, socketMaxConnections):
        """
        Create an attribute by expanding the node, adding a label and
        connection items.

        :type  name: str.
        :param name: The name of the attribute. The name has to be
                     unique as it is used as a key to store the node
                     object.

        :type  index: int.
        :param index: The index of the attribute in the node.

        :type  preset: str.
        :param preset: The name of graphical preset in the config file.

        :type  plug: bool.
        :param plug: Whether or not this attribute can emit connections.

        :type  socket: bool.
        :param socket: Whether or not this attribute can receive
                       connections.

        :type  dataType: type.
        :param dataType: Type of the data represented by this attribute
                         in order to highlight attributes of the same
                         type while performing a connection.

        """
        if name in self.attrs:
            print 'An attribute with the same name already exists on this node : {0}'.format(name)
            print 'Attribute creation aborted !'
            return
        
        self.attrPreset = preset
        
        # Create a plug connection item.
        if plug:
            plugInst = PlugItem(parent=self,
                                attribute=name,
                                index=self.attrCount,
                                preset=preset,
                                dataType=dataType,
                                maxConnections=plugMaxConnections)
            
            self.plugs[name] = plugInst
        
        # Create a socket connection item.
        if socket:
            socketInst = SocketItem(parent=self,
                                    attribute=name,
                                    index=self.attrCount,
                                    preset=preset,
                                    dataType=dataType,
                                    maxConnections=socketMaxConnections)
            
            self.sockets[name] = socketInst
        
        self.attrCount += 1
        
        # Add the attribute based on its index.
        if index == -1 or index > self.attrCount:
            self.attrs.append(name)
        else:
            self.attrs.insert(index, name)
        
        # Store attr data.
        self.attrsData[name] = {'name': name,
                                'socket': socket,
                                'plug': plug,
                                'preset': preset,
                                'dataType': dataType,
                                'plugMaxConnections': plugMaxConnections,
                                'socketMaxConnections': socketMaxConnections
                                }
        
        # Update node height.
        self.update()
    
    
    def _deleteAttribute(self, index):
        """
        Remove an attribute by reducing the node, removing the label
        and the connection items.

        :type  index: int.
        :param index: The index of the attribute in the node.

        """
        name = self.attrs[index]
        
        # Remove socket and its connections.
        if name in self.sockets.keys():
            for connection in self.sockets[name].connections:
                connection._remove()
            
            self.scene().removeItem(self.sockets[name])
            self.sockets.pop(name)
        
        # Remove plug and its connections.
        if name in self.plugs.keys():
            for connection in self.plugs[name].connections:
                connection._remove()
            
            self.scene().removeItem(self.plugs[name])
            self.plugs.pop(name)
        
        # Reduce node height.
        if self.attrCount > 0:
            self.attrCount -= 1
        
        # Remove attribute from node.
        if name in self.attrs:
            self.attrs.remove(name)
        
        self.update()
    
    
    def updateNodeConnectionsPath(self):
        """
        Update the connections position.

        """
        for plug in self.plugs.values():
            for connection in plug.connections:
                if (connection.target is not None and connection.source is not None):
                    connection.target_point = connection.target.center()
                    connection.source_point = connection.source.center()
                    connection.updatePath()
        
        for socket in self.sockets.values():
            for connection in socket.connections:
                if (connection.target is not None and connection.source is not None):
                    connection.target_point = connection.target.center()
                    connection.source_point = connection.source.center()
                    connection.updatePath()
    
    
    def _disconnectAll(self):
        """
        Disconnect this node from all nodes of the scene

        """
        # reconnect if only one in and one out
        removedConnections = list()
        addedConnections = list()
        
        nodzInst = self.scene().views()[0]
        
        nodzInst.signal_StartCompoundInteraction.emit(nodzInst)
        
        selectionPlugConnectionItems = list()
        selectionSocketConnectionItems = list()
        
        # store connections before reconnecting in-out nodes, cause it will shunt incoming connection
        for selectedNode in nodzInst.selectedNodes:
            for socket in self.scene().nodes[
                selectedNode].sockets.values():  # Remove all sockets connections not in selection
                for iCon in range(0, len(socket.connections)):
                    if socket.connections[iCon].plugNode not in nodzInst.selectedNodes:
                        selectionPlugConnectionItems.append(socket.connections[iCon])
                        removedConnections.append(ConnectionInfo(socket.connections[iCon]))
            
            for plug in self.scene().nodes[selectedNode].plugs.values():  # Remove all plugs connections.
                for iCon in range(0, len(plug.connections)):
                    if plug.connections[iCon].socketNode not in nodzInst.selectedNodes:
                        selectionSocketConnectionItems.append(plug.connections[iCon])
                        removedConnections.append(ConnectionInfo(plug.connections[iCon]))
        
        if len(selectionPlugConnectionItems) == 1 and len(selectionSocketConnectionItems) == 1:
            plugItem = selectionPlugConnectionItems[0].plugItem
            socketItem = selectionSocketConnectionItems[0].socketItem
            
            # link previous plug to next socket
            if (socketItem.accepts(plugItem)):
                newConnection = nodzInst.createConnection(selectionPlugConnectionItems[0].plugNode,
                                                          selectionPlugConnectionItems[0].plugAttr,
                                                          selectionSocketConnectionItems[0].socketNode,
                                                          selectionSocketConnectionItems[0].socketAttr)
                addedConnections.append(ConnectionInfo(newConnection))
        
        # actually remove remaining connections
        for selectedNode in nodzInst.selectedNodes:
            for socket in self.scene().nodes[selectedNode].sockets.values():  # Remove all sockets connections.
                if len(socket.connections) > 0:
                    connectionIndex = len(socket.connections) - 1
                    while connectionIndex >= 0:
                        if socket.connections[connectionIndex].plugNode not in nodzInst.selectedNodes:
                            socket.connections[connectionIndex]._remove()
                        connectionIndex -= 1
        
        for selectedNode in nodzInst.selectedNodes:
            for plug in self.scene().nodes[selectedNode].plugs.values():  # Remove all plugs connections.
                if len(plug.connections) > 0:
                    connectionIndex = len(plug.connections) - 1
                    while connectionIndex >= 0:
                        if plug.connections[connectionIndex].socketNode not in nodzInst.selectedNodes:
                            plug.connections[connectionIndex]._remove()
                        connectionIndex -= 1
        
        if (len(removedConnections) > 0 or len(addedConnections) > 0):
            # for removedCon in removedConnections:
            #     print "stack undo Redo connections : Remove {}.{} to {}.{}".format(removedCon.plugNode, removedCon.plugAttr, removedCon.socketNode, removedCon.socketAttr )
            
            # for addedCon in addedConnections:
            #     print "stack undo Redo connections : Add {}.{} to {}.{}".format(addedCon.plugNode, addedCon.plugAttr, addedCon.socketNode, addedCon.socketAttr )
            
            # print('disconnectAll')
            nodzInst.signal_UndoRedoConnectNodes.emit(nodzInst, removedConnections, addedConnections)
            nodzInst.signal_EndCompoundInteraction.emit(nodzInst, True)
        else:
            nodzInst.signal_EndCompoundInteraction.emit(nodzInst, False)
    
    
    def _remove(self):
        """
        Remove this node instance from the scene.

        Make sure that all the connections to this node are also removed
        in the process

        """
        # Remove all sockets connections.
        for socket in self.sockets.values():
            while len(socket.connections) > 0:
                socket.connections[0]._remove()
        
        # Remove all plugs connections.
        for plug in self.plugs.values():
            while len(plug.connections) > 0:
                plug.connections[0]._remove()
        
        self.scene().nodes.pop(self.name)
        
        # Remove node.
        scene = self.scene()
        scene.removeItem(self)
        scene.update()
    
    
    def center(self):
        """
        Return The center of the Slot.

        """
        rect = self.boundingRect()
        center = QtCore.QPointF(rect.x() + rect.width() * 0.5,
                                rect.y() + rect.height() * 0.5)
        
        return self.mapToScene(center)
    
    
    def boundingRect(self):
        """
        The bounding rect based on the width and height variables.

        """
        rect = QtCore.QRect(0, 0, self.baseWidth, self.height)
        rect = QtCore.QRectF(rect)
        return rect
    
    
    def checkIsWithinSceneRect(self):
        """
        Resize scene if node position is outside of the scene

        """
        currentNodz = self.scene().parent()
        config = currentNodz.config
        baseResolution = [config["scene_width"], config["scene_height"]]
        borderMarginRatio = config["scene_marginRatio"]
        
        currentPos = self.pos()
        sceneRect = self.scene().sceneRect()
        rectHasChanged = False
        
        borderMarginWidth = (borderMarginRatio * baseResolution[0])
        borderMarginHeight = (borderMarginRatio * baseResolution[1])
        
        if currentPos.x() - borderMarginWidth < sceneRect.x():
            xBefore = sceneRect.x()
            sceneRect.setX(currentPos.x() - borderMarginWidth)
            xAfter = sceneRect.x()
            sceneRect.setWidth(sceneRect.width() + (xBefore - xAfter))
            rectHasChanged = True
        if currentPos.y() - borderMarginHeight < sceneRect.y():
            yBefore = sceneRect.y()
            sceneRect.setY(currentPos.y() - borderMarginHeight)
            yAfter = sceneRect.y()
            sceneRect.setHeight(sceneRect.height() + (yBefore - yAfter))
            rectHasChanged = True
        if currentPos.x() + borderMarginWidth > sceneRect.x() + sceneRect.width():
            sceneRect.setWidth(currentPos.x() - sceneRect.x() + borderMarginWidth)
            rectHasChanged = True
        if currentPos.y() + borderMarginHeight > sceneRect.y() + sceneRect.height():
            sceneRect.setHeight(currentPos.y() - sceneRect.y() + borderMarginHeight)
            rectHasChanged = True
        
        if rectHasChanged:
            self.scene().setSceneRect(sceneRect)
            self.updateNodeConnectionsPath()
    
    
    def getAttributeAtPos(self, scenePos):
        """
        return the attribute plug
        """
        # check that scenePos x is in node range :
        yPos = scenePos.y() - self.pos().y()
        if (yPos <= 0 or yPos > self.height):
            return None
        yPos = yPos - self.baseHeight + self.radius
        # if (yPos > 0): take banner as first attribute (easier to click for layout)
        yPos /= self.attrHeight
        attributeIndex = int(yPos)
        # yPos is now the attribute index, if any :
        if (yPos < self.attrCount):
            return self.attrs[attributeIndex]
        return None
    
    
    def getAttributePlugAtPos(self, scenePos):
        """
        return the attribute plug
        """
        if (len(self.plugs) == 1):
            return self.plugs.itervalues().next()
        attributeName = self.getAttributeAtPos(scenePos)
        if (attributeName is not None):
            # print "found plug for {}".format(attributeName)
            if attributeName in self.plugs.keys():
                return self.plugs[attributeName]
        # print "found no plug"
        return None
    
    
    def getAttributeSocketAtPos(self, scenePos):
        """
        return the attribute plug
        """
        if (len(self.sockets) == 1):
            return self.sockets.itervalues().next()
        attributeName = self.getAttributeAtPos(scenePos)
        if (attributeName is not None):
            # print "found socket for {}".format(attributeName)
            if attributeName in self.sockets.keys():
                return self.sockets[attributeName]
        # print "found no socket"
        return None
    
    
    def shape(self):
        """
        The shape of the item.

        """
        path = QtGui.QPainterPath()
        path.addRect(self.boundingRect())
        return path
    
    
    def paint(self, painter, option, widget):
        """
        Paint the node and attributes.

        """
        # Node base.
        painter.setBrush(self._brush)
        painter.setPen(self.pen)
        
        nodzInst = self.scene().views()[0]
        config = nodzInst.config
        
        viewport_rect = QtCore.QRect(0, 0, nodzInst.viewport().width(), nodzInst.viewport().height())
        visible_scene_rect = nodzInst.mapToScene(viewport_rect).boundingRect()
        nodeSizeInScreenPixels = self.baseWidth * viewport_rect.width() / visible_scene_rect.width()
        
        # displaying icon :
        
        attributesDisplayLimitPixOnScreen = config["attributes_display_limit"]
        titleDisplayLimitPixOnScreen = config["node_title_display_limit"]
        big_icon_display_limit = config["big_icon_display_limit"]
        
        if (nodeSizeInScreenPixels <= big_icon_display_limit):
            self.usingSquareDisplay = True
        else:
            self.usingSquareDisplay = False
        painter.drawRoundedRect(0, 0,
                                self.baseWidth,
                                self.height,
                                self.radius,
                                self.radius)
        
        # Node label.
        painter.setPen(self._textPen)
        painter.setFont(self._nodeTextFont)
        
        metrics = QtGui.QFontMetrics(painter.font())
        text_width = metrics.boundingRect(self.name).width() + 14
        text_height = metrics.boundingRect(self.name).height() + 14
        margin = (text_width - self.baseWidth) * 0.5
        textRect = QtCore.QRect(-margin,
                                -text_height,
                                text_width,
                                text_height)
        
        if (self.icon is not None):
            if (
                    nodeSizeInScreenPixels > big_icon_display_limit and nodeSizeInScreenPixels > titleDisplayLimitPixOnScreen):  # display beside the node title
                iconSize = 32
                margin = 4
                iconRect = QtCore.QRect(textRect.left() - (iconSize / 2),
                                        textRect.top() - (iconSize + margin) + text_height,
                                        iconSize, iconSize)
                self.icon.paint(painter, iconRect, QtCore.Qt.AlignCenter, QtGui.QIcon.Normal, QtGui.QIcon.On)
                
                textRect.setRect(textRect.left() + (iconSize / 2),
                                 textRect.top() - (iconSize - text_height + margin) / 2, textRect.width(),
                                 textRect.height())
            
            elif (nodeSizeInScreenPixels < big_icon_display_limit):
                iconSize = 128
                if (self.scaledIcon is None):
                    scaledPixmap2 = self.icon.pixmap(iconSize, iconSize).scaled(iconSize, iconSize,
                                                                                QtCore.Qt.KeepAspectRatio,
                                                                                QtCore.Qt.SmoothTransformation)
                    self.scaledIcon = QtGui.QIcon(scaledPixmap2)
                
                # center on node attributes
                iconRect = QtCore.QRect(0 + (self.baseWidth - iconSize) / 2,
                                        0 + (self.baseWidth - iconSize) / 2,
                                        iconSize, iconSize)
                
                self.scaledIcon.paint(painter, iconRect, QtCore.Qt.AlignCenter, QtGui.QIcon.Normal, QtGui.QIcon.On)
        
        if (nodeSizeInScreenPixels > titleDisplayLimitPixOnScreen):
            painter.drawText(textRect,
                             QtCore.Qt.AlignCenter,
                             self.name)
        
        # Attributes.
        if (nodeSizeInScreenPixels >= big_icon_display_limit):
            offset = 0
            for attr in self.attrs:
                
                # Attribute rect.
                rect = QtCore.QRect(self.border / 2,
                                    self.baseHeight - self.radius + offset,
                                    self.baseWidth - self.border,
                                    self.attrHeight)
                
                attrData = self.attrsData[attr]
                name = attr
                
                preset = attrData['preset']
                
                # Attribute base.
                self._attrBrush.setColor(utils._convertDataToColor(config[preset]['bg']))
                if self.alternate:
                    self._attrBrushAlt.setColor(
                        utils._convertDataToColor(config[preset]['bg'], True, config['alternate_value']))
                
                self._attrPen.setColor(utils._convertDataToColor([0, 0, 0, 0]))
                painter.setPen(self._attrPen)
                painter.setBrush(self._attrBrush)
                if (offset / self.attrHeight) % 2:
                    painter.setBrush(self._attrBrushAlt)
                
                painter.drawRect(rect)
                
                if (nodeSizeInScreenPixels > attributesDisplayLimitPixOnScreen):
                    
                    painter.setPen(utils._convertDataToColor(config[preset]['text']))
                    painter.setFont(self._attrTextFont)
                    
                    # Search non-connectable attributes.
                    if nodzInst.drawingConnection:
                        if self == nodzInst.currentHoveredNodeForConnection:
                            if (attrData['dataType'] != nodzInst.sourceSlot.dataType or
                                    (nodzInst.sourceSlot.slotType == 'plug' and attrData['socket'] == False or
                                     nodzInst.sourceSlot.slotType == 'socket' and attrData['plug'] == False)):
                                # Set non-connectable attributes color.
                                painter.setPen(utils._convertDataToColor(config['non_connectable_color']))
                    
                    textRect = QtCore.QRect(rect.left() + self.radius,
                                            rect.top(),
                                            rect.width() - 2 * self.radius,
                                            rect.height())
                    
                    painter.drawText(textRect, self._attrVAlign, name)
                
                offset += self.attrHeight
    
    
    def contextMenuEvent(self, event):
        if (self.scene().parent().editEnabled):
            self.scene().parent().signal_NodeContextMenuEvent.emit(event, self.name)
    
    
    def mousePressEvent(self, event):
        """
        Keep the selected node on top of the others.

        """
        # nodzInst = self.scene().views()[0]
        if (self.scene().parent().editEnabled):
            maxZValue = 0
            nodes = self.scene().nodes
            for node in nodes.values():
                node.setZValue(node.baseZValue)
                maxZValue = max(maxZValue, node.baseZValue)
            
            for item in self.scene().items():
                if isinstance(item, ConnectionItem):
                    item.setZValue(1)
            
            self.setZValue(maxZValue + 1)
            self.attributeBeingPlugged = None
            
            # if middle click, initiate a link from the current attribute
            if (event.button() == QtCore.Qt.MiddleButton):
                self.attributeBeingPlugged = self.getAttributePlugAtPos(event.scenePos())
                if (self.attributeBeingPlugged is not None):
                    self.attributeBeingPlugged.mousePressEvent(event)
            else:
                super(NodeItem, self).mousePressEvent(event)
                self.lastMousePressPos = self.pos()  # take position after potential node selection / edition which may change the layout
        else:
            super(NodeItem, self).mousePressEvent(event)
    
    
    def mouseDoubleClickEvent(self, event):
        """
        Emit a signal.

        """
        super(NodeItem, self).mouseDoubleClickEvent(event)
        
        if (self.scene().parent().editEnabled):
            self.scene().parent().signal_NodeDoubleClicked.emit(self.name)
    
    
    def mouseMoveEvent(self, event):
        """
        .

        """
        if (self.scene().parent().editEnabled):
            if (self.attributeBeingPlugged is not None):
                self.attributeBeingPlugged.mouseMoveEvent(event)
            else:
                if self.scene().views()[0].gridVisToggle:
                    if self.scene().views()[0].gridSnapToggle or self.scene().views()[0]._nodeSnap:
                        gridSize = self.scene().gridSize
                        
                        currentPos = self.mapToScene(event.pos().x() - self.baseWidth / 2,
                                                     event.pos().y() - self.height / 2)
                        
                        snap_x = (round(currentPos.x() / gridSize) * gridSize) - gridSize / 4
                        snap_y = (round(currentPos.y() / gridSize) * gridSize) - gridSize / 4
                        snap_pos = QtCore.QPointF(snap_x, snap_y)
                        self.setPos(snap_pos)
                        
                        self.scene().updateScene()
                    else:
                        self.scene().updateScene()
                        super(NodeItem, self).mouseMoveEvent(event)
                
                # Moving the node : is there a connectionItem around there to plug ourself
                nodzInst = self.scene().views()[0]
                config = nodzInst.config
                
                if event.modifiers() & QtCore.Qt.AltModifier:
                    self._disconnectAll()
                
                # Handle drop on link : highlight currently selected link if any, and only if nodeItem is a pass through (1 in 1 out)
                nodzInst.currentHoveredLink = None
                if (len(self.plugs) == 1 and len(self.sockets) == 1):
                    theNodePlug = self.plugs.itervalues().next()
                    theNodeSocket = self.sockets.itervalues().next()
                    plugConnections = theNodePlug.connections
                    socketConnections = theNodeSocket.connections
                    if (len(plugConnections) == 0 and len(socketConnections) == 0):
                        mbb = utils._createPointerBoundingBox(pointerPos=event.scenePos().toPoint(),
                                                              bbSize=config['mouse_bounding_box'])
                        hoveredItems = self.scene().items(mbb)
                        lowestDistance2 = 10000000000
                        for hoveredItem in hoveredItems:
                            if (isinstance(hoveredItem, ConnectionItem)):
                                # Check that link accepts plug-nodeSocket and nodePlug-socket connections
                                # use theNodeSocket to test accepts, as plugs must be empty / not at max connection
                                if (theNodeSocket.accepts(hoveredItem.plugItem) and theNodePlug.accepts(
                                        hoveredItem.socketItem)):
                                    fromScenePos = event.scenePos()
                                    toScenePos = hoveredItem.center()
                                    deltaPos = toScenePos - fromScenePos
                                    distance2 = deltaPos.x() * deltaPos.x() + deltaPos.y() * deltaPos.y()
                                    if (nodzInst.currentHoveredLink is None or distance2 < lowestDistance2):
                                        lowestDistance2 = distance2
                                        nodzInst.currentHoveredLink = hoveredItem
                
                nodzInst.currentHoveredNodeForDrop = None
                mbb = utils._createPointerBoundingBox(pointerPos=event.scenePos().toPoint(),
                                                      bbSize=config['mouse_bounding_box'])
                hoveredItems = self.scene().items(mbb)
                lowestDistance2 = 10000000000
                for hoveredItem in hoveredItems:
                    if (hoveredItem is not self and isinstance(hoveredItem, NodeItem) and hoveredItem.acceptNodeDrop):
                        fromScenePos = event.scenePos()
                        toScenePos = hoveredItem.center()
                        deltaPos = toScenePos - fromScenePos
                        distance2 = deltaPos.x() * deltaPos.x() + deltaPos.y() * deltaPos.y()
                        if (nodzInst.currentHoveredNodeForDrop is None or distance2 < lowestDistance2):
                            lowestDistance2 = distance2
                            nodzInst.currentHoveredNodeForDrop = hoveredItem
            
            self.checkIsWithinSceneRect()
        # else:
        #     super(NodeItem, self).mouseMoveEvent(event) # parent graphic item will move on mouseMoveEvent if not blocked
    
    
    def mouseReleaseEvent(self, event):
        """
        Emit signal_NodeMoved signal.

        """
        if (self.scene().parent().editEnabled):
            # Emit node moved signal.
            nodzInst = self.scene().views()[0]
            if (event.button() == QtCore.Qt.LeftButton):
                
                if (self.lastMousePressPos != self.pos()):
                    nodesMovedList = list()
                    fromPosList = list()
                    toPosList = list()
                    
                    deltaPosAdded = self.pos() - self.lastMousePressPos
                    if (nodzInst.selectedNodes is not None):
                        for selectedNode in nodzInst.selectedNodes:
                            selectedNodeInst = self.scene().nodes[selectedNode]
                            self.scene().signal_NodeMoved.emit(selectedNode, selectedNodeInst.pos())
                            nodesMovedList.append(selectedNode)
                            fromPosList.append(selectedNodeInst.pos() - deltaPosAdded)
                            toPosList.append(selectedNodeInst.pos())
                    # nodesMovedList.append(self)
                    # fromPosList.append()
                    # toPosList.append(self.pos())
                    
                    # print("move node {} from {} to {}".format(self.name, self.lastMousePressPos, self.pos()))
                    
                    # if currentHoveredNodeForDrop is not None, we drop node on other node : don't care about "moving" i
                    if nodzInst.currentHoveredNodeForDrop is None:
                        nodzInst.signal_UndoRedoMoveNodes.emit(nodzInst, nodesMovedList, fromPosList, toPosList)
                    
                    # handle connection if dropped an unconnected "pass through" node on a link
                    if nodzInst.currentHoveredLink is not None:
                        fromNode = nodzInst.currentHoveredLink.plugNode
                        fromAttr = nodzInst.currentHoveredLink.plugAttr
                        toNode = nodzInst.currentHoveredLink.socketNode
                        toAttr = nodzInst.currentHoveredLink.socketAttr
                        
                        theNodePlugAttr = self.plugs.itervalues().next().attribute
                        theNodeSocketAttr = self.sockets.itervalues().next().attribute
                        
                        removedConnections = list()
                        addedConnections = list()
                        
                        # pack the layout update call in a single call
                        nodzInst.signal_StartCompoundInteraction.emit(nodzInst)
                        removedConnections.append(ConnectionInfo(nodzInst.currentHoveredLink))
                        nodzInst.currentHoveredLink._remove()
                        
                        addedConnections.append(
                            ConnectionInfo(nodzInst.createConnection(fromNode, fromAttr, self.name, theNodeSocketAttr)))
                        addedConnections.append(
                            ConnectionInfo(nodzInst.createConnection(self.name, theNodePlugAttr, toNode, toAttr)))
                        
                        nodzInst.signal_EndCompoundInteraction.emit(nodzInst, True)
                        
                        nodzInst.signal_UndoRedoConnectNodes.emit(nodzInst, removedConnections, addedConnections)
                    
                    if nodzInst.currentHoveredNodeForDrop is not None:
                        nodzInst.signal_dropOnNode.emit(nodzInst,
                                                        nodzInst.currentHoveredNodeForDrop.name)  # can get back selection from nodzInst
            
            elif (event.button() == QtCore.Qt.MiddleButton):
                if (self.attributeBeingPlugged is not None):
                    self.attributeBeingPlugged.mouseReleaseEvent(event)
                elif nodzInst.currentHoveredLink is not None:
                    fromNode = nodzInst.currentHoveredLink.plugNode
                    fromAttr = nodzInst.currentHoveredLink.plugAttr
                    toNode = nodzInst.currentHoveredLink.socketNode
                    toAttr = nodzInst.currentHoveredLink.plugAttr
                    
                    theNodePlugAttr = self.plugs.itervalues().next().key()
                    theNodeSocketAttr = self.sockets.itervalues().next()().key()
                    
                    removedConnections = list()
                    addedConnections = list()
                    
                    removedConnections.append(ConnectionInfo(nodzInst.currentHoveredLink))
                    nodzInst.currentHoveredLink._remove()
                    
                    addedConnections.append(
                        ConnectionInfo(nodzInst.createConnection(fromNode, fromAttr, self, theNodeSocketAttr)))
                    addedConnections.append(
                        ConnectionInfo(nodzInst.createConnection(self, theNodePlugAttr, toNode, toAttr)))
                    
                    nodzInst.signal_UndoRedoConnectNodes.emit(nodzInst, removedConnections, addedConnections)
            
            # if(event.button() == QtCore.Qt.RightButton):
            #     self.scene().parent().signal_NodeRightClicked.emit(self.name)
            
            self.attributeBeingPlugged = None
            
            if (nodzInst.currentHoveredNodeForDrop is None):
                super(NodeItem, self).mouseReleaseEvent(event)
            
            nodzInst.currentHoveredNodeForDrop = None
            nodzInst.currentHoveredLink = None
            self.setZValue(self.baseZValue)  # restore the base Z order (notes behind, other ndoes in front...)
        # else:
        #     super(NodeItem, self).mouseReleaseEvent(event)
    
    
    def hoverLeaveEvent(self, event):
        """
        .

        """
        if (self.scene().parent().editEnabled):
            nodzInst = self.scene().views()[0]
            
            for item in nodzInst.scene().items():
                if isinstance(item, ConnectionItem):
                    item.setZValue(0)
        
        super(NodeItem, self).hoverLeaveEvent(event)


class SlotItem(QtWidgets.QGraphicsItem):
    """
    The base class for graphics item representing attributes hook.

    """
    
    
    def __init__(self, parent, attribute, preset, index, dataType, maxConnections):
        """
        Initialize the class.

        :param parent: The parent item of the slot.
        :type  parent: QtWidgets.QGraphicsItem instance.

        :param attribute: The attribute associated to the slot.
        :type  attribute: String.

        :param index: int.
        :type  index: The index of the attribute in the node.

        :type  preset: str.
        :param preset: The name of graphical preset in the config file.

        :param dataType: The data type associated to the attribute.
        :type  dataType: Type.

        """
        super(SlotItem, self).__init__(parent)
        
        # Status.
        self.setAcceptHoverEvents(True)
        
        # Storage.
        self.slotType = None
        self.attribute = attribute
        self.preset = preset
        self.index = index
        self.dataType = dataType
        
        # Style.
        self.brush = QtGui.QBrush()
        self.brush.setStyle(QtCore.Qt.SolidPattern)
        
        self.pen = QtGui.QPen()
        self.pen.setStyle(QtCore.Qt.SolidLine)
        
        # Connections storage.
        self.connected_slots = list()
        self.newConnection = None
        self.connections = list()
        self.maxConnections = maxConnections
    
    
    def accepts(self, slot_item):
        """
        Only accepts plug items that belong to other nodes, and only if the max connections count is not reached yet.

        """
        # no plug on plug or socket on socket
        thePlugItem = None
        theSocketItem = None
        
        if isinstance(self, PlugItem):
            thePlugItem = self
        if isinstance(slot_item, PlugItem):
            thePlugItem = slot_item
        
        if isinstance(self, SocketItem):
            theSocketItem = self
        if isinstance(slot_item, SocketItem):
            theSocketItem = slot_item
        
        if thePlugItem is None or theSocketItem is None:
            return False
        
        # no self connection
        if self.parentItem() == slot_item.parentItem():
            return False
        
        # no more than maxConnections
        if self.maxConnections > 0 and len(self.connected_slots) >= self.maxConnections:
            return False
        
        # no connection with different types
        if slot_item.dataType != self.dataType:
            return False
        
        # if loop forbidden, the plug/source node should not be already connected to target via its source nodes
        nodzInst = self.scene().views()[0]
        if not nodzInst.allowLoop:
            validConnection = True
            processedNodes = list()
            nodesToProcess = list()
            nextNodesToProcess = list()
            
            processedNodes.append(theSocketItem.parentItem().name)  # forbid target node in parents
            nodesToProcess.append(thePlugItem.parentItem())  # check parents from sourceNode
            
            while (not len(nodesToProcess) == 0 and validConnection):
                for nodeToProcess in nodesToProcess:
                    processedNodes.append(nodeToProcess.name)
                    for socket in nodeToProcess.sockets.values():
                        for connection in socket.connections:
                            if connection.plugNode in processedNodes:
                                validConnection = validConnection and connection.plugNode != processedNodes[
                                    0]  # processedNodes[0] is theSocketItem.parentItem()
                            else:
                                nextNodesToProcess.append(self.scene().nodes[
                                                              connection.plugNode])  # may be stacked several times in nextNodesToProcess, but will be skipped later by processedNodes test
                        if not validConnection:
                            break
                nodesToProcess = nextNodesToProcess[:]
                nextNodesToProcess[:] = []
                # del nodesToProcess[:]
            if not validConnection:
                print "This Connection would make a loop, this is forbidden"
                return
        
        # otherwise, all fine.
        return True
    
    
    def mousePressEvent(self, event):
        """
        Start the connection process.

        """
        if (self.scene().parent().editEnabled):
            if event.button() == QtCore.Qt.LeftButton or event.button() == QtCore.Qt.MiddleButton:
                self.newConnection = ConnectionItem(self.center(),
                                                    self.mapToScene(event.pos()),
                                                    self,
                                                    None)
                
                self.connections.append(self.newConnection)
                self.scene().addItem(self.newConnection)
                
                nodzInst = self.scene().views()[0]
                nodzInst.drawingConnection = True
                nodzInst.sourceSlot = self
                nodzInst.currentDataType = self.dataType
            else:
                super(SlotItem, self).mousePressEvent(event)
        else:
            super(SlotItem, self).mousePressEvent(event)
    
    
    def mouseMoveEvent(self, event):
        """
        Update the new connection's end point position.

        """
        if (self.scene().parent().editEnabled):
            nodzInst = self.scene().views()[0]
            config = nodzInst.config
            if nodzInst.drawingConnection:
                mbb = utils._createPointerBoundingBox(pointerPos=event.scenePos().toPoint(),
                                                      bbSize=config['mouse_bounding_box'])
                
                # Get nodes in pointer's bounding box.
                targets = self.scene().items(mbb)
                
                if any(isinstance(target, NodeItem) for target in targets):
                    if self.parentItem() not in targets:
                        for target in targets:
                            if isinstance(target, NodeItem):
                                nodzInst.currentHoveredNodeForConnection = target
                                eventScenePos = self.mapToScene(event.pos())
                                nodzInst.currentHoveredAttribute = nodzInst.currentHoveredNodeForConnection.getAttributeAtPos(
                                    eventScenePos)
                
                else:
                    nodzInst.currentHoveredNodeForConnection = None
                    nodzInst.currentHoveredAttribute = None
                
                # Set connection's end point.
                self.newConnection.target_point = self.mapToScene(event.pos())
                self.newConnection.updatePath()
            else:
                super(SlotItem, self).mouseMoveEvent(event)
        else:
            super(SlotItem, self).mouseMoveEvent(event)
    
    
    def mouseReleaseEvent(self, event):
        """
        Apply the connection if target_slot is valid.

        """
        if (self.scene().parent().editEnabled):
            nodzInst = self.scene().views()[0]
            if event.button() == QtCore.Qt.LeftButton or event.button() == QtCore.Qt.MiddleButton:
                nodzInst.drawingConnection = False
                nodzInst.currentDataType = None
                
                target = self.scene().itemAt(event.scenePos().toPoint(), QtGui.QTransform())
                
                if isinstance(target, NodeItem):
                    target = target.getAttributeSocketAtPos(event.scenePos())
                
                if not isinstance(target, SlotItem):
                    self.newConnection._remove()
                    super(SlotItem, self).mouseReleaseEvent(event)
                    return
                
                if target.accepts(self):
                    self.newConnection.target = target
                    self.newConnection.source = self
                    self.newConnection.target_point = target.center()
                    self.newConnection.source_point = self.center()
                    
                    # Perform the ConnectionItem.
                    self.connect(target, self.newConnection)
                    target.connect(self, self.newConnection)
                    
                    self.newConnection.updatePath()
                    
                    removedConnections = list()
                    addedConnections = list()
                    addedConnections.append(ConnectionInfo(self.newConnection))
                    nodzInst.signal_UndoRedoConnectNodes.emit(nodzInst, removedConnections, addedConnections)
                
                else:
                    self.newConnection._remove()
            else:
                super(SlotItem, self).mouseReleaseEvent(event)
        else:
            super(SlotItem, self).mouseReleaseEvent(event)
        
        nodzInst.currentHoveredNodeForConnection = None
        nodzInst.currentHoveredNodeForDrop = None
        nodzInst.currentHoveredAttribute = None
        nodzInst.currentHoveredLink = None
    
    
    def shape(self):
        """
        The shape of the Slot is a circle.

        """
        path = QtGui.QPainterPath()
        path.addRect(self.boundingRect())
        return path
    
    
    def paint(self, painter, option, widget):
        """
        Paint the Slot.

        """
        painter.setBrush(self.brush)
        painter.setPen(self.pen)
        
        nodzInst = self.scene().views()[0]
        config = nodzInst.config
        if nodzInst.drawingConnection:
            if self.parentItem() == nodzInst.currentHoveredNodeForConnection:
                # non connectable by type
                painter.setBrush(utils._convertDataToColor(config['connection_color']))
                if (self.slotType == nodzInst.sourceSlot.slotType or self.dataType != nodzInst.sourceSlot.dataType):
                    painter.setBrush(utils._convertDataToColor(config['non_connectable_color']))
                else:
                    if (len(self.parentItem().sockets) == 1 or self.attribute == nodzInst.currentHoveredAttribute):
                        _penValid = QtGui.QPen()
                        _penValid.setStyle(QtCore.Qt.SolidLine)
                        _penValid.setWidth(2)
                        _penValid.setColor(QtGui.QColor(255, 255, 255, 255))
                        painter.setPen(_penValid)
                        painter.setBrush(utils._convertDataToColor(config['connection_sel_color']))
                        # painter.setBrush(self.brush)
        
        painter.drawEllipse(self.boundingRect())
    
    
    def center(self):
        """
        Return The center of the Slot.

        """
        rect = self.boundingRect()
        center = QtCore.QPointF(rect.x() + rect.width() * 0.5,
                                rect.y() + rect.height() * 0.5)
        
        return self.mapToScene(center)


class PlugItem(SlotItem):
    """
    A graphics item representing an attribute out hook.

    """
    
    
    def __init__(self, parent, attribute, index, preset, dataType, maxConnections):
        """
        Initialize the class.

        :param parent: The parent item of the slot.
        :type  parent: QtWidgets.QGraphicsItem instance.

        :param attribute: The attribute associated to the slot.
        :type  attribute: String.

        :param index: int.
        :type  index: The index of the attribute in the node.

        :type  preset: str.
        :param preset: The name of graphical preset in the config file.

        :param dataType: The data type associated to the attribute.
        :type  dataType: Type.

        """
        super(PlugItem, self).__init__(parent, attribute, preset, index, dataType, maxConnections)
        
        # Storage.
        self.attribute = attribute
        self.preset = preset
        self.slotType = 'plug'
        
        # Methods.
        self._createStyle(parent)
    
    
    def _createStyle(self, parent):
        """
        Read the attribute style from the configuration file.

        """
        config = parent.scene().views()[0].config
        self.brush = QtGui.QBrush()
        self.brush.setStyle(QtCore.Qt.SolidPattern)
        self.brush.setColor(utils._convertDataToColor(config[self.preset]['plug']))
    
    
    def boundingRect(self):
        """
        The bounding rect based on the width and height variables.

        """
        width = height = self.parentItem().attrHeight / 2.0
        
        nodzInst = self.scene().views()[0]
        config = nodzInst.config
        
        x = self.parentItem().baseWidth - (width / 2.0)
        y = (self.parentItem().baseHeight - config['node_radius'] +
             self.parentItem().attrHeight / 4 +
             self.parentItem().attrs.index(self.attribute) * self.parentItem().attrHeight)
        
        rect = QtCore.QRectF(QtCore.QRect(x, y, width, height))
        return rect
    
    
    def connect(self, socket_item, connection):
        """
        Connect to the given socket_item.

        """
        if self.maxConnections > 0 and len(self.connected_slots) >= self.maxConnections:
            # Already connected.
            self.connections[self.maxConnections - 1]._remove()
        
        # Populate connection.
        connection.plugItem = self
        connection.plugNode = self.parentItem().name
        connection.plugAttr = self.attribute
        connection.socketItem = socket_item
        connection.socketNode = socket_item.parentItem().name
        connection.socketAttr = socket_item.attribute
        
        # Add socket to connected slots.
        if socket_item in self.connected_slots:
            self.connected_slots.remove(socket_item)
        self.connected_slots.append(socket_item)
        
        # Add connection.
        if connection not in self.connections:
            self.connections.append(connection)
        
        # Emit signal.
        nodzInst = self.scene().views()[0]
        nodzInst.signal_PlugConnected.emit(connection.plugNode, connection.plugAttr, connection.socketNode,
                                           connection.socketAttr)
    
    
    def disconnect(self, connection):
        """
        Disconnect the given connection from this plug item.

        """
        # Emit signal.
        nodzInst = self.scene().views()[0]
        
        nodzInst.signal_PlugDisconnected.emit(connection.plugNode, connection.plugAttr, connection.socketNode,
                                              connection.socketAttr)
        
        # Remove connected socket from plug
        if connection.socketItem in self.connected_slots:
            self.connected_slots.remove(connection.socketItem)
        # Remove connection
        self.connections.remove(connection)


class SocketItem(SlotItem):
    """
    A graphics item representing an attribute in hook.

    """
    
    
    def __init__(self, parent, attribute, index, preset, dataType, maxConnections):
        """
        Initialize the socket.

        :param parent: The parent item of the slot.
        :type  parent: QtWidgets.QGraphicsItem instance.

        :param attribute: The attribute associated to the slot.
        :type  attribute: String.

        :param index: int.
        :type  index: The index of the attribute in the node.

        :type  preset: str.
        :param preset: The name of graphical preset in the config file.

        :param dataType: The data type associated to the attribute.
        :type  dataType: Type.

        """
        super(SocketItem, self).__init__(parent, attribute, preset, index, dataType, maxConnections)
        
        # Storage.
        self.attribute = attribute
        self.preset = preset
        self.slotType = 'socket'
        
        # Methods.
        self._createStyle(parent)
    
    
    def _createStyle(self, parent):
        """
        Read the attribute style from the configuration file.

        """
        config = parent.scene().views()[0].config
        self.brush = QtGui.QBrush()
        self.brush.setStyle(QtCore.Qt.SolidPattern)
        self.brush.setColor(utils._convertDataToColor(config[self.preset]['socket']))
    
    
    def boundingRect(self):
        """
        The bounding rect based on the width and height variables.

        """
        width = height = self.parentItem().attrHeight / 2.0
        
        nodzInst = self.scene().views()[0]
        config = nodzInst.config
        
        x = - width / 2.0
        y = (self.parentItem().baseHeight - config['node_radius'] +
             (self.parentItem().attrHeight / 4) +
             self.parentItem().attrs.index(self.attribute) * self.parentItem().attrHeight)
        
        rect = QtCore.QRectF(QtCore.QRect(x, y, width, height))
        return rect
    
    
    def connect(self, plug_item, connection):
        """
        Connect to the given plug item.

        """
        if self.maxConnections > 0 and len(self.connected_slots) >= self.maxConnections:
            # Already connected.
            self.connections[self.maxConnections - 1]._remove()
        
        # Populate connection.
        connection.socketItem = self
        connection.socketNode = self.parentItem().name
        connection.socketAttr = self.attribute
        connection.plugItem = plug_item
        connection.plugNode = plug_item.parentItem().name
        connection.plugAttr = plug_item.attribute
        
        # Add plug to connected slots.
        self.connected_slots.append(plug_item)
        
        # Add connection.
        if connection not in self.connections:
            self.connections.append(connection)
        
        # Emit signal.
        nodzInst = self.scene().views()[0]
        nodzInst.signal_SocketConnected.emit(connection.plugNode, connection.plugAttr, connection.socketNode,
                                             connection.socketAttr)
    
    
    def disconnect(self, connection):
        """
        Disconnect the given connection from this socket item.

        """
        # Emit signal.
        nodzInst = self.scene().views()[0]
        nodzInst.signal_SocketDisconnected.emit(connection.plugNode, connection.plugAttr, connection.socketNode,
                                                connection.socketAttr)
        
        # Remove connected plugs
        if connection.plugItem in self.connected_slots:
            self.connected_slots.remove(connection.plugItem)
        # Remove connections
        self.connections.remove(connection)


class ConnectionItem(QtWidgets.QGraphicsPathItem):
    """
    A graphics path representing a connection between two attributes.

    """
    
    
    def __init__(self, source_point, target_point, source, target):
        """
        Initialize the class.

        :param sourcePoint: Source position of the connection.
        :type  sourcePoint: QPoint.

        :param targetPoint: Target position of the connection
        :type  targetPoint: QPoint.

        :param source: Source item (plug or socket).
        :type  source: class.

        :param target: Target item (plug or socket).
        :type  target: class.

        """
        super(ConnectionItem, self).__init__()
        
        self.setZValue(1)
        self.lastSelected = False
        
        # Storage.
        self.socketNode = None
        self.socketAttr = None
        self.plugNode = None
        self.plugAttr = None
        
        self.source_point = source_point
        self.target_point = target_point
        self.source = source
        self.target = target
        
        self.plugItem = None
        self.socketItem = None
        
        self.movable_point = None
        
        self.data = tuple()
        
        # Methods.
        self._createStyle()
    
    
    @property
    def pen(self):
        """
        Return the pen based on the selection state of the node.

        """
        nodzInst = self.source.scene().views()[0]
        if self.isSelected():
            return self._penSel
        elif nodzInst.currentHoveredLink is self:
            return self._penHover
        else:
            return self._pen
    
    
    def paint(self, painter, option, widget):
        """
        Paint the node and attributes.

        """
        # handle selection change...
        isSelected = self.isSelected()
        if self.lastSelected != isSelected:
            self.updatePath()
            self.lastSelected = isSelected
        
        super(ConnectionItem, self).paint(painter, option, widget)
    
    
    def center(self):
        """
        Return The center of the Slot.

        """
        rect = self.boundingRect()
        center = QtCore.QPointF(rect.x() + rect.width() * 0.5,
                                rect.y() + rect.height() * 0.5)
        
        return self.mapToScene(center)
    
    
    def _createStyle(self):
        """
        Read the connection style from the configuration file.

        """
        config = self.source.scene().views()[0].config
        self.setAcceptHoverEvents(True)
        self.setZValue(-1)
        
        self._pen = QtGui.QPen(utils._convertDataToColor(config['connection_color']))
        self._pen.setWidth(config['connection_width'])
        
        # make link selectable + selection style
        self._penSel = QtGui.QPen(utils._convertDataToColor(config['connection_sel_color']))
        self._penSel.setWidth(config['connection_sel_width'])
        
        # make link highlit
        self._penHover = QtGui.QPen(utils._convertDataToColor(config['connection_color']))
        self._penHover.setWidth(config['connection_sel_width'])
        
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable)
    
    
    def _outputConnectionData(self):
        """
        .

        """
        return ("{0}.{1}".format(self.plugNode, self.plugAttr),
                "{0}.{1}".format(self.socketNode, self.socketAttr))
    
    
    def mousePressEvent(self, event):
        """
        Make connection in front of other items

        """
        nodzInst = self.scene().views()[0]
        
        for item in nodzInst.scene().items():
            if isinstance(item, ConnectionItem):
                item.setZValue(0)
        
        super(ConnectionItem, self).mousePressEvent(event)
    
    
    def _remove(self):
        """
        Remove this Connection from the scene.

        """
        if self.source is not None:
            self.source.disconnect(self)
        if self.target is not None:
            self.target.disconnect(self)
        
        scene = self.scene()
        scene.removeItem(self)
        scene.update()
    
    
    def updatePath(self):
        """
        Update the path.

        """
        self.setPen(self.pen)
        
        path = QtGui.QPainterPath()
        path.moveTo(self.source_point)
        dx = (self.target_point.x() - self.source_point.x()) * 0.5
        dy = self.target_point.y() - self.source_point.y()
        ctrl1 = QtCore.QPointF(self.source_point.x() + dx, self.source_point.y() + dy * 0)
        ctrl2 = QtCore.QPointF(self.source_point.x() + dx, self.source_point.y() + dy * 1)
        path.cubicTo(ctrl1, ctrl2, self.target_point)
        
        self.setPath(path)
