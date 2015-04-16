# Automatically install script
import maya.cmds as cmds
import time, sys, urllib2, json, re, zipfile, os, shutil

pluginInfo = {
    "name":    "clicktime",  # Name of the script file
    "auto":    "import nothing",  # Command to add to userSetup if any
    "repo":    "shot_pieces",  # Repo to get script from
    "user":    "internetimagery"  # Username of repo
}


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
        print "Canceling install..."
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
        print "Waiting for choice..."

    def _select(self, index):
        print "%s chosen. Moving on..." % self.options[index]
        self.callback(self.options[index])


class Repo(object):  # Repository for scripts

    def __init__(self, user, repo):
        if user and repo:
            baseurl = "https://api.github.com/repos/%s/%s/releases/latest" % (user, repo)
            print "Checking for latest script release"
            try:
                u = urllib2.urlopen(baseurl)
                data = json.loads(u.read())
                self.version = data["tag_name"]
                self.downloadUrl = data["zipball_url"]
                self.releaseDate = re.match("(\d{4}-\d{2}-\d{2})", data["published_at"]).group(1)
                print "Script found. Version %s. Created on %s." % (self.version, self.releaseDate)
            except urllib2.HTTPError as e:
                print e

    def download(self, path, name, callback):  # Perform checks on the URL and content for download
        self.callback = callback
        if os.path.exists(path):
            temp = os.path.join(path, "temp_download")
            final = os.path.join(path, name)
            if not os.path.exists(temp):
                os.makedirs(temp)
            print "Connecting to %s." % self.downloadUrl
            try:
                zippath = os.path.join(temp, "temp.zip")
                u = urllib2.urlopen(self.downloadUrl)
                typeFilter = "application/zip"
                #f = open(zippath, "wb")
                meta = u.info()
                fileType = meta.getheaders("Content-Type")
                if fileType and typeFilter in fileType:
                    fileSize = meta.getheaders("Content-Length")
                    if fileSize:
                        print "File size determined."
                        if self._downloadProgress(u, zippath):  # Start actual download
                            if self._unzip(zippath, final):  # Unzip file
                                print "Doing ok... :)"
                    else:
                        print "Failed to determine file size."
                else:
                    print "File type is incorrect."

            except urllib2.HTTPError as e:
                print "Something went wrong with the connection...\n%s" % e

    def _downloadProgress(self, request, path):
        totalSize = int(request.info().getheaders("Content-Length")[0])
        downloaded = 0.0
        try:
            f = open(path, "wb")
            print "Downloading."
            bar = ProgressBar()
            while True:
                data_buffer = request.read(8192 / 4)
                if not data_buffer:
                    break
                downloaded += len(data_buffer)
                progress = downloaded / totalSize
                bar.step(progress)
                f.write(data_buffer)
            print "Download complete. :)"
            f.close()
            return True
        except IOError as e:
            print "Could not save file...\n%s" % e
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
                        print "Extracting: %s" % reg.sub(dest, f)
                        z.extract(f, tmp)
                    z.close()
                    base_path = os.path.join(tmp, base_name)
                    shutil.move(os.path.join(tmp, base_path), dest)
                    return True
                else:
                    print "Download appears corrupt..."
            else:
                print "File already exists: %s" % dest
        else:
            print "Could not find the file: %s" % src
        return False


@unique
class Log(object):  # Logging output

    def __init__(object):
        pass

    def log(message):
        print message


def result(*thing):  # Just for testing.
    print thing


def uninstall():  # Remove everything
    print "removing everything"


rep = Repo(pluginInfo["user"], pluginInfo["repo"])
rep._unzip("/Users/Maczone/Desktop/temp/temp_download/temp.zip", "/Users/Maczone/Desktop/temp/hello")
#rep.download("/Users/Maczone/Desktop/temp", "hello", result)
