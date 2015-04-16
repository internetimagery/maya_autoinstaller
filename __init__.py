# Automatically install script
import maya.cmds as cmds
import time, sys


def unique(item):  # Only keep one window open at a time
    items = {}

    def UniqueItem(*args, **kwargs):
        if (item in items and sys.getrefcount(items[item]) < 3) or item not in items:
            items[item] = item(*args, **kwargs)
        return items[item]
    return UniqueItem


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
        self.GUI["button1"] = cmds.button(h=40, l="Yes. I would like to exit.", c=self._callback)
        self.GUI["button2"] = cmds.button(h=40, l="No. Please continue.", c=self._cleanup)
        cmds.showWindow(self.GUI["window"])

    def _cleanup(self, *args):
        if cmds.window(self.GUI["window"], ex=True):
            cmds.deleteUI(self.GUI["window"], wnd=True)

    def _callback(self, button):
        self._cleanup()
        self.callback()


class ProgressBar(object):

    def __init__(self):
        self.GUI = {}
        self.progress = 0

        self.GUI["window"] = cmds.window(title="Downloading Files:", rtf=True, s=False, mnb=False, mxb=False, ret=True)
        self.GUI['layout1'] = cmds.columnLayout(adjustableColumn=True)
        self.GUI["progress1"] = cmds.progressBar(w=500)
        self.GUI["button1"] = cmds.button(l="Cancel", c=self._cancelDialog)
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
            print "DONE"

    def _cancelDialog(self, *button):
        ConfirmDialog(self._cancelProgress)

    def _cancelProgress(self):
        uninstall()

    def _cleanup(self):
        if cmds.window(self.GUI["window"], ex=True):
            cmds.deleteUI(self.GUI["window"], wnd=True)
        cmds.deleteUI(ConfirmDialog(self._cancelProgress).GUI["window"], wnd=True)

def uninstall():  # Remove everything
    print "removing everything"

bar = ProgressBar()
for i in range(100):
    time.sleep(0.1)
    i = (i + 1) / 100.0
    bar.step(i)
