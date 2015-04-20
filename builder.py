# Simple python mel droppable builder. Created by Jason Dixon 20/04/2015
import datetime
import os

path = os.path.dirname(os.path.realpath(__file__))

src = os.path.join(path, "__init__.py")
dest = os.path.join(path, "build.mel")

with open(src, "r") as f:
    data = f.read()


with open(dest, "w") as f:
    f.write("""// Simple Script Installer. Created 20/04/2015 Jason Dixon. Built on %s
// Edit the below:

$name = "testscript"; // Name of script (folder)
$shelf = "print \\"Shelf Works.\\""; // Code to go in a shelf icon (if any)
$auto = "print \\"This should be visible if it works.\\""; // Code in userSetup (if any)
$repo = "shot_pieces"; // Name of repo
$user = "internetimagery"; // Owner of repo

// DON'T CHANGE ANYTHING BELOW THIS LINE. :)
""" % datetime.date.today())
    f.write("""
python("%s");
""" % data.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", r"\n"))
