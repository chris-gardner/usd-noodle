#  ![Screenshot](docs/noodle_icon_64.png) usd-noodle

Pretty node graph showing dependencies of a USD file

![Screenshot](docs/usd_noodle_screenshot.png)


## Requirements

* Python 2.7 or 3.x
* USD build (19.x or later) for your python version
* PySide2 or PyQt5


## Cloning

Make sure you clone with submodules. Like this:

```
cd /path/to/somewhere
git clone --recursive https://github.com/chris-gardner/usd-noodle.git
```

## Running from inside a DCC

For example, Houdini, which provides the USD libraries and PySide2 out of the box.

Make the usd-noodle directory is on your PYTHONPATH:

```
import sys
sys.path.append('/path/to/somewhere/usd-noodle')
import usd_noodle
usd_noodle.main()
```

### Houdini
Aka "hoodle" -  a Houdini PythonPanel and basic LOPs integration are available.

Use these install instructions:
[Houdini Installation](https://github.com/chris-gardner/usd-noodle/tree/master/integrations/houdini)

## Running from a commandline
Assuming you have a USD installation at $USD...

$PYTHONPATH will require $USD/lib/python along with some flavour of PyQt/PySide

$PATH will require $USD/lib and $USD/bin

here's a sample bash script. PySide2 has already been installed to the python installation.
```
#!/bin/bash

export USD=/home/chrisg/usd-20.05-linux-x86_64-py36
export NOODLE=/home/chrisg/usd-noodle

export PYTHONPATH=$PYTHONPATH:$USD/lib/python::
export PATH=$PATH:$USD/lib:$USD/bin:

python3 $NOODLE/usd_noodle/
```

### Arguments:
```
usage: [-h] [-i USDFILE] [-t]
   
optional arguments:
  -h, --help            show this help message and exit
  -i USDFILE, --usdfile USDFILE
                        usd file to load
  -t, --textures        Load textures (ie, walk attributes)
```
