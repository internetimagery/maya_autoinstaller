# Automatically install script
from functools import wraps
import maya.cmds as cmds
import maya.mel as mel
import traceback
import zipfile
import urllib
import shutil
import json
import math
import sys
import re
import os


## UTILITY CLASSES
def getMelVars():
    """
    Grab user (and global) variables from Mel
    """
    var = {}
    var["scriptPath"] = mel.eval("internalVar -usd;")  # Script folder
    var["name"] = mel.eval("$tmp = $name")  # Name of the script (folder)
    var["shelf"] = mel.eval("$tmp = $shelf")  # Script to put in a shelf button (if any)
    var["auto"] = mel.eval("$tmp = $auto")  # Code to put in userSetup (if any)
    var["repo"] = mel.eval("$tmp = $repo")  # Name of repo
    var["user"] = mel.eval("$tmp = $user")  # Owner of repo
    var["shelfUI"] = mel.eval('$tmp = $gShelfTopLevel')  # UI element of the Maya shelf
    return var


def unique(item):
    """
    Only keep one Class in memory at a time.
    """
    items = {}

    @wraps(item)
    def UniqueItem(*args, **kwargs):
        if (item in items and sys.getrefcount(items[item]) < 3) or item not in items:
            items[item] = item(*args, **kwargs)
        return items[item]
    return UniqueItem


class call(object):
    """
    Generic callback for buttons to pass values
    """
    def __init__(s, func, *args, **kwargs):
            s.func = func
            s.args = args
            s.kwargs = kwargs

    def __call__(s, *args):
            return s.func(*s.args, **s.kwargs)


@unique
class Say(object):
    """
    Logging output
    """
    def __init__(s):
        s.log = {}
        s.prog = 0.0  # Progress. 0 - 100
    """
    Register somewhere to show output and update progress
    """
    def what(s, name, func):
        s.log[name] = s.log.get(name, [])
        s.log[name].append(func)
        return s
    """
    Update overall progress
    """
    def when(s, progress):
        s.prog += progress
        s.prog = 0 if s.prog < 0 else s.prog
        s.prog = 100 if 100 < s.prog else s.prog
        try:
            for func in s.log["update"]:
                func(s.prog)
        except (KeyError, TypeError) as e:
            print "Warning:", e
    """
    Output message
    """
    def it(s, message):
        print message
        try:
            if s.log:
                for func in s.log["log"]:
                    func(message)
        except (KeyError, TypeError) as e:
            print "Warning:", e
sayhold = Say()  # Keep Say alive


## Functionality
class MainWindow(object):
    """
    Main window. For selecting initial options and providing feedback
    """
    def __init__(s, title):
        s.GUI = {}
        s.title = title
        s.width = 500  # Width of window
        s.GUI["window"] = cmds.window(title="Script Installer", rtf=True, s=False, mnb=False, mxb=False, ret=True)
        s.GUI["wrapper"] = cmds.columnLayout(adjustableColumn=True, w=s.width)
        cmds.showWindow(s.GUI["window"])
        s._buildSelection()

    def _buildSelection(s):
        """
        Create Selection UI (main menu)
        """
        s._clearFrame()
        s.GUI["layout1"] = cmds.columnLayout(adjustableColumn=True, w=s.width)
        s.GUI["text1"] = cmds.text(label="Features for %s." % s.title)
        cmds.separator()
        s.GUI["layout2"] = cmds.rowColumnLayout(nc=2)
        s.GUI["layout3"] = cmds.columnLayout(adjustableColumn=True)
        s.GUI["image1"] = cmds.iconTextStaticLabel(image="choice.svg", h=130, w=130)
        cmds.setParent("..")
        s.GUI["layout4"] = cmds.columnLayout(adjustableColumn=True)
        s.GUI["text2"] = cmds.text(label="What would you like to do?", h=50)
        s.GUI["button1"] = cmds.iconTextButton(label="Install Script", h=40, image="cluster.png", st="iconAndTextHorizontal", c=call(s._buildInstall))
        s.GUI["button2"] = cmds.iconTextButton(label="Remove Script", h=40, image="deleteActive.png", st="iconAndTextHorizontal", c=call(s._buildRemove))
        cmds.setParent("..")
        cmds.setParent("..")
        cmds.setParent(s.GUI["wrapper"])

    def _buildInstall(s):  # Install UI
        """
        Create Install UI
        """
        s._clearFrame()
        s.GUI["layout1"] = cmds.columnLayout(adjustableColumn=True, w=s.width)
        s.GUI["progress1"] = cmds.progressBar(w=s.width, s=0)
        s.GUI["layout2"] = cmds.scrollLayout(bgc=[0, 0, 0], cr=True, w=s.width, h=200)
        s.GUI["text1"] = cmds.text(label="", align="left")
        cmds.setParent("..")
        cmds.setParent(s.GUI["wrapper"])

        def log(message):
            try:
                text = cmds.text(s.GUI["text1"], q=True, label=True)
                text = "%s\n:>   %s" % (text, message)
                cmds.text(s.GUI["text1"], e=True, label=text)
                cmds.scrollLayout(s.GUI["layout2"], e=True, sp="down")
                cmds.refresh(cv=True)
            except RuntimeError:
                pass

        def update(progress):
            cmds.progressBar(s.GUI["progress1"], e=True, pr=progress)
            cmds.refresh(cv=True)

        Say().what("log", log).what("update", update)

        Say().it("Installing script...")
        Say().it("\n")

        s._install()

    def _buildRemove(s):  # Uninstall UI
        """
        Create Uninstall UI
        """
        s._clearFrame()
        s.GUI["layout1"] = cmds.columnLayout(adjustableColumn=True, w=s.width)
        s.GUI["text1"] = cmds.text(label="Uninstalling Script.", p=s.GUI["wrapper"], h=50, w=400)
        s.GUI["layout2"] = cmds.scrollLayout(bgc=[0, 0, 0], cr=True, w=s.width, h=200)
        s.GUI["text2"] = cmds.text(label="", align="left")
        cmds.setParent("..")
        cmds.setParent(s.GUI["wrapper"])

        def log(message):
            try:
                text = cmds.text(s.GUI["text2"], q=True, label=True)
                text = "%s\n:>   %s" % (text, message)
                cmds.text(s.GUI["text2"], e=True, label=text)
                cmds.scrollLayout(s.GUI["layout2"], e=True, sp="down")
                cmds.refresh(cv=True)
            except RuntimeError:
                pass

        Say().what("log", log)
        Say().it("Removing Script.")
        s._uninstall()

    def _clearFrame(s):  # Clear the UI
        """
        Clear UI for next build
        """
        s.GUI["wrapper"] = s.GUI.get("wrapper", "")
        if cmds.layout(s.GUI["wrapper"], ex=True):
            cmds.deleteUI(s.GUI["wrapper"])
        s.GUI["wrapper"] = cmds.columnLayout(adjustableColumn=True, p=s.GUI["window"])

    def _install(s):
        """
        Let the installation BEGIN!
        """
        with Install() as i:
            operations = math.ceil(100.0 / 6)  # Number of operations
            Say().it("Checking online for latest script.")
            meta = i.getMetaInfo(i.repoUrl)
            Say().it("Found version %s. Created on %s" % (meta["version"], meta["release"]))
            Say().when(operations)

            def downloadUpdate(progress):
                Say().when(progress * operations)

            Say().it("Downloading from %s." % meta["download"])
            temp = i.download(meta["download"], downloadUpdate)
            Say().it("Download Complete. :)")

            Say().it("Extracting files.")
            folder = i.unzip(temp)
            Say().when(operations)

            Say().it("Copying script into place.")
            i.move(folder, i.scriptPath)
            Say().when(operations)

            if i.auto:
                Say().it("Adding startup code.")
                with userSetup() as u:
                    u.add(i.name, i.auto)
            Say().when(operations)

            if i.code:
                Say().it("Adding shelf button to current shelf.")
                mayaShelf(i.shelf).add(i.name, i.code)
            Say().when(operations)

            Say().it("Install Complete!")

    def _uninstall(s):
        """
        Remove script...
        """
        with Install() as u:

            Say().it("Removing Script files.")
            u.cleanup.append(u.scriptPath)
            if u.auto:
                Say().it("Cleaning userSetup.")
                with userSetup() as s:
                    s.delete(u.name)
            if u.code:
                Say().it("Removing shelf icon.")
                mayaShelf(u.shelf).delete(u.name, u.code)

        Say().it("YAY! Uninstall complete!")


class Install(object):
    """
    Run through installation process
    """
    def __enter__(s):
        # Script provided Info
        pluginInfo = getMelVars()
        s.name = pluginInfo["name"]  # Name of script
        s.code = pluginInfo["shelf"]  # Code to put in a shelf icon.
        s.auto = pluginInfo["auto"]  # Code to put in userSetup
        s.repo = pluginInfo["repo"]  # name of Repository
        s.user = pluginInfo["user"]  # user of Repository
        scriptDir = pluginInfo["scriptPath"]  # Path to scripts
        s.shelf = mel.eval('$tmp = $gShelfTopLevel')  # UI element of the Maya shelf

        # Derived info
        s.repoUrl = "https://api.github.com/repos/%s/%s/releases/latest" % (s.user, s.repo)
        s.scriptPath = os.path.join(scriptDir, s.name)  # Place we will put the script
        s.cleanup = []  # List of items to remove afterwards
        return s

    def getMetaInfo(s, url):
        """
        Get download information from Repo
        """
        u = urllib.urlopen(url)
        data = json.load(u)
        result = {}
        result["version"] = data["tag_name"]
        result["download"] = data["zipball_url"]
        result["release"] = re.match("(\d{4}-\d{2}-\d{2})", data["published_at"]).group(1)
        return result

    def download(s, url, callback):
        """
        Download the specified file and provide updates to the callback
        """

        def update(i, block, size):
            if i and size > 0:
                step = 1 / math.ceil(float(size) / block)
                callback(step)
            elif size < 0:
                callback(1.0)

        f = urllib.urlretrieve(url, None, update)[0]
        s.cleanup.append(f)
        return f

    def unzip(s, src):
        z = zipfile.ZipFile(src, "r")
        tmp = os.path.dirname(src)
        folder = os.path.join(tmp, z.namelist()[0])
        z.extractall(tmp)
        s.cleanup.append(folder)
        return folder

    def move(s, src, dest):
        if os.path.exists(dest):
            s.delete(dest)
        shutil.move(src, dest)
        return dest

    def delete(s, path):
        try:
            if os.path.isfile(path):
                os.remove(path)
                Say().it("Deleting file %s" % path)
            elif os.path.isdir(path):
                shutil.rmtree(path)
                Say().it("Removing folder %s" % path)
        except OSError as e:
            Say().it(e)

    def __exit__(s, errType, errValue, trace):
        """
        Clean up after install, or if error occurrs
        """
        if errType:
            Say().it("Uh oh... there was a problem. :(")
            Say().it("%s :: %s" % (errType.__name__, errValue))
            Say().it("\n".join(traceback.format_tb(trace)))
        Say().it("Cleaning up.")
        if s.cleanup:
            for clean in s.cleanup:
                s.delete(clean)
        return True


class userSetup(object):
    """
    Modfiy the startup script
    """
    def __init__(s):
        path = getMelVars()
        s._path = os.path.join(path["scriptPath"], "userSetup.py")
        if os.path.exists(s._path):
            with open(s._path, "r") as f:
                s._data = f.read()
        else:
            s._data = ""

    def __enter__(s):
        search = r"\s*?# # START\s+(\w+)\s*"  # Opening tag
        search += r"(.*?)"  # Content
        search += r"\s*# # END\s+\1\s*"  # Close tag
        parse = re.compile(search, re.S)
        s.code = {}
        subpos = 0
        newData = ""
        for find in parse.finditer(s._data):
            s.code[find.group(1)] = find.group(2)
            pos = find.span()
            newData += s._data[subpos:pos[0]] + "\n"
            subpos = pos[1]
        newData += s._data[subpos:len(s._data)]
        s._data = newData
        return s

    def __exit__(s, type, err, trace):
        for k in s.code:
            codeblock = """
# # START %(name)s
%(code)s
# # END %(name)s
""" % {"name": k, "code": s.code[k]}
            s._data += codeblock
        with open(s._path, "w") as f:
            data = re.sub("\r?\n", os.linesep, s._data)  # Fix newlines for windows
            f.write(data)

    def add(s, key, val):
        s.code[key] = val
        exec val

    def delete(s, key):
        if key in s.code:
            del s.code[key]


class mayaShelf(object):
    """
    Access maya shelf and insert items.
    """
    def __init__(s, shelf):
        s.shelf = shelf

    def add(s, name, code):
        s._addToShelf(name, code)

    def delete(s, name, code):
        s._removeFromShelf(name, code)

    def _addToShelf(s, name, code):
        active = cmds.tabLayout(s.shelf, st=True, q=True)  # Grab active shelf
        buttons = cmds.shelfLayout(active, q=True, ca=True)  # List all buttons in shelf
        missing = True  # Shelf button exists here?
        for b in buttons:
            label = cmds.shelfButton(b, l=True, q=True)
            if label == name:
                cmds.shelfButton(b, e=True, c=code)
                missing = False
                Say().it("Updated existing shelf button.")
        if missing:
            cmds.shelfButton(label=name, c=code, image="daisyLarge.png", p=active)
            Say().it("Created shelf button.")

    def _removeFromShelf(s, name, code):
        allShelf = cmds.tabLayout(s.shelf, ca=True, q=True)
        for s in allShelf:
            buttons = cmds.shelfLayout(s, q=True, ca=True)
            if buttons:
                for b in buttons:
                    label = cmds.shelfButton(b, q=True, l=True)
                    command = cmds.shelfButton(b, q=True, c=True)
                    if label == name and command == code:
                        Say().it("Removing shelf button: %s." % b)
                        cmds.deleteUI(b, ctl=True)


if __name__ == "__main__":  # Are we running by being dragged into maya?
    info = getMelVars()
    MainWindow(info["name"])
else:  # Else we're running in maya window normally. Lets set up some test variables
    mel.eval("""
    $name = "testscript";
    $shelf = "print \\"Shelf Works.\\"";
    $auto = "print \\"This should be visible if it works.\\"\\nprint \\"this should be on a new line\\"";
    $repo = "license_fix";
    $user = "internetimagery";
    """)
    MainWindow("testscript")
