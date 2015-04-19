# Build the install mel file
import os

path = os.path.dirname(os.path.realpath(__file__))

src = os.path.join(path, "__init__.py")
src = os.path.join(path, "test.py")
dest = os.path.join(path, "build.mel")

with open(src, "r") as f:
    data = f.read()


with open(dest, "w") as f:
    f.write("""// Simple Script Installer. Created 20/04/2015 Jason Dixon.
// Edit the below:

$name = "clicktime"; // Name of script (folder)
$shelf = "print \\"code here\\"";
$auto = "print \\"hello\\""; // Code in userSetup (if any)
$repo = "shot_pieces"; // Name of repo
$user = "internetimagery"; // Owner of repo

// DON'T CHANGE ANYTHING BELOW THIS LINE. :)

""")
    f.write("python(\"")
    data = data.replace("\\", "\\\\")
    data = data.replace("\"", "\\\"")
    data = data.replace("\n", r"\n")
    f.write(data)
    f.write("\");")
