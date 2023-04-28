import functools
import re
import tempfile
import time
import typing
import unicodedata
import uuid
from collections.abc import Hashable, Iterable
from pathlib import Path
from typing import Union, List, Optional

import numpy as np
from MRdataset.config import MRDS_EXT
from MRdataset.log import logger
from dictdiffer import diff as dict_diff


def files_under_folder(fpath: Union[str, Path],
                       ext: str = None) -> typing.Iterable[Path]:
    """
    Generates all the files inside the folder recursively. If ext is given
    returns file which have that extension.

    Parameters
    ----------
    fpath: str
        filepath of the directory
    ext: str
        filter files with given extension. For ex. return only .nii files

    Returns
    -------
    generates filepaths
    """
    if not Path(fpath).is_dir():
        raise FileNotFoundError(f"Folder doesn't exist : {fpath}")
    folder_path = Path(fpath).resolve()
    if ext:
        pattern = '*'+ext
    else:
        pattern = '*'
    for file in folder_path.rglob(pattern):
        if file.is_file():
            # If it is a regular file and not a directory, return filepath
            yield file


def safe_get(dictionary: dict, keys: str, default=None):
    """
    Used to get value from nested dictionaries without getting KeyError

    Parameters
    ----------
    dictionary : nested dict from which the value should be fetched
    keys : string of keys delimited by '.'
    default : if KeyError, return default

    Returns
    -------
    Value stored in that key

    Examples:
    To get value, dictionary[tag1][tag2][tag3],
    if KeyError: return default
    >>>     items = safe_get(dictionary, 'tags1.tag2.tag3')

    """
    return functools.reduce(
        lambda d, key: d.get(key, default) if isinstance(d, dict) else default,
        keys.split('.'),
        dictionary
    )


def param_difference(dict1: dict,
                     dict2: dict,
                     ignore: Iterable = None,
                     tolerance: float = 0.1) -> List[Iterable]:
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

    Parameters
    ----------
    dict1 : source dictionary
    dict2 : destination dictionary
    ignore : dictionary keys which should be ignored
    tolerance : tolerance for float values

    Returns
    -------
    list of items representing addition/deletion/change
    """
    if isinstance(dict1, dict) and isinstance(dict2, dict):
        if ignore is None:
            return list(dict_diff(dict1, dict2, tolerance=tolerance))
        elif isinstance(ignore, Iterable):
            return list(dict_diff(dict1, dict2, tolerance=tolerance,
                                  ignore=set(ignore)))
        raise TypeError(
            "Expected type 'iterable', got {} instead. "
            "Pass a list of parameters.".format(type(ignore)))
    raise TypeError("Expected type 'dict', got {} instead".format(type(dict2)))


def random_name() -> str:
    """
    Function to generate a random identifier/name

    Returns
    -------
    random_number cast to string
    """
    return str(hash(str(uuid.uuid1())) % 1000000)


def is_hashable(value) -> bool:
    """
    Check if variable type is hashable, required to make dictionary keys

    Parameters
    ----------
    value : any datatype

    Returns
    -------
    If the data type is hashable
    """
    return isinstance(value, Hashable)


def make_hashable(value):
    if value is None:
        return None
    if isinstance(value, np.ndarray):
        values = value.tolist()
    else:
        values = value
    if isinstance(values, Iterable) and not isinstance(values, str):
        return " ".join([str(x) for x in values])
    if not isinstance(values, str) and np.isnan(values):
        return 'NaN'
    if is_hashable(values):
        return values
    return str(values)


def timestamp() -> str:
    """
    Generates time string in the specified format

    Returns
    -------
    time formatted as string
    """
    time_string = time.strftime("%m_%d_%Y_%H_%M")
    return time_string


def files_in_path(fp_list: Union[Iterable, str, Path],
                  ext: Optional[str] = None):
    """
    If given a single folder, returns the list of all files in the directory.
    If given a list of folders, returns concatenated list of all the files
    inside each directory.

    Parameters
    ----------
    fp_list : List[Path]
        List of folder paths
    ext : str
        Used to filter files, and select only those which have this extension
    Returns
    -------
    List of paths
    """
    if isinstance(fp_list, Iterable):
        files = []
        for i in fp_list:
            if str(i) == '' or str(i) == '.' or i == Path():
                logger.warning("Found an empty string. Skipping")
                continue
            if Path(i).is_dir():
                files.extend(list(files_under_folder(i, ext)))
            elif Path(i).is_file():
                files.append(i)
        return sorted(list(set(files)))
    elif isinstance(fp_list, str) or isinstance(fp_list, Path):
        return sorted(list(files_under_folder(fp_list, ext)))
    else:
        raise NotImplementedError("Expected either Iterable or str type. Got"
                                  f"{type(fp_list)}")


def valid_dirs(folders: Union[List, str]) -> Union[List[Path], Path]:
    """
    If given a single path, the function will just check if it's valid.
    If given a list of paths, the function validates if all the paths exist or
    not. The paths can either be an instance of string or POSIX path.

    Parameters
    ----------
    folders : str or List[str]
        The path or list of paths that must be validated

    Returns
    -------
    List of POSIX Paths that exist on disk
    """
    if folders is None:
        raise ValueError('Expected a valid path, Got NoneType')
    if isinstance(folders, str) or isinstance(folders, Path):
        if not Path(folders).is_dir():
            raise OSError('Invalid directory {0}'.format(folders))
        return Path(folders).resolve()
    elif isinstance(folders, Iterable):
        for folder in folders:
            if not Path(folder).is_dir():
                raise OSError('Invalid directory {0}'.format(folder))
        return [Path(f).resolve() for f in folders]
    else:
        raise NotImplementedError('Expected str or Path or Iterable, '
                                  f'Got {type(folders)}')


def valid_paths(files: Union[List, str]) -> Union[List[Path], Path]:
    """
    If given a single path, the function will just check if it's valid.
    If given a list of paths, the function validates if all the paths exist or
    not. The paths can either be an instance of string or POSIX path.

    Parameters
    ----------
    files : str or List[str]
        The path or list of paths that must be validated

    Returns
    -------
    List of POSIX Paths that exist on disk
    """
    if files is None:
        raise ValueError('Expected a valid path or Iterable, Got NoneType')
    if isinstance(files, str) or isinstance(files, Path):
        if not Path(files).is_file():
            raise OSError('Invalid File {0}'.format(files))
        return Path(files).resolve()
    elif isinstance(files, Iterable):
        for file in files:
            if not Path(file).is_file():
                raise OSError('Invalid File {0}'.format(file))
        return [Path(f).resolve() for f in files]
    else:
        raise NotImplementedError('Expected str or Path or Iterable, '
                                  f'Got {type(files)}')


def slugify(value, allow_unicode=False):
    """
    Taken from https://github.com/django/django/blob/master/django/utils/text.py
    Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
    dashes to single dashes. Remove characters that aren't alphanumerics,
    underscores, or hyphens. Convert to lowercase. Also strip leading and
    trailing whitespace, dashes, and underscores.
    """
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize('NFKC', value)
    else:
        value = unicodedata.normalize(
            'NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s-]', '', value.lower())
    return re.sub(r'[-\s]+', '-', value).strip('-_')


def check_mrds_extension(filepath: Union[str, Path]):
    """
    Check if the extension of the file is .mrds.pkl
    Parameters
    ----------
    filepath: str or pathlib.Path
        filepath pointing to the file

    Returns
    -------
    None
    """
    if isinstance(filepath, Path):
        ext = "".join(filepath.suffixes)
    elif isinstance(filepath, str):
        ext = "".join(Path(filepath).suffixes)
    else:
        raise NotImplementedError(f"Expected str or pathlib.Path,"
                                  f" Got {type(filepath)}")
    assert ext == MRDS_EXT, f"Expected extension {MRDS_EXT}, Got {ext}"


def is_same_dataset(dataset1, dataset2):
    modalities_list1 = sorted(dataset1.modalities)
    modalities_list2 = sorted(dataset2.modalities)
    for modality1, modality2 in zip(modalities_list1, modalities_list2):
        assert modality1.name == modality2.name
        assert modality1.compliant == modality2.compliant
        assert modality1._reference == modality2._reference
        assert modality1.non_compliant_data.equals(modality2.non_compliant_data)
        subjects_list1 = sorted(modality1.subjects)
        subjects_list2 = sorted(modality2.subjects)
        for subject1, subject2 in zip(subjects_list1, subjects_list2):
            assert subject1.name == subject2.name
            assert subject1.__dict__ == subject2.__dict__
            sessions_list1 = sorted(subject1.sessions)
            sessions_list2 = sorted(subject2.sessions)
            for session1, session2 in zip(sessions_list1, sessions_list2):
                assert session1.name == session2.name
                assert session1.__dict__ == session2.__dict__
                runs_list1 = sorted(session1.runs)
                runs_list2 = sorted(session2.runs)
                for run1, run2 in zip(runs_list1, runs_list2):
                    assert run1.__dict__ == run2.__dict__
                    assert run1.name == run2.name
                    assert run1.params == run2.params
    return True


def is_writable(dir_path):
    try:
        with tempfile.TemporaryFile(dir=dir_path, mode='w') as testfile:
            testfile.write("OS write to directory test.")
            logger.info(f"Created temp file in {dir_path}")
    except (OSError, IOError) as e:
        logger.error(e)
        return False
    return True

