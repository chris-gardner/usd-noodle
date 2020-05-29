import sys
import os.path


sys.path.append(os.path.join(os.path.dirname(__file__), "vendor"))
from Qt import QtWidgets, QtGui, QtCore
from app import *


reload(app)
