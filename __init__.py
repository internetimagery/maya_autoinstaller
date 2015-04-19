# Automatically install script
import maya.cmds as cmds
import maya.mel as mel
import sys, urllib, json, re, zipfile, os, shutil, traceback, math
from functools import wraps

mel.eval("""
$name = "clicktime";
$shelf = "print \\"code here\\"";
$auto = "print \\"hello\\"";
$repo = "shot_pieces";
$user = "internetimagery";
""")


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
    def __init__(self, func, *args, **kwargs):
            self.func = func
            self.args = args
            self.kwargs = kwargs

    def __call__(self, *args):
            return self.func(*self.args, **self.kwargs)


@unique
class Say(object):
    """
    Logging output
    """
    def __init__(self):
        self.log = {}
    """
    Register somewhere to show output and update progress
    """
    def what(self, name, func):
        self.log[name] = self.log.get(name, [])
        self.log[name].append(func)
        return self
    """
    Update overall progress
    """
    def when(self, progress):
        try:
            for func in self.log["update"]:
                func(progress)
        except (KeyError, TypeError) as e:
            print "Warning:", e
    """
    Output message
    """
    def it(self, message):
        print message
        try:
            if self.log:
                for func in self.log["log"]:
                    func(message)
        except (KeyError, TypeError) as e:
            print "Warning:", e
sayhold = Say()  # Keep Say alive


## Functionality
class MainWindow(object):
    """
    Main window. For selecting initial options and providing feedback
    """
    def __init__(self, title):
        self.GUI = {}
        self.title = title
        self.GUI["content"] = {}
        self.GUI["window"] = cmds.window(title="Script Installer", rtf=True, s=False, mnb=False, mxb=False, ret=True)
        self.GUI["wrapper"] = cmds.columnLayout(adjustableColumn=True)
        cmds.showWindow(self.GUI["window"])
        self._buildSelection()

    def _buildSelection(self):
        """
        Create Selection UI (main menu)
        """
        self._clearFrame()
        self.GUI["content"]["layout1"] = cmds.columnLayout(adjustableColumn=True)
        self.GUI["content"]["text1"] = cmds.text(label="Features for %s." % self.title)
        cmds.separator()
        self.GUI["content"]["layout2"] = cmds.rowColumnLayout(nc=2)
        self.GUI["content"]["layout3"] = cmds.columnLayout(adjustableColumn=True)
        self.GUI["content"]["image1"] = cmds.iconTextStaticLabel(image="choice.svg", h=130, w=130)
        cmds.setParent("..")
        self.GUI["content"]["layout4"] = cmds.columnLayout(adjustableColumn=True)
        self.GUI["content"]["text2"] = cmds.text(label="What would you like to do?", h=50)
        self.GUI["content"]["button1"] = cmds.iconTextButton(label="Install Script", h=40, image="cluster.png", st="iconAndTextHorizontal", c=call(self._buildInstall))
        self.GUI["content"]["button2"] = cmds.iconTextButton(label="Remove Script", h=40, image="deleteActive.png", st="iconAndTextHorizontal", c=call(self._buildRemove))
        cmds.setParent("..")
        cmds.setParent("..")
        cmds.setParent(self.GUI["wrapper"])

    def _buildInstall(self):  # Install UI
        """
        Create Install UI
        """
        self._clearFrame()
        self.GUI["content"]["layout1"] = cmds.columnLayout(adjustableColumn=True)
        self.GUI["content"]["progress1"] = cmds.progressBar(w=500)
        self.GUI["content"]["layout2"] = cmds.scrollLayout(bgc=[0, 0, 0], cr=True, h=500)
        self.GUI["content"]["text1"] = cmds.text(label="", align="left")
        cmds.setParent("..")
        cmds.setParent(self.GUI["wrapper"])

        def log(message):
            try:
                text = cmds.text(self.GUI["content"]["text1"], q=True, label=True)
                text = "%s\n:>   %s" % (text, message)
                cmds.text(self.GUI["content"]["text1"], e=True, label=text)
                cmds.scrollLayout(self.GUI["content"]["layout2"], e=True, sp="down")
                cmds.refresh(cv=True)
            except RuntimeError:
                pass

        def update(progress):
            cmds.progressBar(self.GUI["content"]["progress1"], e=True, s=progress)
            cmds.refresh(cv=True)

        Say().what("log", log).what("update", update)

        Say().it("Installing script...")
        Say().it("\n")

        self._install()

    def _buildRemove(self):  # Uninstall UI
        """
        Create Uninstall UI
        """
        self._clearFrame()
        self.GUI["content"]["text1"] = cmds.text(label="REMOVAL WINDOW", p=self.GUI["wrapper"], h=50, w=100)

        self._uninstall()

    def _clearFrame(self):  # Clear the UI
        """
        Clear UI for next build
        """
        if self.GUI["content"]:
            for key, val in self.GUI["content"].iteritems():
                try:
                    cmds.deleteUI(val)
                except RuntimeError:
                    pass
            self.GUI["content"] = {}

    def _install(self):
        """
        Let the installation BEGIN!
        """
        with Install() as i:
            operations = 100 / 6  # Number of operations
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
                with userSetup as u:
                    u.add(i.name, i.auto)
            Say().when(operations)

            if i.code:
                Say().it("Adding shelf button to current shelf.")
                mayaShelf(i.shelf).add(i.name, i.code)
            Say().when(operations)

            Say().it("Install Complete!")

    def _uninstall(self):
        """
        Remove script...
        """
        with Install() as u:
            u.cleanup.append(u.scriptPath)
            if u.auto:
                with userSetup() as s:
                    s.delete(u.name)
            if u.code:
                mayaShelf(u.shelf).delete(u.name, u.code)


class Install(object):
    """
    Run through installation process
    """
    def __enter__(self):
        # Script provided Info
        pluginInfo = getMelVars()
        self.name = pluginInfo["name"]  # Name of script
        self.code = pluginInfo["shelf"]  # Code to put in a shelf icon.
        self.auto = pluginInfo["auto"]  # Code to put in userSetup
        self.repo = pluginInfo["repo"]  # name of Repository
        self.user = pluginInfo["user"]  # user of Repository
        scriptDir = pluginInfo["scriptPath"]  # Path to scripts
        self.shelf = mel.eval('$tmp = $gShelfTopLevel')  # UI element of the Maya shelf

        # Derived info
        self.repoUrl = "https://api.github.com/repos/%s/%s/releases/latest" % (self.user, self.repo)
        self.scriptPath = os.path.join(scriptDir, self.name)  # Place we will put the script
        self.cleanup = []  # List of items to remove afterwards
        return self

    def getMetaInfo(self, url):
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

    def download(self, url, callback):
        """
        Download the specified file and provide updates to the callback
        """

        def update(i, block, size):
            if i and size:
                step = 1 / math.ceil(float(size) / block)
                callback(step)
            elif not size:
                callback(1.0)

        f = urllib.urlretrieve(url, None, update)[0]
        self.cleanup.append(f)
        return f

    def unzip(self, src):
        z = zipfile.ZipFile(src, "r")
        tmp = os.path.dirname(src)
        folder = os.path.join(tmp, z.namelist()[0])
        z.extractall(tmp)
        self.cleanup.append(folder)
        return folder

    def move(self, src, dest):
        if os.path.exists(dest):
            os.rmdir(dest)
        shutil.move(src, dest)
        return dest

    def delete(self, path):
        try:
            if os.path.isfile(path):
                os.remove(path)
                Say().it("Deleting file %s." % path)
            elif os.path.isdir(path):
                os.rmdir(path)
                Say().it("Removing folder %s." % path)
        except OSError as e:
            Say().it(e)

    def __exit__(self, errType, errValue, trace):
        """
        Clean up after install, or if error occurrs
        """
        if errType:
            Say().it("Uh oh... there was a problem. :(")
            Say().it("%s :: %s" % (errType.__name__, errValue))
            Say().it("\n".join(traceback.format_tb(trace)))
        Say().it("Cleaning up.")
        if self.cleanup:
            for clean in self.cleanup:
                self.delete(clean)
        return True


class userSetup(object):
    """
    Modfiy the startup script
    """
    def __init__(self):
        path = getMelVars()
        self._path = os.path.join(path["scriptPath"], "userSetup.py")
        if os.path.exists(self._path):
            with open(self._path, "r") as f:
                self._data = f.read()
        else:
            self._data = ""

    def __enter__(self):
        search = r"\s*# # START\s+(\w+)\s*"  # Opening tag
        search += r"(.*?)"  # Content
        search += r"\s*# # END\s+\1\s*"  # Close tag
        parse = re.compile(search, re.S)
        self.code = {}
        subpos = 0
        newData = ""
        for find in parse.finditer(self._data):
            self.code[find.group(1)] = find.group(2)
            pos = find.span()
            newData += self._data[subpos:pos[0]] + "\n"
            subpos = pos[1]
        newData += self._data[subpos:len(self._data)]
        self._data = newData
        return self

    def __exit__(self, type, err, trace):
        for k in self.code:
            codeblock = """
# # START %s
%s
# # END %s
""" % (k, self.code[k], k)
            self._data += codeblock
        with open(self._path, "w") as f:
            f.write(self._data)

    def add(self, key, val):
        self.code[key] = val

    def delete(self, key):
        if key in self.code:
            del self.code[key]


class mayaShelf(object):
    """
    Access maya shelf and insert items.
    """
    def __init__(self, shelf):
        self.shelf = shelf

    def add(self, name, code):
        self._addToShelf(name, code)

    def delete(self, name, code):
        self._removeFromShelf()

    def _addToShelf(self, name, code):
        active = cmds.tabLayout(self.shelf, st=True, q=True)  # Grab active shelf
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

    def _removeFromShelf(self, name, code):
        allShelf = cmds.tabLayout(self.shelf, ca=True, q=True)
        for s in allShelf:
            buttons = cmds.shelfLayout(s, q=True, ca=True)
            if buttons:
                for b in buttons:
                    label = cmds.shelfButton(b, q=True, l=True)
                    command = cmds.shelfButton(b, q=True, c=True)
                    if label == name and command == code:
                        Say().it("Removing shelf button: %s." % b)
                        cmds.deleteUI(b, ctl=True)


if __name__ == "__main__":  # Are we testing?
    pass
    #import doctest
    #doctest.testmod()
else:  # Run GUI
    # info = getMelVars()
    # MainWindow(info["name"])
    pass
