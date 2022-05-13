from collections import defaultdict


def fix(f):
    """
    Pythonic way to construct defaultdict() all the way down
    See : https://quanttype.net/posts/2016-03-29-defaultdicts-all-the-way-down.html
    d = fix(defaultdict)()
    """
    return lambda *args, **kwargs: f(fix(f), *args, **kwargs)


def flatten(arg):
    returnlist = []
    for i in arg:
        if isinstance(i, list):
            returnlist.extend(flatten(i))
        else:
            returnlist.append(i)
    return returnlist


class DeepDefaultDict(defaultdict):
    def __init__(self, depth, default=list, _root=True):
        self.root = _root
        self.depth = depth
        if self.depth > 1:
            curr_default = lambda: DeepDefaultDict(depth-1, default, False)
        else:
            curr_default = default
        defaultdict.__init__(self, curr_default)

    def __repr__(self):
        # if self.root:
        #     return "DeepDefaultDict(%d): {%s}" % (self.depth,
        #                                             defaultdict.__repr__(self))
        # else:
        return dict.__repr__(self)

    def __str__(self):
        return dict.__str__(self)

