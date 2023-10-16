""" Utility functions for dicom files """
import warnings

import dicom2nifti
import pydicom
from MRdataset import logger

with warnings.catch_warnings():
    warnings.filterwarnings('ignore')


# logger = logging.getLogger('root')


def is_dicom_file(filename: str):
    """
    The first 4 bytes are read from the file. For a valid DICOM file,
    the bytes should be DICM. Otherwise, it is not a valid DICOM file.
    Parameters
    ----------
    filename : str
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
    return False



def is_valid_inclusion(dicom: pydicom.FileDataset,
                       include_phantom=False,
                       include_moco=False,
                       include_sbref=False,
                       include_derived=False) -> bool:
    """
    Function will do some basic checks to see if it is a valid imaging dicom

    Parameters
    ----------
    dicom : pydicom.FileDataset
        dicom object returned by pydicom.dcmread or pydicom.read_file
    include_phantom : bool
        whether to include AAhead_coil/localizer/ACR/Phantom

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

    if series_desc is not None:
        series_desc = series_desc.lower()
        if not include_phantom:
            if 'local' in series_desc:
                # logger.info('Localizer: Skipping %s', filepath.parent)
                return False
            if 'aahead' in series_desc:
                # logger.info('AAhead_Scout: Skipping %s', filepath.parent)
                return False
            if is_phantom(dicom):
                # logger.info('ACR/Phantom: %s', filepath.parent)
                return False
        if not include_sbref:
            if 'sbref' in series_desc:
                return False
    else:
        return False

    if image_type is not None:
        for i in image_type:
            if not include_moco and 'moco' in i.lower():
                return False
            if not include_derived and 'derived' in i.lower():
                return False
    else:
        return False

    return True


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
