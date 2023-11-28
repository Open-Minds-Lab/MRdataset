import json
import re
import tempfile
import time
import unicodedata
import uuid
from collections.abc import Iterable
from pathlib import Path
from typing import Union, List, Optional

from MRdataset.config import MRDS_EXT


def random_name() -> str:
    """
    Function to generate a random identifier/name

    Returns
    -------
    random_number cast to string
    """
    return str(hash(str(uuid.uuid1())) % 1000000)


def timestamp() -> str:
    """
    Generates time string in the specified format

    Returns
    -------
    time formatted as string
    """
    time_string = time.strftime("%m_%d_%Y_%H_%M")
    return time_string


def folders_with_min_files(root: Union[Path, str],
                           pattern: Optional[str] = "*.dcm",
                           min_count=3) -> List[Path]:
    """
    Returns all the folders with at least min_count of files
    matching the pattern. One at time via generator.

    Parameters
    ----------
    root : List[Path]
        List of folder paths
    pattern : str
        pattern to filter files
    min_count : int
        size representing the number of files in folder
        matching the input pattern

    Returns
    -------
    List of folders
    """

    if not isinstance(root, (Path, str)):
        raise ValueError('root must be a Path-like object (str or Path)')

    if not root.exists():
        raise ValueError('Root folder does not exist')
    root = Path(root).resolve()

    terminals = find_terminal_folders(root)

    for folder in terminals:
        if len([file_ for file_ in folder.rglob(pattern)]) >= min_count:
            yield folder

    return


def is_folder_with_no_subfolders(fpath):
    """
    Check if the folder has any subfolders

    Parameters
    ----------
    fpath: str | Path
        filepath pointing to the folder
    """
    if isinstance(fpath, str):
        fpath = Path(fpath)
    if not fpath.is_dir():
        raise FileNotFoundError(f'Folder not found: {fpath}')

    sub_dirs = [file_ for file_ in fpath.iterdir() if file_.is_dir()]

    return len(sub_dirs) < 1, sub_dirs


def find_terminal_folders(root):
    """
    Find all the terminal folders in the given root folder

    Parameters
    ----------
    root: str | Path
        filepath pointing to the folder
    """
    try:
        no_more_subdirs, sub_dirs = is_folder_with_no_subfolders(root)
    except FileNotFoundError:
        return []

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


def valid_dirs(folders: Union[List, Path, str]) -> List:
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
        return [Path(folders).resolve()]
    elif isinstance(folders, Iterable):
        for folder in folders:
            if not Path(folder).is_dir():
                raise OSError('Invalid directory {0}'.format(folder))
        return [Path(f).resolve() for f in folders]
    else:
        raise ValueError('Expected str or Path or Iterable, '
                         f'Got {type(folders)}')


def convert2ascii(value, allow_unicode=False):
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
    value = re.sub(r'[^\w\s-]', '', value)
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
    try:
        filepath = Path(filepath)
    except TypeError:
        raise TypeError(f'Expected str or pathlib.Path, Got {type(filepath)}')
    ext = "".join(Path(filepath).suffixes)
    assert ext == MRDS_EXT, f"Expected extension {MRDS_EXT}, Got {ext}"


def read_json(filepath: Path):
    """
    Read json file and return a dictionary

    Parameters
    ----------
    filepath: str or pathlib.Path
        filepath pointing to the file
    """
    try:
        filepath = Path(filepath)
    except TypeError:
        raise TypeError(f'Expected str or pathlib.Path, Got {type(filepath)}')

    if not filepath.is_file():
        raise FileNotFoundError(f'File not found: {filepath}')

    with open(filepath, 'r') as fp:
        try:
            dict_ = json.load(fp)
        except ValueError as e:
            raise ValueError(f'Error while reading {filepath}: {e}')
    return dict_


def is_writable(dir_path):
    """
    Check if the directory is writable

    Parameters
    ----------
    dir_path: str or pathlib.Path
        filepath pointing to the directory

    Returns
    -------
    bool
    """
    try:
        with tempfile.TemporaryFile(dir=dir_path, mode='w') as testfile:
            testfile.write("OS write to directory test.")
    except (OSError, IOError):
        return False
    return True
