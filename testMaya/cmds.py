from functools import wraps
import sys


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


@unique
class Application(object):
    """
    Keep the state of the application active throughout the script

    >>> a = Application()
    >>> b = Application()
    >>> a is b
    True

    Create new gui element

    >>> print a.createUI("window", {})
    window0
    >>> id = a.createUI("window", {"data":"ok"})
    >>> print a.gui[id]["data"]
    ok

    Remove gui element

    >>> a.removeUI(id)
    True
    >>> a.removeUI(id)
    Traceback (most recent call last):
        ...
    RuntimeError

    Edit a gui element

    >>> ui = a.createUI("window", {"data":"one"})
    >>> a.editUI(ui, {"data":"two"})
    True
    >>> print a.gui[ui]["data"]
    two

    Query ui

    >>> print a.queryUI(ui, "data")
    two
    """
    def __init__(self):
        self.gui = {}  # GUI
        self.lastgui = "mainWindow"  # Previously made gui

    def createUI(self, element, data):
        def uuid(index):
            name = element + str(index)
            if name in self.gui:
                name = uuid(index+1)
            return name
        name = uuid(0)
        self.gui[name] = data
        if "p" not in data:
            self.gui[name]["p"] = self.lastgui
        self.lastgui = name
        return name

    def removeUI(self, ui):
        if ui in self.gui:
            children = [element for element in self.gui if self.gui[element]["p"] is ui]
            if children:
                for child in children:
                    del self.gui[child]
            del self.gui[ui]
            return True
        raise RuntimeError

    def editUI(self, ui, data):
        if ui in self.gui:
            for key in data:
                if key in self.gui[ui]:
                    self.gui[ui][key] = data[key]
            return True
        raise RuntimeError

    def queryUI(self, ui, key=False):
        if ui in self.gui:
            if key and key in self.gui[ui]:
                return self.gui[ui][key]
            return self.gui[ui]

hold = Application()


def UIElement(element, *args, **kwargs):
    """
    Generic UI element
    """
    edit = False
    query = False
    if kwargs:
        if "e" in kwargs and kwargs["e"]:
            del kwargs["e"]
            edit = True
        if "edit" in kwargs and kwargs["edit"]:
            del kwargs["edit"]
            edit = True
        if "q" in kwargs and kwargs["q"]:
            del kwargs["q"]
            query = True
        if "query" in kwargs and kwargs["query"]:
            del kwargs["query"]
            query = True
    if args:
        if edit:
            Application().editUI(args[0], kwargs)
        elif query:
            for key in kwargs:
                return Application().queryUI(args[0], key)
    else:
        if kwargs:
            return Application().createUI(element, kwargs)
        return Application().createUI(element, kwargs)


########## GUI

def window(*args, **kwargs):
    """
    Create window
    >>> win = window(title="window")
    >>> print window(win, q=True, title=True)
    window
    """
    return UIElement("window", *args, **kwargs)


if __name__ == "__main__":  # Are we testing?
    import doctest
    doctest.testmod()
