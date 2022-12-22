import importlib
import pickle
from pathlib import Path
from typing import Union, List

import MRdataset
from MRdataset.base import BaseDataset
from MRdataset.utils import valid_dirs, random_name, check_mrds_extension
from MRdataset.log import logger
from MRdataset import dicom, bids, fastbids
from MRdataset.config import VALID_DATASET_STYLES


def import_dataset(data_source_folders: Union[str, List[str]] = None,
                   style: str = 'dicom',
                   name: str = None,
                   include_phantom: bool = False,
                   verbose: bool = False,
                   include_nifti_header: bool = False,
                   is_complete: bool = True,
                   **_kwargs) -> "BaseDataset":
    """
    Create dataset as per arguments. This function acts as a Wrapper class for
    base.BaseDataset. This is the main interface between this package and your
    analysis.

    Parameters
    ----------
    data_source_folders : Union[str, List[str]]
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
    dataset : MRdataset.base.BaseDataset
        dataset container class

    Examples
    --------
    >>> from MRdataset import import_dataset
    >>> data = import_dataset('dicom', '/path/to/my/data/')
    """
    # Check if data_root is valid
    data_source_folders = valid_dirs(data_source_folders)

    # Check if name is provided by user, otherwise use random name
    if name is None:
        logger.info(
            'Expected a unique identifier for caching data. Got NoneType. '
            'Using a random name. Use --name flag for persistent metadata',
            stacklevel=2)
        name = random_name()

    # Find dataset class using style
    dataset_class = find_dataset_using_style(style.lower())

    # Instantiate dataset class
    dataset = dataset_class(
        data_source_folders=data_source_folders,
        include_phantom=include_phantom,
        verbose=verbose,
        include_nifti_header=include_nifti_header,
        is_complete=is_complete,
        name=name,
        **_kwargs
    )
    dataset.walk()

    # Print dataset summary
    if verbose:
        print(dataset)
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
    dataset: MRdataset.base.BaseDataset()
        dataset container class
    """
    # Import the module "{style}_dataset.py"
    if dataset_style == 'dicom':
        dataset_class = dicom.DicomDataset
    elif dataset_style == 'bids':
        dataset_class = bids.BIDSDataset
    elif dataset_style == 'fastbids':
        dataset_class = fastbids.FastBIDSDataset
    else:
        raise NotImplementedError(
            f"Dataset style {dataset_style} is not implemented. Valid choices"
            f"are {', '.join(VALID_DATASET_STYLES)}")
    return dataset_class


def load_mr_dataset(filepath: Union[str, Path],
                    style: str = 'dicom') -> BaseDataset:
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
    dataset : MRdataset.base.BaseDataset
        dataset loaded from the file
    """
    check_mrds_extension(filepath)

    if Path(filepath).is_file():
        filepath = Path(filepath)
    else:
        raise FileNotFoundError(f"Invalid filepath {filepath}")

    with open(filepath, 'rb') as f:
        fetched = pickle.load(f)
        if isinstance(fetched, BaseDataset):
            # If object is found, return object
            return fetched
        else:
            # If object is different type, raise error
            raise TypeError(f"Expected {type(BaseDataset)} "
                            f"but got {type(fetched)}")


def save_mr_dataset(filepath: Union[str, Path],
                    mrds_obj: BaseDataset) -> None:
    """
    Save a dataset to a file

    Parameters
    ----------
    filepath: Union[str, Path]
        path to the dataset file
    mrds_obj: MRdataset.base.BaseDataset
        dataset to be saved

    Returns
    -------
    None
    """

    # Extract extension from filename
    check_mrds_extension(filepath)

    parent_folder = Path(filepath).parent
    parent_folder.mkdir(exist_ok=True, parents=True)

    with open(filepath, "wb") as f:
        # save dict of the object as pickle
        pickle.dump(mrds_obj, f)
