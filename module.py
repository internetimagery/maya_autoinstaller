import sys, re


# Unique Classes
def unique(item):  # Only keep one window open at a time
    """
    >>> class testClass(object):
    ...     pass
    >>> type(unique(testClass)()) is testClass
    True
    """
    items = {}

    def UniqueItem(*args, **kwargs):
        if (item in items and sys.getrefcount(items[item]) < 3) or item not in items:
            items[item] = item(*args, **kwargs)
        return items[item]
    return UniqueItem


# Testing
if __name__ == "__main__":
    import doctest
    doctest.testmod()
