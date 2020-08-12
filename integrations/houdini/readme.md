## Installation

Naturally, you've [cloned the usd-noodle repo](https://github.com/chris-gardner/usd-noodle/blob/master/README.md)
 to somewhere on your disk (don't forget the submodules!)

### Houdini 17.5+
Packages are the modern and convenient way to install third party Houdini addons!
* Move "hoodle.json" into a houdini packages directoy (eg "~/houdini18.0/packages/" - if your Hou pref dir doesn't have
a "packages" folder, you can create it)
and edit "NOODLE" path to point to the usd-noodle folder on your disk

```
"NOODLE": "/path/to/usd-noodle"
```

### Houdini 17 and older
Lucky you! You get to modify your houdini.env file!
* Edit your houdini.env file (eg "~/houdini18.0/houdini.env") to add the hoodle path to the HOUDINI_PATH variable and 
and your PYTHONPATH.

For example:

```
NOODLE=/path/to/usd-noodle/
PYTHONPATH=PYTHONPATH;$NOODLE
HOUDINI_PATH=$HOUDINI_PATH;$NOODLE/integrations/hoodle;&
```

Always end the HOUDINI_PATH variable with an "&" - this ensures all the *actual* Houdini files get loaded.

Linux and Mac should use ":" as an envar seperator, windows should use ";".

## Usage
### Make a Noodle panel
You can create a pane tab with Noodle embedded. Click the + button on a pane tab and choose: 

```New Pane Tab Type -> USD -> USD-Noodle```

### LOPs / Solaris
Right click on a LOP node, choose ```LOP Actions -> Noodle Stage``` to load the current stage into a Noodle panel.
