import sys
import os.path


sys.path.append(os.path.join(os.path.dirname(__file__), "vendor"))
from Qt import QtWidgets, QtGui, QtCore
from . import app


reload(app)


def main(*args, **kwargs):
    app.main(*args, **kwargs)
