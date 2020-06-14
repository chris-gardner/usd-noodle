import shutil
import os, os.path

from Qt import QtWidgets, QtCore, QtWidgets, QtGui


class TextViewer(QtWidgets.QDialog):
    def __init__(self, usdfile, parent=None):
        super(TextViewer, self).__init__(parent)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        
        self.settings = QtCore.QSettings("chrisg", "usd-dependency-graph-textview")
        
        self.usdfile = usdfile
        print 'usdfile', self.usdfile
        
        self.data = ''
        
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.setLayout(self.verticalLayout)
        
        self.toolbar = QtWidgets.QToolBar('Main')
        # self.saveAction = QtWidgets.QAction('Save', self)
        # self.toolbar.addAction(self.saveAction)
        
        self.verticalLayout.addWidget(self.toolbar)
        
        self.editor = QtWidgets.QPlainTextEdit()
        font = QtGui.QFont('Courier')
        # font.setPointSize(10)
        self.editor.setFont(font)
        self.editor.setTabStopWidth(40)
        
        self.verticalLayout.addWidget(self.editor)
        
        self.setWindowTitle(self.usdfile)
        
        if self.settings.value("geometry"):
            self.restoreGeometry(self.settings.value("geometry"))
        else:
            self.resize(900, 500)
        
        self.loadData()
    
    
    def closeEvent(self, *args, **kwargs):
        """
        Window close event. Saves preferences. Impregnates your dog.
        """
        
        self.settings.setValue("geometry", self.saveGeometry())
        self.deleteLater()
        
        super(TextViewer, self).closeEvent(*args)
    
    
    def cancel(self):
        self.dirty = False
        self.close()
    
    
    def loadData(self):
        fp = open(self.usdfile, 'r')
        self.data = fp.read()
        fp.close()
        
        self.editor.setPlainText(self.data)
        # make sure we reset the dirty state after setting the editor contents
        self.dirty = False
