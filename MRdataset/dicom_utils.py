""" Utility functions for dicom files """
import re
import warnings
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import Union, Optional

import dicom2nifti
import pydicom
from MRdataset import config
from MRdataset import utils
from MRdataset.log import logger
from MRdataset.utils import slugify

with warnings.catch_warnings():
    warnings.filterwarnings('ignore')
    from nibabel.nicom import csareader


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
    with open(filename, 'rb') as file_stream:
        file_stream.seek(128)
        data = file_stream.read(4)

    if data == b'DICM':
        return True


def is_same_set(dicom: pydicom.FileDataset) -> str:
    """
    Provides a unique id for Series, to which the input dicom file
    belongs to.

    Parameters
    ----------
    dicom : pydicom.FileDataset
        dicom object returned by pydicom.dcmread or pydicom.read_file

    Returns
    -------
    Series identifier to which this DICOM should be added to
    """
    series_uid = dicom.get('SeriesInstanceUID', None)
    # Convert pydicom.valuerep.MultiValue to int
    try:
        echo_num = int(dicom.get('EchoNumbers', None))
    except TypeError as e:
        echo_num = 1
        logger.warning(f'Got {e}')
    # Need to convert pydicom.valuerep.DSfloat to float
    # echo_time = float(dicom.get('EchoTime', None))
    if echo_num > 1:
        run_name = series_uid + '_en_' + str(echo_num)
    else:
        run_name = series_uid
    #     run_name = series_uid
    # else:
    # else:
    # run_name = series_uid
    return run_name


def is_valid_inclusion(filepath: str,
                       dicom: pydicom.FileDataset,
                       include_phantom=False) -> bool:
    """
    Function will do some basic checks to see if it is a valid imaging dicom

    Parameters
    ----------
    filepath : str or Path
        filename for raising the warning
    dicom : pydicom.FileDataset
        dicom object returned by pydicom.dcmread or pydicom.read_file
    include_phantom : bool
        whether to include AAhead_coil/localizer/ACR/Phantom

    Returns
    -------
    bool
    """
    filepath = Path(filepath).resolve()

    if not dicom2nifti.convert_dir._is_valid_imaging_dicom(dicom):
        logger.info('Invalid file: %s', filepath.parent)
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
                    logger.info('Localizer: Skipping %s', filepath.parent)
                    return False

                if 'aahead' in series_desc:
                    logger.info('AAhead_Scout: Skipping %s', filepath.parent)
                    return False

                if is_phantom(dicom):
                    logger.info('ACR/Phantom: %s', filepath.parent)
                    return False
    except AttributeError as e:
        logger.warning('%s :Series Description not found in %s' % (e, filepath))

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
        return 'MR_image'
    ret_value = slugify(property1)
    if ret_value:
        return ret_value
    return 'MR_image'


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
        logger.info(f'Expects dicom files from Siemens to be able to'
                    f' read the private header. For other vendors',
                    f'private header is skipped. '
                    f'{e} in {dicom.filename}')
        # "Use --skip_private_header to create report".format(e))
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

    Raises
    ------

    """
    filepath = Path(dicom_path)
    params = defaultdict()

    if not filepath.exists():
        raise OSError(f'Expected a valid filepath,Got invalid path : {filepath}'
                      f'\n. Consider re-indexing dataset.')

    try:
        # TODO: Read dicom file : 3
        dicom = pydicom.dcmread(filepath,
                                stop_before_pixels=True)
    except OSError as exc:
        raise FileNotFoundError(
            f'Unable to read dicom file from disk : {filepath}'
        ) from exc

    for k in config.PARAMETER_NAMES.keys():
        value = get_param_value_by_name(dicom, k)
        # the value should be hashable
        # a dictionary will be used later to count the majority value
        if not isinstance(value, str):
            if isinstance(value, Iterable):
                value = '_'.join([str(i) for i in sorted(value)])
            elif not utils.is_hashable(value):
                value = str(value)
        params[k] = value
    is3d = params['MRAcquisitionType'] == '3D'
    params['is3d'] = is3d
    params['effective_echo_spacing'] = effective_echo_spacing(dicom)
    if header_exists(dicom):
        csa_values = csa_parser(dicom)
        params['multi_slice_mode'] = csa_values.get('slice_mode', None)
        params['ipat'] = csa_values.get('ipat', None)
        params['shim'] = csa_values.get('shim', None)
        params['phase_polarity'] = get_phase_polarity(dicom)
        # params['phase_encoding_direction'] = get_phase_encoding(dicom)
    else:
        params['multi_slice_mode'] = None
        params['ipat'] = None
        params['shim'] = None
        params['phase_polarity'] = None
        # params['phase_encoding_direction'] = None
    return params


def get_param_value_by_name(dicom: pydicom.FileDataset, name: str):
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


def get_header(dicom: pydicom.FileDataset, name: str):
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


def csa_parser(dicom: pydicom.FileDataset) -> dict:
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

    Raises
    ------
    AttributeError
        If CSA header exists but xProtocol string is missing

    """
    series_header = csareader.read(get_header(dicom, 'series_header_info'))
    items = utils.safe_get(series_header, 'tags.MrPhoenixProtocol.items')
    if items:
        text = items[0]
    else:
        raise AttributeError('CSA Header exists, but xProtocol is missing')

    slice_code = get_csa_props('sKSpace.ucMultiSliceMode', text)
    slice_mode = config.SLICE_MODE.get(slice_code, slice_code)
    ipat_code = get_csa_props('sPat.ucPATMode', text)
    ipat = config.PAT.get(ipat_code, ipat_code)
    shim_code = get_csa_props('sAdjData.uiAdjShimMode', text)
    shim = config.SHIM.get(shim_code, shim_code)

    return {
        'slice_mode': slice_mode,
        'ipat': ipat,
        'shim': shim
    }


def get_csa_props(parameter, corpus):
    """Extract parameter code from CSA header text

    we want 0x1 from e.g.
    sAdjData.uiAdjShimMode                = 0x1
    """
    index = corpus.find(parameter)
    if index == -1:
        return -1

    shift = len(parameter) + 6
    if index + shift > len(corpus):
        print(f"#WARNING: {parameter} in CSA too short: '{corpus[index:]}'")
        return -1

    # 6 chars after parameter text, 3rd value
    param_val = corpus[index:index + shift]
    code_parts = re.split('[\t\n]', param_val)
    if len(code_parts) >= 3:
        return code_parts[2]

    # if not above, might look like:
    # sAdjData.uiAdjShimMode                = 0x1

    # this runs multiple times on every dicom
    # regexp is expensive? don't use unless we need to
    match = re.search(r'=\s*([^\n]+)', corpus[index:])
    if match:
        match = match.groups()[0]
        # above is also a string. don't worry about conversion?
        # match = int(match, 0)  # 0x1 -> 1
        return match

    # couldn't figure out
    return -1


def effective_echo_spacing(dicom: pydicom.FileDataset) -> Optional[float]:
    """
    Calculates effective echo spacing in sec.
    * For Siemens
    Effective Echo Spacing (s) =
    (BandwidthPerPixelPhaseEncode * MatrixSizePhase)^-1

    * For Philips
    echo spacing (msec) =
     1000*water-fat shift (per pixel)/(water-fat shift(in Hz)*echo_train_length)

    Parameters
    ----------
    dicom : pydicom.FileDataset
        dicom object returned by pydicom.dcmread or pydicom.read_file

    Returns
    -------
    float value for effective echo spacing
    """
    bwp_phase_encode = get_param_value_by_name(dicom, 'PixelBandwidth')
    phase_encoding = get_param_value_by_name(dicom, 'PhaseEncodingSteps')

    if (bwp_phase_encode is None) or (phase_encoding is None):
        return None
    denominator = bwp_phase_encode * phase_encoding
    if denominator:
        value = 1000 / denominator
        # Match value to output of dcm2niix
        return value / 1000
    else:
        return None


def get_phase_polarity(dicom: pydicom.FileDataset) -> Optional[int]:
    """
    Get phase polarity from dicom header

    Parameters
    ----------
    dicom : pydicom.FileDataset
        dicom object returned by pydicom.dcmread or pydicom.read_file

    Returns
    -------
    int value for phase polarity
    """
    image_header = csareader.read(get_header(dicom, 'image_header_info'))
    phase_value = utils.safe_get(image_header,
                                 'tags.PhaseEncodingDirectionPositive.items')
    if phase_value:
        return phase_value[0]
    return None


def get_phase_encoding(dicom: pydicom.FileDataset) -> Optional[str]:
    """
    https://github.com/rordenlab/dcm2niix/blob/23d087566a22edd4f50e4afe829143cb8f6e6720/console/nii_dicom_batch.cpp
    https://github.com/rordenlab/dcm2niix/issues/652#issuecomment-1323623521
    https://www.rad.pitt.edu/extract-phase-encoding.html
                            Polarity
                    |  1        |   0       |
    InPlanePED  ROW |  R >> L   |   L >> R  |
                COL |  A >> P   |   P >> A  |

                            Polarity
                    |   1   |   0   |
    InPlanePED  ROW |   i   |   i-  |
                COL |   j   |   j-  |

    Following code only for Siemens, Look into above links for GE, Philips etc.

    Parameters
    ----------
    dicom : pydicom.FileDataset
        dicom object returned by pydicom.dcmread or pydicom.read_file

    Returns
    -------
    string formatted phase encoding direction
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
        ped_value = get_param_value_by_name(dicom, 'PhaseEncodingDirection')
        if ped_value in ['ROW', 'COL']:
            ped = ped_value
        else:
            return None

        nifti_dim = {'COL': 'j', 'ROW': 'i'}
        ped_to_sign = {0: '-', 1: ''}
        ij = nifti_dim[ped]
        sign = ped_to_sign[phase]
        return f'{ij}{sign}'
    return None


def combine_varying_params(parameter_diff_list, params, filepath):
    #   If a different slice is read first, it would lead
    #   to differences in parameters for the run. How to
    #   reconcile ? For ex. in one case, there was a single
    #   dcm file with PED, others didn't have this key.
    #   Depending upon which file is read first, the
    #   parameters are added to run, which is a serious issue.
    #   TODO : Can we maintain a list of values, this would make things simple
    #       especially for multi-echo time modalities. Right now, it has a
    #       single value for each parameter.
    # dcm2niix also raises warnings if parameter value varies. For an example
    # See https://github.com/rordenlab/dcm2niix/blob/bb3a6c35d2bbac6ed95acb2cd0df65f35e79b5fb/console/nii_dicom.cpp#L2352 # noqa

    # If previous value was None, and another dcm file
    # has a value (not None), replace None in params.
    for item in parameter_diff_list:
        if item[0] == 'change':
            _, parameter_name, [new_value, old_value] = item
            if new_value is not None:
                if old_value is None:
                    params[parameter_name] = new_value
                else:
                    logger.warning(f'Slices with varying {parameter_name} '
                                   f'Expected {old_value}, Got {new_value} in '
                                   f'{filepath}')
        elif item[0] == 'add':
            logger.debug('Not expected. Report event - %s', item[0])
            for parameter_name, value in item[2]:
                params[parameter_name] = value
        else:
            logger.debug('Not expected. Report event - %s', item[0])
    return params
