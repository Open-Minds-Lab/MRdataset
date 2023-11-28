import pickle
from pathlib import Path
from typing import Union, List

from MRdataset import logger
from MRdataset.base import BaseDataset
from MRdataset.config import VALID_DATASET_FORMATS
from MRdataset.dicom import DicomDataset
from MRdataset.utils import random_name, check_mrds_extension


# TODO: data_source can be Path or str or List. Modify type hints
def import_dataset(data_source: Union[str, Path, List],
                   ds_format: str = 'dicom',
                   name: str = None,
                   verbose: bool = False,
                   is_complete: bool = True,
                   config_path: Union[str, Path] = None,
                   output_dir: Union[str, Path] = None,
                   **_kwargs) -> 'BaseDataset':
    """
    Create MRdataset from data source as per arguments. This function acts as a
    Wrapper class for
    BaseDataset. This is the main interface between this package and your
    dataset. This function is used by the CLI and the python scripts.

    Parameters
    ----------
    data_source : Union[str, Path, List]
        path/to/my/dataset containing files e.g. .dcm
    ds_format : str
        Specify dataset type. Imports the module "{ds_format}.py",
        which will instantiate {ds_format}Dataset().
    name : str
        Name/Identifier for your dataset, like ADNI. The name used to save files
        and reports. If not provided, a random name is generated e.g. 54231
    verbose: bool
        The flag allows you to change the verbosity of execution
    is_complete: bool
        whether the dataset is subset of a larger dataset. It is useful for
         parallel processing of large datasets.
    config_path: Union[str, Path]
        path to config file which contains the rules for reading the dataset
        e.g.
        sequences to read, subjects to ignore, etc.
    output_dir: Union[str, Path]
        path to the directory where the output files will be saved.

    Returns
    -------
    dataset : BaseDataset
        dataset object containing the dataset

    Examples
    --------
    .. code :: python

        from MRdataset import import_dataset
        data = import_dataset(data_source='/path/to/my/data/',
                              ds_format='dicom', name='abcd_baseline',
                              config_path='mri-config.json',
                              output_dir='/path/to/my/output/dir/')
    """
    # TODO: Option to curb logger messages inside import_dataset.
    #  This would ensure option verbose for both python scripts and cli.
    #  Consider removing it from cli.main
    # if verbose:
    #     logger = configure_logger(logger, output_dir=output_dir,
    #                               mode='w', level='WARNING')
    # else:
    #     logger = configure_logger(logger, output_dir=output_dir,
    #                               mode='w', level='ERROR')
    if output_dir is None:
        # Use current working directory as output directory
        output_dir = Path.cwd()
    if config_path is None:
        THIS_DIR = Path(__file__).parent.resolve()
        config_path = THIS_DIR / 'resources/mri-config.json'
    if data_source is None:
        raise ValueError('Please provide a valid data source.'
                         ' Got NoneType. ')
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
        output_dir=output_dir,
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
    dataset: BaseDataset()
        dataset container class

    """
    # Import the module "{ds_format}_dataset.py"
    if dataset_ds_format == 'dicom':
        dataset_class = DicomDataset
    else:
        raise NotImplementedError(
            f'Dataset ds_format {dataset_ds_format} is not implemented. '
            f"Valid choices are {', '.join(VALID_DATASET_FORMATS)}")
    return dataset_class


def load_mr_dataset(filepath: Union[str, Path]) -> 'BaseDataset':
    """
    Load a dataset from a file. The file must be a pickle file with extension
    .mrds.pkl

    Parameters
    ----------
    filepath: Union[str, Path]
        path to the dataset file

    Returns
    -------
    dataset : BaseDataset
        dataset loaded from the file

    Examples
    --------
    .. code :: python

        from MRdataset import load_mr_dataset
        dataset = load_mr_dataset('/path/to/my/dataset.mrds.pkl')
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
    Save a dataset to a file with extension .mrds.pkl

    Parameters
    ----------
    filepath: Union[str, Path]
        path to the dataset file
    mrds_obj: BaseDataset
        dataset to be saved

    Returns
    -------
    None

    Examples
    --------
    .. code :: python

        from MRdataset import save_mr_dataset
        my_dataset = import_dataset(data_source='/path/to/my/data/',
                      ds_format='dicom', name='abcd_baseline',
                      config_path='mri-config.json')
        dataset = save_mr_dataset(filepath='/path/to/my/dataset.mrds.pkl',
                                  mrds_obj=my_dataset)
    """

    # Extract extension from filename
    check_mrds_extension(filepath)

    parent_folder = Path(filepath).parent
    try:
        parent_folder.mkdir(exist_ok=True, parents=True)
    except OSError as exc:
        logger.error(f'Unable to create folder {parent_folder} '
                     'for saving dataset')
        raise exc

    if isinstance(mrds_obj, DicomDataset):
        mrds_obj.save_process_log(parent_folder)
    with open(filepath, 'wb') as f:
        # save dict of the object as pickle
        pickle.dump(mrds_obj, f)
