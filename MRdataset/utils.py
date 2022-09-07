import functools
import json
import time
import uuid
from collections.abc import Hashable, Iterable
from pathlib import Path
from typing import List

from MRdataset.config import PARAMETER_NAMES
from dictdiffer import diff as dict_diff


def files_under_folder(path):
    if not Path(path).exists():
        raise FileNotFoundError("Folder doesn't exist")
    folder_path = Path(path).resolve()
    for file in folder_path.rglob('*'):
        if file.is_file():
            yield file


def safe_get(dictionary: dict, keys: str, default=None):
    """
    Used to get value from nested dictionaries without getting KeyError
    @param dictionary: nested dict from which the value should be fetched
    @param keys: string of keys delimited by '.'
    @param default: if KeyError, return default
    @return: object

    Examples:
    To get value, dictonary[tag1][tag2][tag3],
    if KeyError: return default
    >>>     items = safe_get(dictionary, 'tags1.tag2.tag3')

    """
    return functools.reduce(
        lambda d, key: d.get(key, default) if isinstance(d, dict) else default,
        keys.split("."),
        dictionary
    )


def param_difference(dict1: dict,
                     dict2: dict,
                     ignore: Iterable = None) -> List[Iterable]:
    """
    A helper function to calculate differences between 2 dictionaries,
    dict1 and dict2. Returns an iterator with differences between 2
    dictionaries. The diff result consist of multiple items, which represent
    addition/deletion/change and the item value is a deep copy from the
    corresponding source and destination objects.
    See https://dictdiffer.readthedocs.io/en/latest/

    TODO: Notes for future reference:
    1. Allowing a range of values for a single parameter
    2. Maybe even more different type of checks
    3. Will be helpful in hierarchical checks (e.g. within modality within
    session)

    @param dict1: source dict
    @param dict2: destination dict
    @param ignore: dictionary keys which should be ignored
    @return: list of items representing addition/deletion/change
    """
    if isinstance(dict1, dict) and isinstance(dict2, dict):
        if ignore is None:
            return list(dict_diff(dict1, dict2, tolerance=0.01))
        elif isinstance(ignore, Iterable):
            return list(dict_diff(dict1, dict2, ignore=set(ignore)))
        raise TypeError(
            "Expected type 'iterable', got {} instead. "
            "Pass a list of parameters.".format(type(ignore)))
    raise TypeError("Expected type 'dict', got {} instead".format(type(dict2)))


def random_name() -> str:
    """
    Function to generate a random identifier/name
    @return: random_number cast to string
    """
    return str(hash(str(uuid.uuid1())) % 1000000)


def is_hashable(value) -> bool:
    """
    Check if variable type is hashable, required to make dictionary keys
    @param value: any variable
    @return: bool
    """
    return isinstance(value, Hashable)


def timestamp() -> str:
    """
    Generates time string in the specified format
    @return: time cast as string
    """
    time_string = time.strftime("%m_%d_%Y_%H_%M")
    return time_string


def select_parameters(filepath):
    with open(filepath, "r") as read_file:
        parameters = json.load(read_file)

    selected_params = dict()
    for key in parameters:
        for entry in PARAMETER_NAMES:
            if entry.lower() in key.lower():
                selected_params[key] = parameters[key]

    return selected_params
