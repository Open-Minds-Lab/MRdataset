import logging
from collections import defaultdict
from MRdataset.utils import config
from nibabel.nicom import csareader
import uuid


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


def header_exists(dicom):
    try:
        series = dicom.get(config.SERIES_HEADER_INFO).value
        image = dicom.get(config.IMAGE_HEADER_INFO).value
        series_header = csareader.read(series)

        # just try reading these values, to bypass any errors, don't need these values now
        # image_header = \
        csareader.read(image)
        # items = \
        series_header['tags']['MrPhoenixProtocol']['items'][0].split('\n')
        return True
    except Exception as e:
        logging.exception(e)
        return False


def random_name():
    return str(hash(str(uuid.uuid1())) % 1000000)
