import sys, re, urllib2, os, json
from functools import wraps


# Unique Classes
def unique(item):
    """
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


# Generic callback for buttons etc
class call(object):
    """
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
            return self.func( *self.args, **self.kwargs )


# Output text to screen AND to function
@unique
class Say(object):
    """
    >>> Say().it("ok")
    ok
    """
    def __init__(self):
        self.output = []
    """
    >>> def testFunc(message):
    ...     print "it is " + message
    >>> a = Say().what(testFunc)
    >>> len(a.output)
    1
    """
    def what(self, function):  # Register somewhere to output text
        self.output.append(function)
    """
    >>> Say().it("ok")
    ok
    it is ok
    """
    def it(self, message):
        print message
        if self.output:
            for func in self.output:
                func(message)


# Github repo for scripts
class Repo(object):  # Repository for scripts
    """
    >>> a = Repo("internetimagery", "shot_pieces")
    Collecting information on script shot_pieces.
    >>> "http" in a.downloadUrl
    True
    >>> b = Repo("fakename", "fakerepo")
    Collecting information on script fakerepo.
    HTTP Error 404: Not Found
    """
    def __init__(self, user, repo):
        if user and repo:
            baseurl = "https://api.github.com/repos/%s/%s/releases/latest" % (user, repo)
            Say().it("Collecting information on script %s." % repo)
            try:
                u = urllib2.urlopen(baseurl)
                data = json.loads(u.read())
                self.version = data["tag_name"]
                self.downloadUrl = data["zipball_url"]
                self.releaseDate = re.match("(\d{4}-\d{2}-\d{2})", data["published_at"]).group(1)
            except urllib2.HTTPError as e:
                Say().it(e)
    """
    >>> print "should fail"
    but doesn't
    """
    def download(self, src, dest, callback):  # Perform checks on the URL and content for download
        self.callback = callback
        if os.path.exists(src):
            temp = os.path.join(src, "temp_download")
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
                            if self._unzip(zippath, dest):  # Unzip file
                                return True
                    else:
                        Say().it("Failed to determine file size.")
                        uninstall()
                else:
                    Say().it("File type is incorrect.")
                    uninstall()

            except urllib2.HTTPError as e:
                Say().it("Something went wrong with the connection...\n%s" % e)
                uninstall()
        return False

    def _downloadProgress(self, request, path):
        totalSize = int(request.info().getheaders("Content-Length")[0])
        downloaded = 0.0
        try:
            with open(path, "wb") as f:
                Say().it("Downloading.")
                while True:
                    data_buffer = request.read(8192 / 4)
                    if not data_buffer:
                        break
                    downloaded += len(data_buffer)
                    progress = downloaded / totalSize
                    self.callback(progress)
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


# Modifying Startup script
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


# Testing
if __name__ == "__main__":
    import doctest
    testDir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "testDir")
    if not os.path.exists(testDir):
        os.makedirs(testDir)
    doctest.testmod()
