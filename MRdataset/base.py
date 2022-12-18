import importlib
import logging
import pickle
from pathlib import Path
from typing import Union, List

import MRdataset
from MRdataset.config import CACHE_DIR, setup_logger, MRDS_EXT
from MRdataset.core import Project
from MRdataset.utils import valid_dirs, random_name, timestamp


def import_dataset(data_root: Union[str, List[str]] = None,
                   style: str = 'dicom',
                   name: str = None,
                   include_phantom: bool = False,
                   verbose: bool = False,
                   metadata_root: Union[str, Path] = None,
                   include_nifti_header: bool = False,
                   save: bool = True,
                   is_complete: bool = True,
                   cache_path: str = None,
                   **_kwargs) -> "Project":
    """
    Create dataset as per arguments. This function acts as a Wrapper class for
    base.Project. This is the main interface between this package and your
    analysis.

    Parameters
    ----------
    data_root : Union[str, List[str]]
        path/to/my/dataset containing files
    style : str
        Specify dataset type. Imports the module "{style}_dataset.py",
        which will instantiate {Style}Dataset().
    name : str
        Identifier for the dataset, like ADNI. The name used to save cached
        results
    reindex : bool
        Similar to --no-cache. Rejects all cached files and rebuilds index.
    include_phantom: bool
        Whether to include non-subject scans like localizer, acr/phantom,
        aahead_scout
    verbose: bool
        The flag allows you to change the verbosity of execution
    metadata_root: Union[str, Path]
        change the default cache directory
    include_nifti_header: bool
        whether to check nifti headers for compliance,
        only used when --style==bids
    save: bool
        whether to save the dataset or not
    is_complete: bool
        whether the dataset is complete or not
    cache_path: str
        path to the save the dataset
    Returns
    -------
    dataset : MRdataset.core.Project
        dataset container class

    Examples
    --------
    >>> from MRdataset import import_dataset
    >>> data = import_dataset('dicom', '/path/to/my/data/')
    """
    # Check if data_root is valid
    data_root = valid_dirs(data_root)

    # Check if metadata_root is provided by user, otherwise use default
    if not metadata_root:
        metadata_root = Path.home() / CACHE_DIR
        metadata_root.mkdir(exist_ok=True)

    # Check if metadata_root is valid
    if not Path(metadata_root).is_dir():
        raise FileNotFoundError('Expected valid directory for --metadata_root '
                                'argument, Got {0}'.format(metadata_root))
    metadata_root = Path(metadata_root).resolve()

    # Setup logger
    log_filename = metadata_root / '{}_{}.log'.format(name, timestamp())
    if verbose:
        setup_logger('root', log_filename, logging.INFO)
    else:
        setup_logger('root', log_filename, logging.WARNING)

    logger = logging.getLogger('root')

    # Check if name is provided by user, otherwise use random name
    if name is None:
        logger.warning(
            'Expected a unique identifier for caching data. Got NoneType. '
            'Using a random name. Use --name flag for persistent metadata',
            stacklevel=2)
        name = random_name()

    # Find dataset class using style
    dataset_class = find_dataset_using_style(style.lower())

    # Instantiate dataset class
    dataset = dataset_class(
        name=name,
        data_root=data_root,
        metadata_root=metadata_root,
        include_phantom=include_phantom,
        include_nifti_header=include_nifti_header,
        save=save,
        is_complete=is_complete,
        cache_path=cache_path,
        **_kwargs
    )
    dataset.walk()

    # Print dataset summary
    if verbose:
        print(dataset)
    # Return dataset
    return dataset


def find_dataset_using_style(dataset_style: str):
    """
    Imports the module "{style}_dataset.py", which will instantiate
    {Style}Dataset(). For future, please ensure that any {Style}Dataset
    is a subclass of MRdataset.base.Dataset

    Parameters
    ----------
    dataset_style : str
        Specify the type of dataset

    Returns
    -------
    dataset: MRdataset.base.Project()
        dataset container class
    """
    # Import the module "{style}_dataset.py"
    dataset_modulename = "MRdataset.{}_dataset".format(dataset_style)
    dataset_lib = importlib.import_module(dataset_modulename)

    dataset = None
    # Find the class in the module
    target_dataset_class = '{}dataset'.format(dataset_style)
    # Iterate through the module's attributes
    for name, cls in dataset_lib.__dict__.items():
        # If the attribute is a class
        name_matched = name.lower() == target_dataset_class.lower()
        # If the class is a subclass of MRdataset.base.Dataset
        if name_matched and issubclass(cls, Project):
            # Use the class
            dataset = cls

    # If no class was found, raise an error
    if dataset is None:
        raise NotImplementedError(
            "Expected %s to be a subclass of MRdataset.base.Project in % s.py."
            % (target_dataset_class, dataset_modulename))
    # Return the class
    return dataset


def load_mr_dataset(filepath: Union[str, Path],
                    style: str = 'dicom') -> Project:
    """
    Load a dataset from a file

    Parameters
    ----------
    filepath: Union[str, Path]
        path to the dataset file
    style : str
        style of the dataset file. Currently only supports dicom, bids

    Returns
    -------
    dataset : MRdataset.core.Project
        dataset loaded from the file
    """
    logger = logging.getLogger('root')

    if Path(filepath).is_file():
        filepath = Path(filepath)
    else:
        raise FileNotFoundError(f"Invalid filepath {filepath}")

    with open(filepath, 'rb') as f:
        fetched = pickle.load(f)
        if isinstance(fetched, dict):
            # If dict is found, create object and update __dict__
            saved_style = fetched.get('style', None)
            is_complete = fetched.get('is_complete', None)
            if is_complete is False:
                logger.warning("Loading a partial dataset.")
            if saved_style is None:
                dataset_class = find_dataset_using_style(style)
            else:
                dataset_class = find_dataset_using_style(saved_style)
            dataset = dataset_class(
                name=fetched['name'],
                data_root=fetched['data_root'],
                metadata_root=fetched['metadata_root'],
                include_phantom=fetched['include_phantom'],
                reindex=False,
                is_complete=fetched['is_complete'],
                save=False,
                style=fetched['style'],
                cache_path=fetched['cache_path']
            )
            dataset.__dict__.update(fetched)
            return dataset
        elif isinstance(fetched, MRdataset.base.Project):
            # If object is found, return object
            return fetched


def save_mr_dataset(filepath: Union[str, Path],
                    mrds_obj: Project) -> None:
    """
    Save a dataset to a file

    Parameters
    ----------
    filepath: Union[str, Path]
        path to the dataset file
    mrds_obj: MRdataset.core.Project
        dataset to be saved

    Returns
    -------
    None
    """
    # Set cache_path, denotes the path to which dataset saved
    mrds_obj.set_cache_path(filepath)

    # Extract extension from filename
    if isinstance(filepath, Path):
        ext = "".join(filepath.suffixes)
    elif isinstance(filepath, str):
        ext = "".join(Path(filepath).suffixes)
    else:
        raise NotImplementedError(f"Expected str or pathlib.Path,"
                                  f" Got {type(filepath)}")
    assert ext == MRDS_EXT, f"Expected extension {MRDS_EXT}, Got {ext}"

    with open(filepath, "wb") as f:
        # save dict of the object as pickle
        pickle.dump(mrds_obj.__dict__, f)
