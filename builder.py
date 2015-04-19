# Build the install mel file
import os

path = os.path.dirname(os.path.realpath(__file__))

src = os.path.join(path, "__init__.py")
dest = os.path.join(path, "build.mel")

with open(src, "r") as f:
    data = f.read()

data = "print \"HELLO\""

with open(dest, "w") as f:
    f.write("python(\"")
    f.write(data.replace("\"", "\\\""))
    f.write("\");")
