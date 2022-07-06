import functools
import sys
import threading
import time
import uuid
from collections import defaultdict
from collections.abc import Hashable


def safe_get(dictionary, keys, default=None):
    return functools.reduce(
        lambda d, key: d.get(key, default) if isinstance(d, dict) else default, keys.split("."),
        dictionary
    )


def fix(f):
    """
    Pythonic way to construct defaultdict() all the way down
    See : https://quanttype.net/posts/2016-03-29-defaultdicts-all-the-way-down.html
    d = fix(defaultdict)()
    """
    return lambda *args, **kwargs: f(fix(f), *args, **kwargs)


def flatten(arg):
    returnlist = []
    if not arg:
        return returnlist
    for i in arg:
        if isinstance(i, list):
            returnlist.extend(flatten(i))
        else:
            returnlist.append(i)
    return returnlist


class DeepDefaultDict(defaultdict):
    def __init__(self, depth, default=list):
        if depth > 1:
            defaultdict.__init__(self, lambda: DeepDefaultDict(depth-1, default))
        else:
            defaultdict.__init__(self, default)

    def __repr__(self):
        return dict.__repr__(self)

    def __str__(self):
        return dict.__str__(self)


def random_name():
    return str(hash(str(uuid.uuid1())) % 1000000)


def is_hashable(value):
    return isinstance(value, Hashable)


class Spinner:
    busy = False
    delay = 0.1

    @staticmethod
    def spinning_cursor():
        while 1:
            for cursor in '|/-\\':
                yield cursor

    def __init__(self, delay=None):
        self.spinner_generator = self.spinning_cursor()
        if delay and float(delay):
            self.delay = delay

    def spinner_task(self):
        while self.busy:
            sys.stdout.write(next(self.spinner_generator))
            sys.stdout.flush()
            time.sleep(self.delay)
            sys.stdout.write('\b')
            sys.stdout.flush()

    def __enter__(self):
        self.busy = True
        threading.Thread(target=self.spinner_task).start()

    def __exit__(self, exception, value, tb):
        self.busy = False
        time.sleep(self.delay)
        if exception is not None:
            return False
