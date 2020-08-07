import argparse
import sys
import sys
import os.path

sys.path.append(os.path.join(os.path.dirname(__file__), "vendor"))

from Qt import QtWidgets, QtGui, QtCore
from app import *


def cli():
    
    parser = argparse.ArgumentParser()
    
    parser.add_argument('-i', '--usdfile', help='usd file to load')
    parser.add_argument('-t', '--textures', action='store_true', help="Load textures (ie, walk attributes)")
    args = parser.parse_args()

    app = QtWidgets.QApplication(sys.argv)
    win = main(args.usdfile, walk_attributes=args.textures)
    sys.exit(app.exec_())


if __name__ == "__main__":
    cli()
