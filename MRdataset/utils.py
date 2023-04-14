import functools
import json
import time
import uuid
from collections.abc import Hashable, Iterable
from pathlib import Path
from typing import List

from MRdataset.config import PARAMETER_NAMES, MRDS_EXT
from dictdiffer import diff as dict_diff
from bids.layout.models import BIDSFile
import nibabel as nib
import numpy as np
import typing
from typing import Union, List, Optional


def files_under_folder(path: str, ext: str = None) -> typing.Iterable[Path]:
    """
    Generates all the files inside the folder recursively. If ext is given
    returns file which have that extension.

    Parameters
    ----------
    path: str
        filepath of the directory
    ext: str
        filter files with given extension. For ex. return only .nii files

    Returns
    -------
    generates filepaths
    """
    if not Path(path).exists():
        raise FileNotFoundError("Folder doesn't exist")
    folder_path = Path(path).resolve()
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

    Parameters
    ----------
    dict1 : source dictionary
    dict2 : destination dictionary
    ignore : dictionary keys which should be ignored

    Returns
    -------
    list of items representing addition/deletion/change
    """
    if isinstance(dict1, dict) and isinstance(dict2, dict):
        if ignore is None:
            return list(dict_diff(dict1, dict2))
        elif isinstance(ignore, Iterable):
            return list(dict_diff(dict1, dict2, ignore=set(ignore)))
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


def select_parameters(file) -> dict:
    """
    Reads parameters for BIDS datasets. The filepath can either point to a
     JSON file or a NIfTI file. In case of a NIfTI file the parameters are
     extracted from the header.

    Parameters
    ----------
    filepath : pathlib.Path or str
        Path pointing to either a JSON or NIfTI file
    Returns
    -------

    """
    # TODO: filepath should already have the extension, why do you need to
    #  pass separately? Modify the code.

    selected_params = dict()

    if isinstance(file, BIDSFile):
        file_path = file.path
    elif isinstance(file, Path):
        file_path = file
    else:
        raise NotImplementedError

    ext = get_ext(file)
    if ext == '.json':
        with open(file_path, "r") as read_file:
            parameters = json.load(read_file)

        for key in parameters:
            for entry in PARAMETER_NAMES:
                if entry.lower() in key.lower():
                    selected_params[key] = parameters[key]
    elif ext in ['.nii', '.nii.gz']:
        nii_image = nib.load(file_path)
        selected_params['obliquity'] = np.any(
            nib.affines.obliquity(nii_image.affine) > 1e-4)
        selected_params['voxel_sizes'] = make_hashable(nii_image.header.get_zooms())
        selected_params['matrix_dims'] = make_hashable(nii_image.shape)
        for key, value in nii_image.header.items():
            if key not in ['sizeof_hdr', 'data_type', 'db_name',
                           'extents', 'session_error']:
                value = make_hashable(value)
                selected_params[key] = value
    return selected_params


def get_ext(file: BIDSFile) -> str:
    """
    Extract the extension from a BIDSFile object.
    Parameters
    ----------
    file : A BIDSFile object

    Returns
    -------
    file extension as a string
    """
    if isinstance(file, BIDSFile):
        return file.tags['extension'].value
    elif isinstance(file, Path):
        return "".join(file.suffixes)
    else:
        raise NotImplementedError('File Format not supported')


def files_in_path(folders: Union[Iterable, str], ext: Optional[str] = None):
    """
    If given a single folder, returns the list of all files in the directory.
    If given a list of folders, returns concatenated list of all the files
    inside each directory.

    Parameters
    ----------
    folders : List[Path]
        List of folder paths
    ext : str
        Used to filter files, and select only those which have this extension
    Returns
    -------
    List of paths
    """
    if isinstance(folders, Iterable):
        files = []
        for i in folders:
            files.extend(list(files_under_folder(i, ext)))
        return files
    return list(files_under_folder(folders, ext))


def files_in_folders(folders: Union[Iterable, Path, str], ext: Optional[str] = None):
    """
    Returns all the files matching the pattern inside each folder.
    One at time via generator.

    Parameters
    ----------
    folders : List[Path]
        List of folder paths
    ext : str
        Extension or pattern to filter files

    Returns
    -------
    List of paths
    """

    if (not isinstance(folders, Iterable)) and isinstance(folders, (Path, str)):
        folders = [folders, ]

    valid_folders = list()
    for folder in folders:
        vfp = Path(folder).resolve()
        if vfp.exists():
            valid_folders.append(folder)

    if len(valid_folders) < 1:
        raise IOError('None of the paths are valid or exist!')

    if ext:
        pattern = '*' + ext
    else:
        pattern = '*'

    for vfp in valid_folders:
        for file in vfp.rglob(pattern):
            # If it is regular file (not hidden, leading dot) and not a directory
            if file.is_file() and (not file.name.startswith('.')):
                yield file

    return


def folders_with_min_files(root: Union[Path, str],
                           pattern: Optional[str] = "*.dcm",
                           min_count=3) -> list[Path]:
    """
    Returns all the folders with at least min_count of files matching the pattern
    One at time via generator.

    Parameters
    ----------
    root : List[Path]
        List of folder paths
    pattern : str
        pattern to filter files

    min_count : int
        size representing the number of files in folder matching the input pattern

    Returns
    -------
    List of folders
    """

    if not isinstance(root, (Path, str)):
        raise ValueError('root must be a Path-like object (str or Path)')

    root = Path(root).resolve()
    if not root.exists():
        raise ValueError('Root folder does not exist')

    terminals = find_terminal_folders(root)

    for folder in terminals:
        if len([file_ for file_ in folder.rglob(pattern)]) >= min_count:
            yield folder

    return


def is_iterable_but_not_str(input_obj):
    """Boolean check for iterables that are not strings and of a minimum length"""

    if not (not isinstance(input_obj, str) and isinstance(input_obj, Iterable)):
        return False


def is_folder_with_no_subfolders(fpath):
    """"""

    sub_dirs = [file_ for file_ in fpath.iterdir() if file_.is_dir()]

    return len(sub_dirs) < 1, sub_dirs


def find_terminal_folders(root):

    no_more_subdirs, sub_dirs = is_folder_with_no_subfolders(root)

    if no_more_subdirs:
        return [root, ]

    terminal = list()
    for sd1 in sub_dirs:
        no_more_subdirs2, level2_subdirs = is_folder_with_no_subfolders(sd1)
        if no_more_subdirs2:
            terminal.append(sd1)
        else:
            for sd2 in level2_subdirs:
                terminal.extend(find_terminal_folders(sd2))

    return terminal


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


def check_mrds_extension(filepath: Union[str, Path]):
    if isinstance(filepath, Path):
        ext = "".join(filepath.suffixes)
    elif isinstance(filepath, str):
        ext = "".join(Path(filepath).suffixes)
    else:
        raise NotImplementedError(f"Expected str or pathlib.Path,"
                                  f" Got {type(filepath)}")
    assert ext == MRDS_EXT, f"Expected extension {MRDS_EXT}, Got {ext}"
