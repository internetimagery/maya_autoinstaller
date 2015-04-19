# Automatically install script
try:
    import maya.cmds as cmds
    import maya.mel as mel
except ImportError:
    import testMaya.cmds as cmds
    pass
import time, sys, urllib, json, re, zipfile, os, shutil, datetime, traceback, math
from functools import wraps


pluginInfo = {
    "name":    "clicktime",  # Name of the script file
    "auto":    "print \"hello\"",  # Command to add to userSetup if any
    "repo":    "shot_pieces",  # Repo to get script from
    "user":    "internetimagery"  # Username of repo
}


## UTILITY CLASSES

def getScriptPath():
    return mel.eval("internalVar -usd;")


def unique(item):
    """
    Only keep one Class in memory at a time.
    >>> @unique
    ... class testClass(object):
    ...     pass
    >>> a = testClass()
    >>> b = testClass()
    >>> a is b
    True
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
    >>> def testFunc(message):
    ...     print message
    >>> call(testFunc, "ok")()
    ok
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
    >>> Say().it("ok")
    ok
    """
    def __init__(self):
        self.log = {}
    """
    Register somewhere to show output and update progress
    >>> def testFunc(message):
    ...     print "it is " + message
    >>> a = Say().what("log", testFunc)
    >>> len(a.log["log"])
    1
    """
    def what(self, name, func):
        self.log[name] = self.log.get(name, [])
        self.log[name].append(func)
        return self
    """
    Update overall progress
    >>> def testFuncTwo(prog):
    ...     print prog
    >>> Say().what("update", testFuncTwo).when(0.5)
    0.5
    """
    def when(self, progress):
        try:
            for func in self.log["update"]:
                func(progress)
        except (KeyError, TypeError) as e:
            print "Warning:", e
    """
    Output message
    >>> Say().it("ok")
    ok
    it is ok
    """
    def it(self, message):
        print message
        try:
            for func in self.log["log"]:
                func(message)
        except (KeyError, TypeError) as e:
            print "Warning:", e
sayhold = Say()  # Keep Say alive


## DIALOGS


@unique
class ConfirmDialog(object):  # Cancel at any time.

    def __init__(self, callback):
        self.callback = callback
        self.GUI = {}
        self.GUI["window"] = cmds.window(title="Cancel?", rtf=True, s=False, mnb=False, mxb=False)
        self.GUI['layout1'] = cmds.columnLayout(adjustableColumn=True)
        self.GUI["text1"] = cmds.text(l="Are you sure you wish to exit?", h=100)
        cmds.setParent("..")
        self.GUI["layout2"] = cmds.rowColumnLayout(nc=2)
        self.GUI["button1"] = cmds.button(h=40, l="Yes. I would like to exit.", c=call(self._callback))
        self.GUI["button2"] = cmds.button(h=40, l="No. Please continue.", c=call(self._cleanup))
        cmds.showWindow(self.GUI["window"])

    def _cleanup(self):
        if cmds.window(self.GUI["window"], ex=True):
            cmds.deleteUI(self.GUI["window"], wnd=True)

    def _callback(self):
        Say().it("Canceling install...")
        self._cleanup()
        self.callback()


class ProgressBar(object):  # Progress bar, displaying progress

    def __init__(self):
        self.GUI = {}
        self.progress = 0

        self.GUI["window"] = cmds.window(title="Downloading Files:", rtf=True, s=False, mnb=False, mxb=False, ret=True)
        self.GUI['layout1'] = cmds.columnLayout(adjustableColumn=True)
        self.GUI["progress1"] = cmds.progressBar(w=500)
        self.GUI["button1"] = cmds.button(l="Cancel", c=call(self._cancelDialog))
        cmds.showWindow(self.GUI["window"])

    def step(self, inc):
        inc = int(inc * 100)
        step = inc - self.progress
        self.progress = inc
        cmds.refresh(cv=True)
        if 0 < inc < 100:
            if not cmds.window(self.GUI["window"], q=True, vis=True):
                cmds.showWindow(self.GUI["window"])
            cmds.progressBar(self.GUI["progress1"], e=True, s=step)
        elif inc >= 100:
            cmds.progressBar(self.GUI["progress1"], e=True, s=1)
            self._cleanup()

    def _cancelDialog(self):
        ConfirmDialog(self._cancelProgress)

    def _cancelProgress(self):
        uninstall()

    def _cleanup(self):
        if cmds.window(self.GUI["window"], ex=True):
            cmds.deleteUI(self.GUI["window"], wnd=True)
        cmds.deleteUI(ConfirmDialog(self._cancelProgress).GUI["window"], wnd=True)


class MultichoiceDialog(object):  # Choose an option

    def __init__(self, text, choices, callback):
        self.options = choices
        self.callback = callback
        self.GUI = {}
        self.GUI["window"] = cmds.window(title="Pick One", rtf=True, s=False, mnb=False, mxb=False, ret=True)
        cmds.columnLayout(adjustableColumn=True)
        cmds.text(l=text, h=20)
        cmds.separator()
        for i, option in enumerate(self.options):
            cmds.rowColumnLayout(nc=2)
            cmds.symbolButton(image="pickCompByType.png", h=40, w=40, c=call(self._select, i))
            cmds.button(l=option, h=40, c=call(self._select, i))
            cmds.setParent("..")
        cmds.showWindow(self.GUI["window"])
        Say().it("Waiting for choice...")

    def _select(self, index):
        Say().it("%s chosen. Moving on..." % self.options[index])
        self.callback(self.options[index])


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
        self._clearFrame()
        self.GUI["content"]["text1"] = cmds.text(label="REMOVAL WINDOW", p=self.GUI["wrapper"], h=50, w=100)

    def _clearFrame(self):  # Clear the UI
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
            operations = 100 / 3  # Number of operations
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

            print folder


class Install(object):
    """
    Run through installation process

    >>> a = Install()
    >>> type(a) is Install
    True
    """
    def __enter__(self):
        # Script provided Info
        global pluginInfo
        self.name = pluginInfo["name"]  # Name of script
        self.auto = pluginInfo["auto"]  # Code to put in userSetup
        self.repo = pluginInfo["repo"]  # name of Repository
        self.user = pluginInfo["user"]  # user of Repository

        # Derived info
        self.repoUrl = "https://api.github.com/repos/%s/%s/releases/latest" % (self.user, self.repo)
        scriptDir = getScriptPath()
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


## FUNCTIONALITY

class Repo(object):  # Repository for scripts

    def _unzip(self, src, dest):
        if os.path.exists(src):
            if not os.path.exists(dest):
                if zipfile.is_zipfile(src):
                    z = zipfile.ZipFile(src, "r")
                    reg = re.compile("^.*?(?=[\\/\\\\])")  # Prettyfy the output
                    tmp = os.path.dirname(src)
                    base_name = ""
                    for f in z.namelist():
                        if not base_name:
                            match = reg.match(f)
                            base_name = match.group(0) if match else ""
                        Say().it("Extracting: %s" % reg.sub(dest, f))
                        z.extract(f, tmp)
                    z.close()
                    base_path = os.path.join(tmp, base_name)
                    shutil.move(os.path.join(tmp, base_path), dest)
                    return True
                else:
                    Say().it("Download appears corrupt...")
                    uninstall()
            else:
                Say().it("File already exists: %s" % dest)
                uninstall()
        else:
            Say().it("Could not find the file: %s" % src)
            uninstall()
        return False


class Startup(object):  # Adding Startup

    def __init__(self):
        self.scriptPath = mel.eval("internalVar -usd;")
        self.startPath = os.path.join(self.scriptPath, "userSetup.py")
        if not os.path.exists(self.startPath):
            Say().it("Creating Startup file. userSetup.py")
            open(self.startPath, "w").close()  # Create blank file if one doesn't exist

    def _parse(self):  # Parse setup file
        #parse = re.compile("## START[ \\t]+(\\w+)[ \\t]*(.*?)## END[ \\t]+\\1[ \\t]*", re.S)
        search = r"\s*## START\s+(\w+)\s*"  # Opening tag
        search += r"(.*?)"  # Content
        search += r"## END\s+\1\s*"
        parse = re.compile(search, re.S)
        with open(self.startPath) as f:
            data = f.read()
        if data:
            import pprint
            pprint.pprint(dict((r[0], r[1]) for r in parse.findall(data)))

    def _inject(self):  # Inject new script into usersetup file
        with open(self.startPath, "r") as f:
            data = f.read()
        reg = re.compile("[\n]*?## Automatically generated on \\d{4}-\\d{2}-\\d{2}.+?## End generation\\.\\n", re.S)
        data = "%s\n%s" % (reg.sub("", data), self._startupFile())
        with open(self.startPath, "w") as f:
            f.write(data)

    def _startupFile(self):
        return """
## Automatically generated on %s
import json, sys
sys.path.append("%s")
try:
    with open("%s", "r") as f:
        try:
            for script in json.load(f):
                exec script["startup"]
        except KeyError:
            pass
except IOError:
    print "Startup missing"
## End generation.
""" % (datetime.date.today(), self.installPath, self.Startup)

    def addMeta(self, data):
        with open(self.Startup, "r") as f:
            pass


def result(*thing):  # Just for testing.
    Say().it(thing)


def uninstall():  # Remove everything TODO: fill this in later... change name to cleanup class or something
    Say().it("Exiting")

if __name__ == "__main__":  # Are we testing?
    import doctest
    doctest.testmod()
else:  # Run GUI
    MainWindow(pluginInfo["name"])
