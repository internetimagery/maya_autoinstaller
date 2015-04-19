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

            if i.auto:
                pass
            Say().when(operations)

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


class userSetup(object):
    """
    Modfiy the startup script
    """
    def __init__(self):
        self.path = os.path.join(getScriptPath(), "userSetup.py")
        if os.path.exists(self.path):
            with open(self.path, "r") as f:
                self.data = f.read()
        else:
            self.data = ""
        self._parse()

    def _parse(self):
        search = r"\s*## START\s+(\w+)\s*"  # Opening tag
        search += r"(.*?)"  # Content
        search += r"\s*## END\s+\1\s*"  # Close tag
        parse = re.compile(search, re.S)
        self.code = {}
        subpos = 0
        newData = ""
        for find in parse.finditer(self.data):
            self.code[find.group(1)] = find.group(2)
            pos = find.span()
            newData += "\n" + self.data[subpos:pos[0]]
            subpos = pos[1]
        newData += "\n" + self.data[subpos:len(self.data)]
        self.data = newData

    def _build(self):
        for k in self.code:
            codeblock = """
## START %s
%s
## END %s
""" % (k, self.code[k], k)
            print codeblock


    def add(self, code):
        pass

userSetup()._build()


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
    pass
    #MainWindow(pluginInfo["name"])
