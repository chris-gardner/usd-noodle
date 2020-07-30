# usd-noodle
Pretty node graph showing dependencies of a USD file

![Screenshot](docs/usd_noodle_screenshot.png)

## Cloning

Make sure you clone with submodules. Like this:

```
cd /path/to/usd-noodle
git clone --recursive https://github.com/chris-gardner/usd-noodle.git
```

# Running from inside a DCC

For example, Houdini, which provides the USD libraries and PySide2 out of the box.

Make the usd-noodle directory is on your PYTHONPATH:

```
import sys
sys.path.append('/path/to/usd-noodle')
import usd_noodle
usd_noodle.main()
```

## Houdini
Don't attempt to run it from the script editor. Make a shelf button. You will cry less.

# Running from a commandline
Assuming you have a USD installation at $USD...

$PYTHONPATH will require $USD/lib/python along with some flavour of PyQt/PySide

$PATH will require $USD/lib and $USD/bin

```
python /path/to/usd-noodle/usd_noodle/app.py
```

## Arguments:
```
usage: app.py [-h] [-i USDFILE] [-t]
   
optional arguments:
  -h, --help            show this help message and exit
  -i USDFILE, --usdfile USDFILE
                        usd file to load
  -t, --textures        Load textures (ie, walk attributes)
```
