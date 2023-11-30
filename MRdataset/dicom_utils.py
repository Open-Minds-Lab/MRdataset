""" Utility functions for dicom files """
import warnings
from pathlib import Path
from typing import Union

import dicom2nifti
import pydicom

from MRdataset import logger

with warnings.catch_warnings():
    warnings.filterwarnings('ignore')


# logger = logging.getLogger('root')


def is_dicom_file(filename: Union[str, Path]):
    """
    The first 4 bytes are read from the file. For a valid DICOM file,
    the bytes should be DICM. Otherwise, it is not a valid DICOM file.
    Parameters
    ----------
    filename : Path | str
        path to the file

    Returns
    -------
    bool : if the file is a DICOM file
    """
    # TODO: Read dicom file : 1
    try:
        with open(filename, 'rb') as file_stream:
            file_stream.seek(128)
            data = file_stream.read(4)
            if data == b'DICM':
                return True
    except FileNotFoundError:
        logger.error(f'File not found : {filename}')
    except PermissionError:
        logger.warning(f'Permission denied : {filename}')
    return False


def is_valid_inclusion(dicom: pydicom.FileDataset,
                       include_phantom=False,
                       include_moco=False,
                       include_sbref=False,
                       include_derived=False,
                       suppress_warnings=False,
                       folder=None) -> bool:
    """
    Function will do some basic checks to see if it is a valid imaging dicom

    Parameters
    ----------
    dicom : pydicom.FileDataset
        dicom object returned by pydicom.dcmread or pydicom.read_file
    include_phantom : bool
        whether to include AAhead_coil/localizer/ACR/Phantom
    include_moco : bool
        whether to include moco series
    include_sbref : bool
        whether to include sbref series
    include_derived : bool
        whether to include derived series
    suppress_warnings : bool
        if folder has been already flagged as localizer, do not raise
        warning again
    folder : str
        path to the dicom folder. Used to raise warning

    Returns
    -------
    bool
    """
    if not dicom2nifti.convert_dir._is_valid_imaging_dicom(dicom):
        logger.info('Invalid file')
        return False

    # TODO: revisit whether to include localizer or not,
    #  it may have relationship with other modalities
    # TODO: make the check more concrete. See dicom2nifti for details

    # check quality control subject :  Not present dicom headers
    series_desc = dicom.get('SeriesDescription', None)
    image_type = dicom.get('ImageType', None)

    if series_desc is None:
        return False

    series_desc = series_desc.lower()
    if not include_phantom:
        phantom_keys = {'localizer', 'aahead'}
        if any(x in series_desc for x in phantom_keys):
            raise_warning('Phantom', folder, suppress_warnings)
            return False
        if is_phantom(dicom):
            raise_warning('Phantom', folder, suppress_warnings)
            return False
    if not include_sbref and 'sbref' in series_desc:
        raise_warning('SBRef', folder, suppress_warnings)
        return False

    if image_type is None:
        return False

    for i in image_type:
        if not include_moco and 'moco' in i.lower():
            raise_warning('MOCO', folder, suppress_warnings)
            return False
        if not include_derived and 'derived' in i.lower():
            raise_warning('Derived', folder, suppress_warnings)
            return False

    return True


def raise_warning(msg: str, path, suppress_warnings=False):
    """
    Raise warning
    Parameters
    ----------
    msg : str
        warning message
    path : str
        path to the file
    suppress_warnings : bool
        whether to suppress warnings. If True, warning will not be raised
    Returns
    -------
    None
    """
    if not suppress_warnings:
        logger.warning(f'Set {msg.lower()} as true in config.json to include.\n'
                       f'Skipping : {path}')


def is_phantom(dicom: pydicom.FileDataset) -> bool:
    """
    Implements a heuristic to detect a phantom. Checks patient's name,
    sex and age, to discriminate a phantom from a real person. It is very
    unlikely that a patient's name is phantom, or age is 1 day.
    Parameters
    ----------
    dicom : pydicom.FileDataset
        dicom object read from pydicom.read_file

    Returns
    -------
    bool
    """

    sid = str(dicom.get('PatientID', None))
    sex = str(dicom.get('PatientSex', None))
    age = str(dicom.get('PatientAge', None))
    if sid and ('phantom' in sid.lower()):
        return True
    if sex and (sex.lower() == 'o'):
        return True
    if age == '001D':
        return True
    return False
