import logging
import warnings
from collections import defaultdict
from pathlib import Path
from typing import Union

import dicom2nifti
import pydicom
from MRdataset import config
from MRdataset import utils
from collections.abc import Iterable

with warnings.catch_warnings():
    warnings.filterwarnings("ignore")
    from nibabel.nicom import csareader


logger = logging.getLogger('root')


def isSameSet(dicom):
    series_uid = dicom.get('SeriesInstanceUID', None)
    # echo_num = dicom.get('EchoNumbers', None)
    echo_time = dicom.get('EchoTime', None)
    # if echo_num:
    #     run_name = series_uid + '_e' + str(dicom.EchoNumbers)
    if echo_time:
        run_name = series_uid + '_e' + str(dicom.EchoTime)
    else:
        run_name = series_uid
    return run_name




def is_valid_inclusion(filename: str,
                       dicom: pydicom.FileDataset,
                       include_phantom=False) -> bool:
    """
    Function will do some basic checks to see if it is a valid imaging dicom

    Parameters
    ----------
    filename : str or Path
        filename for raising the warning
    dicom : pydicom.FileDataset
        dicom object returned by pydicom.dcmread or pydicom.read_file
    include_phantom : bool
        whether to include AAhead_coil/localizer/ACR/Phantom

    Returns
    -------
    bool
    """
    filename = Path(filename).resolve()

    if not dicom2nifti.convert_dir._is_valid_imaging_dicom(dicom):
        logger.info("Invalid file: %s" % filename.parent)
        return False

    # if not header_exists(dicom):
    #     logger.error("Header Absent: %s" % filename)
    #     return False

    # TODO: revisit whether to include localizer or not,
    #  it may have relationship with other modalities
    # TODO: make the check more concrete. See dicom2nifti for details

    # check quality control subject :  Not present dicom headers
    try:
        series_desc = dicom.get('SeriesDescription', None)
        if series_desc is not None:
            series_desc = series_desc.lower()
            if not include_phantom:
                if 'local' in series_desc:
                    logger.info("Localizer: Skipping %s" % filename.parent)
                    return False

                if 'aahead' in series_desc:
                    logger.info("AAhead_Scout: Skipping %s" % filename.parent)
                    return True

                if is_phantom(dicom):
                    logger.info('ACR/Phantom: %s' % filename.parent)
                    return False
    except AttributeError as e:
        logger.warning("Series Description not found in %s" % filename)

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


def get_dicom_modality_tag(dicom: pydicom.FileDataset) -> str:
    """
    Infer modality through dicom tags. In most cases series_description
    should explain the modality of the volume, otherwise either use sequence
    name or protocol name from DICOM metadata

    Parameters
    ----------
    dicom : pydicom.FileDataset
        dicom object read from pydicom.read_file

    Returns
    -------
    str
    """
    property1 = dicom.get('SeriesDescription', None)

    if property1 is None:
        property1 = dicom.get('SequenceName', None)
    if property1 is None:
        property1 = dicom.get('ProtocolName', None)
    if property1 is None:
        return None
    return str(property1.replace(" ", "_"))

# TODO : rename csa
def header_exists(dicom: pydicom.FileDataset) -> bool:
    """
    Check if the private SIEMENS header exists in the file or not. Some
    parameters like effective_echo_spacing and shim method need the dicom
    header to be present.

    Parameters
    ----------
    dicom : pydicom.FileDataset
        dicom object read from pydicom.read_file

    Returns
    -------
    bool
    """
    try:
        series = get_header(dicom, 'series_header_info')
        image = get_header(dicom, 'image_header_info')
        series_header = csareader.read(series)

        # just try reading these values, to bypass any errors,
        # don't need these values now
        # image_header = \
        csareader.read(image)
        # items = \
        series_header['tags']['MrPhoenixProtocol']['items'][0].split('\n')
        return True
    except Exception as e:
        # logger.exception("{}. Expects dicom files from Siemens. "
        #                  "Use --skip_private_header to create report".format(e))
        # raise e
        return False


def parse_imaging_params(dicom_path: Union[str, Path]) -> dict:
    """
    Given a filepath to a .dcm file, the function reader DICOM metadata
    and extracts relevant parameter values for checking compliance.
    The parameters are selected if it is present in config.PARAMETER_NAMES
    Parameters
    ----------
    dicom_path: str or Path
        filepath for .dcm file
    Returns
    -------
    dict
        contains key, value pairs for relevant parameters
    """
    filepath = Path(dicom_path)
    params = defaultdict()

    if not filepath.exists():
        raise OSError("Expected a valid filepath, Got invalid path : {0}\n"
                      "Consider re-indexing dataset.".format(filepath))

    try:
        dicom = pydicom.dcmread(filepath,
                                stop_before_pixels=True)
    except OSError:
        raise FileNotFoundError(
            "Unable to read dicom file from disk : {0}".format(filepath)
        )

    for k in config.PARAMETER_NAMES.keys():
        # try:
        value = get_param_value_by_name(dicom, k)
        # the value should be hashable
        # a dictionary will be used later to count the majority value
        if not isinstance(value, str):
            if isinstance(value, Iterable):
                value = '_'.join(value)
            elif not utils.is_hashable(value):
                value = str(value)
        params[k] = value
        # except:
        #     warnings.warn('Unable to parse parameter {} from \n\t{}'
        #                   ''.format(k, dicom_path))
    is3d = params['MRAcquisitionType'] == '3D'
    params["is3d"] = is3d
    params["effective_echo_spacing"] = effective_echo_spacing(dicom)
    if header_exists(dicom):
        csa_values = csa_parser(dicom)
        params['multi_slice_mode'] = csa_values.get('slice_mode', None)
        params['ipat'] = csa_values.get('ipat', None)
        params['shim'] = csa_values.get('shim', None)
        params["phase_encoding_direction"] = get_phase_encoding(
                                dicom,
                                is3d=params['is3d'],
                                echo_train_length=params['EchoTrainLength'])
    else:
        params['multi_slice_mode'] = None
        params['ipat'] = None
        params['shim'] = None
        params['phase_encoding_direction'] = None
    return params


def get_param_value_by_name(dicom, name):
    """
    Extracts value from dicom metadata looking up the corresponding HEX tag
    in config.PARAMETER_NAMES

    Parameters
    ----------
    dicom : pydicom.FileDataset
        dicom object read from pydicom.read_file

    name : str
        parameter name such as MagneticFieldStrength or Manufacturer

    Returns
    -------
    This method return a value for the given key. If key is not available,
    then returns default value None.
    """
    # TODO: consider name.lower()
    data = dicom.get(config.PARAMETER_NAMES[name], None)
    if data:
        return data.value
    return None


def get_header(dicom, name):
    """
    Extracts value from dicom headers looking up the corresponding HEX tag
    in config.HEADER_TAGS

    Parameters
    ----------
    dicom : pydicom.FileDataset
        dicom object read from pydicom.read_file

    name : str
        parameter name such as ImageHeader or SeriesHeader

    Returns
    -------
    This method return a value for the given key. If key is not available,
    then returns default value None.
    """
    data = dicom.get(config.HEADER_TAGS[name], None)
    if data:
        return data.value
    return None


# def get_tags_by_name(dicom, name):
#     """
#     Extracts value from dicom metadata looking up the corresponding HEX tag
#     in config.PARAMETER_NAMES
#
#     Parameters
#     ----------
#     dicom : pydicom.FileDataset
#         dicom object read from pydicom.read_file
#
#     name : str
#         parameter name such as MagneticFieldStrength or Manufacturer
#
#     Returns
#     -------
#     This method return a value for the given key. If key is not available,
#     then returns default value None.
#     """
#     data = dicom.get(config.TAGS[name], None)
#     if data is None:
#         return None
#     return data.value


def csa_parser(dicom):
    """
    Handles the private CSA header from Siemens formatted raw scanner.

    Parameters
    ----------
    dicom : pydicom.FileDataset
        dicom object read from pydicom.read_file

    Returns
    -------
    dict
        Contains multi-slice mode, iPAT and shim_mode

    """
    series_header = csareader.read(get_header(dicom, 'series_header_info'))
    items = utils.safe_get(series_header, 'tags.MrPhoenixProtocol.items')
    if items:
        text = items[0].split("\n")
    else:
        raise AttributeError('CSA Header exists, but xProtocol is missing')

    start = False
    end = False
    props = {}
    for e in text:
        if e[:15] == '### ASCCONV END':
            end = True
        if start and not end:
            ele = e.split()
            if ele[1].strip() == "=":
                props[ele[0]] = ele[2]
        if e[:17] == '### ASCCONV BEGIN':
            start = True

    slice_code = props.get("sKSpace.ucMultiSliceMode", None)
    slice_mode = config.SLICE_MODE.get(slice_code, None)

    ipat_code = props.get("sPat.ucPATMode", None)
    ipat = config.PAT.get(ipat_code, None)

    shim_code = props.get("sAdjData.uiAdjShimMode", None)
    shim = config.SHIM.get(shim_code, None)

    return {
        'slice_mode': slice_mode,
        'ipat': ipat,
        'shim': shim
    }


def effective_echo_spacing(dicom):
    # if self.get("echo_train_length") > 1: # Check if etl == pel
    # check =
    # (self.get("echo_train_length") == self.get("phase_encoding_lines"))
    # if not check:
    # print("PhaseEncodingLines is not equal to EchoTrainLength
    # : {0}".format(self.filepath))

    bwp_phase_encode = get_param_value_by_name(dicom, 'PixelBandwidth')
    phase_encoding = get_param_value_by_name(dicom, 'PhaseEncodingSteps')

    if (bwp_phase_encode is None) or (phase_encoding is None):
        return None
    else:
        try:
            value = 1000 / (bwp_phase_encode * phase_encoding)
        except ZeroDivisionError as exc:
            logger.exception(exc)
            return None
        # Match value to output of dcm2niix
        return value / 1000


def get_phase_encoding(dicom, is3d, echo_train_length):
    """
    https://github.com/rordenlab/dcm2niix/blob/23d087566a22edd4f50e4afe829143cb8f6e6720/console/nii_dicom_batch.cpp
    https://neurostars.org/t/determining-bids-phaseencodingdirection-from-dicom/612/6 # noqa
    Following code only for SEIMENS, Look into above links for GE, Philips etc.
    """
    # is_skip = False
    # if is3d:
    #     is_skip = True
    # if echo_train_length > 1:
    #     is_skip = False
    image_header = csareader.read(get_header(dicom, 'image_header_info'))
    phase_value = utils.safe_get(image_header,
                                 'tags.PhaseEncodingDirectionPositive.items')
    if phase_value:
        phase = phase_value[0]
        ped_value = get_param_value_by_name(dicom, "PhaseEncodingDirection")
        if ped_value in ['ROW', 'COL']:
            ped = ped_value
        else:
            return None

        niftidim = {'COL': 'i', 'ROW': 'j'}
        ped_to_sign = {0: '-', 1: ''}
        ij = niftidim[ped]
        sign = ped_to_sign[phase]
        return '{}{}'.format(ij, sign)
    return None
