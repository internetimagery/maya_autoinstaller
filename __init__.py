# Automatically install script
import maya.cmds as cmds
import maya.mel as mel
import time, sys, urllib2, json, re, zipfile, os, shutil, datetime

pluginInfo = {
    "name":    "clicktime",  # Name of the script file
    "auto":    "import nothing",  # Command to add to userSetup if any
    "repo":    "shot_pieces",  # Repo to get script from
    "user":    "internetimagery"  # Username of repo
}


## UTILITY CLASSES


def unique(item):  # Only keep one window open at a time
    items = {}

    def UniqueItem(*args, **kwargs):
        if (item in items and sys.getrefcount(items[item]) < 3) or item not in items:
            items[item] = item(*args, **kwargs)
        return items[item]
    return UniqueItem


class call(object):  # Generic callback for buttons to pass values
        def __init__(self, func, *args, **kwargs):
                self.func = func
                self.args = args
                self.kwargs = kwargs
        def __call__(self, *args):
                return self.func( *self.args, **self.kwargs )


@unique
class Say(object):  # Logging output

    def __init__(self):
        self.output = []

    def what(self, text):  # Register somewhere to output text
        self.output.append(text)

    def it(self, message):
        print message
        if self.output:
            for out in self.output:
                cmds.text(out, e=True, l="\n%s" % message)


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

    def __init__(self):
        self.GUI = {}
        self.GUI["content"] = {}
        self.GUI["window"] = cmds.window(title="Script Installer", rtf=True, s=False, mnb=False, mxb=False, ret=True)
        self.GUI["wrapper"] = cmds.columnLayout(adjustableColumn=True)
        cmds.showWindow(self.GUI["window"])
        self._buildSelection()

    def _buildSelection(self):
        self._clearFrame()
        self.GUI["content"]["layout1"] = cmds.rowColumnLayout(nc=2)
        self.GUI["content"]["layout2"] = cmds.columnLayout(adjustableColumn=True)
        self.GUI["content"]["image1"] = cmds.iconTextStaticLabel(image="choice.svg", h=130, w=130)
        cmds.setParent("..")
        self.GUI["content"]["layout3"] = cmds.columnLayout(adjustableColumn=True)
        self.GUI["content"]["text1"] = cmds.text(label="What would you like to do?", h=50)
        self.GUI["content"]["button1"] = cmds.iconTextButton(label="Install Script", h=40, image="cluster.png", st="iconAndTextHorizontal")
        self.GUI["content"]["button2"] = cmds.iconTextButton(label="Remove Script", h=40, image="deleteActive.png", st="iconAndTextHorizontal")
        cmds.setParent("..")
        cmds.setParent(self.GUI["wrapper"])

    def _clearFrame(self):  # Clear the UI
        if self.GUI["content"]:
            for key, val in self.GUI["content"]:
                cmds.deleteUI(val)
            self.GUI["content"] = {}

MainWindow()

## FUNCTIONALITY

class Repo(object):  # Repository for scripts

    def __init__(self, user, repo):
        if user and repo:
            baseurl = "https://api.github.com/repos/%s/%s/releases/latest" % (user, repo)
            Say().it("Checking for latest script release")
            try:
                u = urllib2.urlopen(baseurl)
                data = json.loads(u.read())
                self.version = data["tag_name"]
                self.downloadUrl = data["zipball_url"]
                self.releaseDate = re.match("(\d{4}-\d{2}-\d{2})", data["published_at"]).group(1)
                Say().it("Script found. Version %s. Created on %s." % (self.version, self.releaseDate))
            except urllib2.HTTPError as e:
                Say().it(e)
                uninstall()

    def download(self, path, name, callback):  # Perform checks on the URL and content for download
        self.callback = callback
        if os.path.exists(path):
            temp = os.path.join(path, "temp_download")
            final = os.path.join(path, name)
            if not os.path.exists(temp):
                os.makedirs(temp)
            Say().it("Connecting to %s." % self.downloadUrl)
            try:
                zippath = os.path.join(temp, "temp.zip")
                u = urllib2.urlopen(self.downloadUrl)
                typeFilter = "application/zip"
                meta = u.info()
                fileType = meta.getheaders("Content-Type")
                if fileType and typeFilter in fileType:
                    fileSize = meta.getheaders("Content-Length")
                    if fileSize:
                        Say().it("File size determined.")
                        if self._downloadProgress(u, zippath):  # Start actual download
                            if self._unzip(zippath, final):  # Unzip file
                                callback(final)
                    else:
                        Say().it("Failed to determine file size.")
                        uninstall()
                else:
                    Say().it("File type is incorrect.")
                    uninstall()

            except urllib2.HTTPError as e:
                Say().it("Something went wrong with the connection...\n%s" % e)
                uninstall()

    def _downloadProgress(self, request, path):
        totalSize = int(request.info().getheaders("Content-Length")[0])
        downloaded = 0.0
        try:
            with open(path, "wb") as f:
                Say().it("Downloading.")
                bar = ProgressBar()
                while True:
                    data_buffer = request.read(8192 / 4)
                    if not data_buffer:
                        break
                    downloaded += len(data_buffer)
                    progress = downloaded / totalSize
                    bar.step(progress)
                    f.write(data_buffer)
                Say().it("Download complete. :)")
                return True
        except IOError as e:
            Say().it("Could not save file...\n%s" % e)
            uninstall()
            return False

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


#Repo(pluginInfo["user"], pluginInfo["repo"]).download("/Users/Maczone/Desktop/temp", "hello", result)
