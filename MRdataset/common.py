import pickle
from pathlib import Path
from typing import Union, List

from MRdataset import logger
from MRdataset.base import BaseDataset
from MRdataset.bids import BidsDataset
from MRdataset.config import VALID_DATASET_FORMATS
from MRdataset.dicom import DicomDataset
from MRdataset.utils import random_name, check_mrds_extension


# TODO: data_source can be Path or str or List. Modify type hints
def import_dataset(data_source: Union[str, List, Path] = None,
                   ds_format: str = 'dicom',
                   name: str = None,
                   verbose: bool = False,
                   is_complete: bool = True,
                   config_path: Union[str, Path] = None,
                   **_kwargs) -> 'BaseDataset':
    """
    Create dataset as per arguments. This function acts as a Wrapper class for
    base.BaseDataset. This is the main interface between this package and your
    analysis.

    Parameters
    ----------
    data_source : Union[str, List[str]]
        path/to/my/dataset containing files
    ds_format : str
        Specify dataset type. Imports the module "{ds_format}_dataset.py",
        which will instantiate {Style}Dataset().
    name : str
        Identifier for the dataset, like ADNI. The name used to save cached
        results
    verbose: bool
        The flag allows you to change the verbosity of execution
    is_complete: bool
        whether the dataset is complete or not
    config_path: Union[str, Path]
        path to config file
    Returns
    -------
    dataset : MRdataset.__base.BaseDataset
        dataset container class

    Examples
    --------
    >>> from MRdataset import import_dataset
    >>> data = import_dataset('dicom', '/path/to/my/data/')
    """
    # TODO: Option to curb logger messages inside import_dataset.
    #  This would ensure option verbose for both python scripts and cli.
    #  Consider removing it from cli.main
    if verbose:
        logger.setLevel('INFO')
    else:
        logger.setLevel('WARNING')

    if data_source is None:
        raise ValueError(f'Please provide a valid data source.'
                         f' Got NoneType. ')
    # Check if name is provided by user, otherwise use random name
    if name is None:
        logger.info(
            'Expected a unique identifier for caching data. Got NoneType. '
            'Using a random name. Use --name flag for persistent metadata',
            stacklevel=2)
        name = random_name()

    # Find dataset class using ds_format
    dataset_class = find_dataset_using_ds_format(ds_format.lower())

    # Instantiate dataset class
    dataset = dataset_class(
        data_source=data_source,
        verbose=verbose,
        is_complete=is_complete,
        name=name,
        config_path=config_path,
        **_kwargs
    )
    dataset.load()
    # Print dataset summary
    if verbose:
        print(dataset)
    return dataset


def find_dataset_using_ds_format(dataset_ds_format: str):
    """
    Find dataset class using ds_format. This function is used by
    import_dataset() to find the dataset class.

    Parameters
    ----------
    dataset_ds_format : str
        Specify the type of dataset

    Returns
    -------
    dataset: MRdataset.base.BaseDataset()
        dataset container class
    """
    # Import the module "{ds_format}_dataset.py"
    if dataset_ds_format == 'dicom':
        dataset_class = DicomDataset
    elif dataset_ds_format == 'bids':
        dataset_class = BidsDataset
    else:
        raise NotImplementedError(
            f'Dataset ds_format {dataset_ds_format} is not implemented. '
            f"Valid choices are {', '.join(VALID_DATASET_FORMATS)}")
    return dataset_class


def load_mr_dataset(filepath: Union[str, Path]) -> 'BaseDataset':
    """
    Load a dataset from a file

    Parameters
    ----------
    filepath: Union[str, Path]
        path to the dataset file
    Returns
    -------
    dataset : BaseDataset
        dataset loaded from the file
    """
    check_mrds_extension(filepath)

    if isinstance(filepath, str):
        filepath = Path(filepath)

    if not filepath.is_file():
        raise FileNotFoundError(f'Invalid filepath {filepath}')

    with open(filepath, 'rb') as f:
        fetched = pickle.load(f)
        if isinstance(fetched, BaseDataset):
            # If object is found, return object
            return fetched
        else:
            # If object is different type, raise error
            raise TypeError(f'Expected {type(BaseDataset)} '
                            f'but got {type(fetched)}')


def save_mr_dataset(filepath: Union[str, Path],
                    mrds_obj: 'BaseDataset') -> None:
    """
    Save a dataset to a file

    Parameters
    ----------
    filepath: Union[str, Path]
        path to the dataset file
    mrds_obj: BaseDataset
        dataset to be saved

    Returns
    -------
    None
    """

    # Extract extension from filename
    check_mrds_extension(filepath)

    parent_folder = Path(filepath).parent
    try:
        parent_folder.mkdir(exist_ok=True, parents=True)
    except OSError as exc:
        logger.error(f'Unable to create folder {parent_folder} for saving dataset')
        raise exc

    with open(filepath, 'wb') as f:
        # save dict of the object as pickle
        pickle.dump(mrds_obj, f)
