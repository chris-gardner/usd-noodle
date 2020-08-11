## Installation

### Houdini 17.5+
Packages are the modern and convenient way to install third party Houdini addons!
* Download and expand the archive to somewhere on your drive
* Move "hoodle.json" into a houdini packages directoy (eg "~/houdini18.0/packages/" - if your Hou pref dir doesn't have
a "packages" folder, you can create it)
and edit the file to point to your hoodle folder on disk

### Houdini 17 and older
Lucky you! You get to modify your houdini.env file!
* Download and expand the archive to somewhere convenient on your drive
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