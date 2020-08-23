from __future__ import print_function

import shutil
import os, os.path
from functools import partial

from Qt import QtWidgets, QtCore, QtWidgets, QtGui
from pxr import Usd, Sdf, Ar, UsdUtils


left_pad = 80


class QHSeperationLine(QtWidgets.QFrame):
    def __init__(self):
        super(QHSeperationLine, self).__init__()
        self.setMinimumWidth(1)
        self.setFixedHeight(20)
        self.setFrameShape(QtWidgets.QFrame.HLine)
        self.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Minimum)


class GeneralEdit(QtWidgets.QWidget):
    # Signals
    valueChanged = QtCore.Signal(str, object)
    
    
    def __init__(self, label="Unknown", enabled=True, readOnly=False, toolTip=None, parent=None):
        QtWidgets.QWidget.__init__(self, parent)
        self.label = label
        self.enabled = enabled
        self.readOnly = readOnly
        self.toolTip = toolTip
        self.draw()
    
    
    def draw(self):
        # The upper layout holds the label, the value, and the "expand" button
        upperLayout = QtWidgets.QHBoxLayout()
        upperLayout.setContentsMargins(0, 0, 0, 0)
        # upperLayout.setSpacing(0)
        
        self.label = QtWidgets.QLabel(self.label, self)
        self.label.setMinimumWidth(left_pad)
        self.label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        if self.toolTip:
            self.label.setToolTip(self.toolTip)
        
        self.lineEdit = QtWidgets.QLineEdit(self)
        self.lineEdit.setAlignment(QtCore.Qt.AlignLeft)
        self.lineEdit.setEnabled(self.enabled)
        self.lineEdit.setReadOnly(self.readOnly)
        self.lineEdit.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        
        upperLayout.addWidget(self.label)
        upperLayout.addWidget(self.lineEdit)
        
        self.setLayout(upperLayout)
        
        # Chain signals out with property name and value
        self.lineEdit.editingFinished.connect(
            lambda: self.valueChanged.emit(self.label.text(), self.lineEdit.text()))
    
    
    def setValue(self, value):
        """
        A clean interface for setting the property value and emitting signals.
        """
        self.lineEdit.setText(str(value))


class StringAttrEdit(GeneralEdit):
    """
    An edit widget that is basically a general edit, but also stores the
    attribute object, dagNode we're associated with, and dag the node is a
    member of.
    """
    
    
    def __init__(self, label, value, parent=None, tooltip=None, enabled=True, readOnly=False):
        """
        """
        GeneralEdit.__init__(self,
                             label=label,
                             toolTip=tooltip,
                             enabled=enabled,
                             readOnly=readOnly,
                             parent=parent)
        self.setValue(value)


class FloatAttrEdit(StringAttrEdit):
    """
    An edit widget that is basically a general edit, but also stores the
    attribute object, dagNode we're associated with, and dag the node is a
    member of.
    """
    
    
    def __init__(self, label, value, parent=None, tooltip=None, enabled=True, readOnly=False):
        """
        """
        GeneralEdit.__init__(self,
                             label=label,
                             toolTip=tooltip,
                             enabled=enabled,
                             readOnly=readOnly,
                             parent=parent)
        self.setValue(value)
    
    
    def draw(self):
        upperLayout = QtWidgets.QHBoxLayout()
        upperLayout.setContentsMargins(0, 0, 0, 0)
        # upperLayout.setSpacing(0)
        
        self.label = QtWidgets.QLabel(self.label, self)
        self.label.setMinimumWidth(left_pad)
        self.label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        if self.toolTip:
            self.label.setToolTip(self.toolTip)
        
        self.lineEdit = QtWidgets.QDoubleSpinBox(self)
        self.lineEdit.setEnabled(self.enabled)
        self.lineEdit.setReadOnly(self.readOnly)
        self.lineEdit.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        
        upperLayout.addWidget(self.label)
        upperLayout.addWidget(self.lineEdit)
        
        self.setLayout(upperLayout)
        
        # Chain signals out with property name and value
        self.lineEdit.editingFinished.connect(
            lambda: self.valueChanged.emit(self.label.text(), self.lineEdit.value()))
    
    
    def setValue(self, value):
        """
        A clean interface for setting the property value and emitting signals.
        """
        self.value = value
        self.lineEdit.setValue(float(value))


class TextAttrEdit(StringAttrEdit):
    """
    An edit widget that is basically a general edit, but also stores the
    attribute object, dagNode we're associated with, and dag the node is a
    member of.
    """
    
    
    def __init__(self, label, value, parent=None, tooltip=None, enabled=True, readOnly=False):
        """
        """
        GeneralEdit.__init__(self,
                             label=label,
                             toolTip=tooltip,
                             enabled=enabled,
                             readOnly=readOnly,
                             parent=parent)
        self.setValue(value)
    
    
    def draw(self):
        upperLayout = QtWidgets.QHBoxLayout()
        upperLayout.setContentsMargins(0, 0, 0, 0)
        # upperLayout.setSpacing(0)
        
        self.label = QtWidgets.QLabel(self.label, self)
        self.label.setMinimumWidth(left_pad)
        self.label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignTop)
        if self.toolTip:
            self.label.setToolTip(self.toolTip)
        
        self.lineEdit = QtWidgets.QPlainTextEdit(self)
        self.lineEdit.setEnabled(self.enabled)
        self.lineEdit.setReadOnly(self.readOnly)
        self.lineEdit.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        
        upperLayout.addWidget(self.label)
        upperLayout.addWidget(self.lineEdit)
        
        self.setLayout(upperLayout)
        
        # Chain signals out with property name and value
        self.lineEdit.textChanged.connect(
            lambda: self.valueChanged.emit(self.label.text(), self.lineEdit.toPlainText()))
    
    
    def setValue(self, value):
        """
        A clean interface for setting the property value and emitting signals.
        """
        self.value = value
        self.lineEdit.setPlainText(value)


class ListAttrEdit(GeneralEdit):
    """
    An edit widget that is basically a general edit, but also stores the
    attribute object, dagNode we're associated with, and dag the node is a
    member of.
    """
    
    
    def __init__(self, label, value, parent=None, tooltip=None, enabled=True, readOnly=False):
        """
        """
        GeneralEdit.__init__(self,
                             label=label,
                             toolTip=tooltip,
                             enabled=enabled,
                             readOnly=readOnly,
                             parent=parent)
        self.setValue(value)
    
    
    def draw(self):
        upperLayout = QtWidgets.QHBoxLayout()
        upperLayout.setContentsMargins(0, 0, 0, 0)
        # upperLayout.setSpacing(0)
        
        self.label = QtWidgets.QLabel(self.label, self)
        self.label.setMinimumWidth(left_pad)
        self.label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignTop)
        if self.toolTip:
            self.label.setToolTip(self.toolTip)
        
        self.lineEdit = QtWidgets.QListWidget(self)
        self.lineEdit.setEnabled(self.enabled)
        self.lineEdit.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        
        upperLayout.addWidget(self.label)
        upperLayout.addWidget(self.lineEdit)
        
        self.setLayout(upperLayout)
    
    
    def setValue(self, values):
        """
        A clean interface for setting the property value and emitting signals.
        """
        self.value = values
        self.lineEdit.clear()
        for val in values:
            self.lineEdit.addItem(QtWidgets.QListWidgetItem(val))


class BoolAttrEdit(StringAttrEdit):
    """
    An edit widget that is basically a general edit, but also stores the
    attribute object, dagNode we're associated with, and dag the node is a
    member of.
    """
    
    
    def __init__(self, label, value, parent=None, tooltip=None, enabled=True, readOnly=False):
        """
        """
        GeneralEdit.__init__(self,
                             label=label,
                             toolTip=tooltip,
                             enabled=enabled,
                             readOnly=readOnly,
                             parent=parent)
        self.setValue(value)
    
    
    def draw(self):
        upperLayout = QtWidgets.QHBoxLayout()
        upperLayout.setContentsMargins(0, 0, 0, 0)
        # upperLayout.setSpacing(0)
        
        self.label = QtWidgets.QLabel(self.label, self)
        self.label.setMinimumWidth(left_pad)
        self.label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        if self.toolTip:
            self.label.setToolTip(self.toolTip)
        
        self.lineEdit = QtWidgets.QCheckBox(self)
        self.lineEdit.setEnabled(self.enabled)
        self.lineEdit.setEnabled(not self.readOnly)
        self.lineEdit.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        
        upperLayout.addWidget(self.label)
        upperLayout.addWidget(self.lineEdit)
        
        self.setLayout(upperLayout)
        
        # Chain signals out with property name and value
        self.lineEdit.stateChanged.connect(
            lambda: self.valueChanged.emit(self.label.text(), self.lineEdit.isChecked()))
    
    
    def setValue(self, value):
        """
        A clean interface for setting the property value and emitting signals.
        """
        self.value = value
        self.lineEdit.setChecked(bool(value))


class InfoPanel(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(InfoPanel, self).__init__(parent)
        
        self.usdfile = None
        
        self.build_ui()
    
    
    def clear(self):
        # Clear out all existing widgets
        while self.attrLayout.count():
            child = self.attrLayout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
    
    
    def build_ui(self):
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setContentsMargins(5, 5, 5, 5);
        self.setLayout(self.verticalLayout)
        
        type_lay = QtWidgets.QHBoxLayout()
        self.verticalLayout.addLayout(type_lay)
        self.type_label = QtWidgets.QLabel()
        self.type_label.setFixedWidth(48)
        self.type_label.setFixedHeight(48)
        type_lay.addWidget(self.type_label)
        self.type_edit = QtWidgets.QLabel()
        type_lay.addWidget(self.type_edit)
        
        self.attrLayout = QtWidgets.QVBoxLayout()
        self.attrLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.addLayout(self.attrLayout)
        
        spacer = QtWidgets.QSpacerItem(1, 1, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacer)
    
    
    def loadData(self, usdfile, info):
        if self.visibleRegion().isEmpty():
            # dont bother updating if the widget can't be seen
            return
        
        self.clear()
        
        filebase, fileext = os.path.splitext(usdfile)
        
        self.usdfile = usdfile
        
        self.attrLayout.addWidget(StringAttrEdit('Name', os.path.basename(self.usdfile), readOnly=True))
        self.attrLayout.addWidget(StringAttrEdit('Usage', info.get("count", 0), readOnly=True))
        
        # some node types don't represent files
        non_file_nodes = ['clip', 'variant', 'material']
        if not info.get("type") in non_file_nodes:
            file_online = os.path.isfile(self.usdfile)
            self.attrLayout.addWidget(BoolAttrEdit('Online', file_online, readOnly=True))
            
            if file_online:
                self.attrLayout.addWidget(
                    StringAttrEdit('Size', '{:.2f}mb'.format(os.path.getsize(self.usdfile) / 1024.0 / 1024.0),
                                   readOnly=True)
                )
            
            self.attrLayout.addWidget(StringAttrEdit('Path', self.usdfile, readOnly=True))
        
        node_icon = "sublayer.png"
        if info.get("type") == 'clip':
            node_icon = "clip.png"
        elif info.get("type") == 'payload':
            node_icon = "payload.png"
        elif info.get("type") == 'variant':
            node_icon = "variant.png"
        elif info.get("type") == 'specialize':
            node_icon = "specialize.png"
        elif info.get("type") == 'reference':
            node_icon = "reference.png"
        elif info.get("type") == 'tex':
            node_icon = "texture.png"
        elif info.get("type") == 'material':
            node_icon = "material.png"
        
        icon = QtGui.QPixmap()
        icon.load(os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons", node_icon))
        self.type_label.setPixmap(icon.scaled(48, 48,
                                              QtCore.Qt.KeepAspectRatio,
                                              QtCore.Qt.SmoothTransformation)
                                  )
        self.type_edit.setText(info.get("type"))
        
        self.attrLayout.addWidget(QHSeperationLine())
        
        if info.get("type") == 'variant':
            self.attrLayout.addWidget(StringAttrEdit('Variant Set', info.get("variant_set"), readOnly=True))
            self.attrLayout.addWidget(StringAttrEdit('Current', info.get("current_variant"), readOnly=True))
            self.attrLayout.addWidget(ListAttrEdit('Variants',
                                                   sorted(info.get("variants"), key=lambda x: x.lower()),
                                                   readOnly=True))
        
        if info.get("type") == 'tex':
            self.attrLayout.addWidget(StringAttrEdit('colorspace', info.get("colorspace"), readOnly=True))
        
        if info.get("type") == 'clip':
            self.attrLayout.addWidget(StringAttrEdit('clipSet', info.get("clipSet"), readOnly=True))
            self.attrLayout.addWidget(StringAttrEdit('primPath', info.get("primPath"), readOnly=True))
        
        elif info.get("type") == 'sublayer':
            self.attrLayout.addWidget(StringAttrEdit('specifier', info.get("specifier"), readOnly=True))
            self.attrLayout.addWidget(StringAttrEdit('defaultPrim', info.get("defaultPrim"), readOnly=True))
            self.attrLayout.addWidget(StringAttrEdit('PseudoRoot', info.get("PseudoRoot"), readOnly=True))
            self.attrLayout.addWidget(BoolAttrEdit('muted', info.get("muted"), readOnly=True))
        
        if 'RootPrims' in info:
            self.attrLayout.addWidget(StringAttrEdit('RootPrims', ','.join(info.get("RootPrims")), readOnly=True))
        
        if 'info' in info:
            self.attrLayout.addWidget(QHSeperationLine())
            info_dict = info.get("info")
            for key in info_dict:
                if key in ['comment', 'doc', 'documentation']:
                    self.attrLayout.addWidget(TextAttrEdit(key, info_dict[key], readOnly=True))
                else:
                    self.attrLayout.addWidget(StringAttrEdit(key, info_dict[key], readOnly=True))
        
        if not fileext.startswith(".usd"):
            return
