from __future__ import print_function

import shutil
import os, os.path
from functools import partial

from Qt import QtWidgets, QtCore, QtWidgets, QtGui
from pxr import Usd, Sdf, Ar, UsdUtils


class InfoPanel(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(InfoPanel, self).__init__(parent)
        
        self.usdfile = None
        
        self.build_ui()
    
    
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
        
        name_lay = QtWidgets.QHBoxLayout()
        self.verticalLayout.addLayout(name_lay)
        name_label = QtWidgets.QLabel("Name")
        name_lay.addWidget(name_label)
        self.name_edit = QtWidgets.QLineEdit()
        self.name_edit.setReadOnly(True)
        name_lay.addWidget(self.name_edit)
        
        path_lay = QtWidgets.QHBoxLayout()
        self.verticalLayout.addLayout(path_lay)
        path_label = QtWidgets.QLabel("Path")
        path_lay.addWidget(path_label)
        self.path_edit = QtWidgets.QLineEdit()
        self.path_edit.setReadOnly(True)
        path_lay.addWidget(self.path_edit)
        
        online_lay = QtWidgets.QHBoxLayout()
        self.verticalLayout.addLayout(online_lay)
        online_label = QtWidgets.QLabel("Online")
        online_lay.addWidget(online_label)
        self.online_edit = QtWidgets.QLineEdit()
        self.online_edit.setReadOnly(True)
        online_lay.addWidget(self.online_edit)
        
        spacer = QtWidgets.QSpacerItem(10, 10, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacer)
    
    
    def loadData(self, usdfile, info):
        self.usdfile = usdfile
        
        self.name_edit.setText(os.path.basename(self.usdfile))
        self.online_edit.setText('{}'.format(os.path.isfile(self.usdfile)))
        self.path_edit.setText(self.usdfile)
        
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
        
        icon = QtGui.QPixmap()
        icon.load(os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons", node_icon))
        self.type_label.setPixmap(icon.scaled(48, 48,
                                              QtCore.Qt.KeepAspectRatio,
                                              QtCore.Qt.SmoothTransformation)
                                  )
        self.type_edit.setText(info.get("type"))
        
        layer = Sdf.Layer.FindOrOpen(self.usdfile)
        if not layer:
            return
        # print(id, layer.realPath)
        root = layer.pseudoRoot
