import logging
from collections import defaultdict
from pathlib import Path

import dicom2nifti
import pydicom
from nibabel.nicom import csareader

from MRdataset import common
from MRdataset import config
from MRdataset import utils
from typing import Union
logger = logging.getLogger('root')


def is_valid_inclusion(filename: str,
                       dicom: pydicom.FileDataset,
                       include_phantom=False) -> bool:
    """
    Function will do some basic checks to see if it is a valid imaging dicom
    @param filename: path for raising the warning
    @param dicom: pydicom.FileDataset instance returned
                  from pydicom.read_file
    @param include_phantom: whether to include
                            AAhead_coil/localizer/ACR/Phantom in report
    @return: bool
    """
    if not dicom2nifti.convert_dir._is_valid_imaging_dicom(dicom):
        config.warn_once(logger, "Invalid file: %s" % filename)
        return False

    if not common.header_exists(dicom):
        config.warn_once(logger, "Header Absent: %s" % filename)
        return False

    # TODO: revisit whether to include localizer or not,
    #  it may have relationship with other modalities
    # TODO: make the check more concrete. See dicom2nifti for details

    # check quality control subject :  Not present dicom headers
    if not include_phantom:
        series_desc = get_tags_by_name(dicom, 'series_description').lower()
        if 'local' in series_desc:
            config.warn_once(logger, "Localizer: Skipping %s" % filename)
            return False

        if 'aahead' in series_desc:
            config.warn_once(logger, "AAhead_Scout: Skipping %s" % filename)
            return True

        if is_phantom(dicom):
            config.warn_once(logger, 'ACR/Phantom: %s' % filename)
            return False

    return True


def is_phantom(dicom: pydicom.FileDataset) -> bool:
    """
    Implements a heuristic to detect a phantom. Checks patient's name,
    sex and age, to discriminate a phantom from a real person. It is very
    unlikely that a patient's name is phantom, or age is 1 day.
    @param dicom: dicom object read from pydicom.read_file
    @return: boolean indicating if .dcm file belongs to a phantom
    """

    sid = str(get_tags_by_name(dicom, 'patient_name')).lower()
    sex = str(get_tags_by_name(dicom, 'patient_sex')).lower()
    age = str(get_tags_by_name(dicom, 'patient_age'))
    if 'phantom' in sid:
        return True
    if sex == 'o':
        return True
    if age == '001D':
        return True
    return False


def get_dicom_modality_tag(dicom: pydicom.FileDataset) -> str:
    property1 = get_tags_by_name(dicom, 'series_description')

    if property1 is None:
        property1 = get_tags_by_name(dicom, 'sequence_name')
    if property1 is None:
        property1 = get_tags_by_name(dicom, 'protocol_name')

    # TODO: need to decide on whether to use SERIES NUMBER as part of modality
    # identification
    # property2 = get_tags_by_name(dicom, 'SERIES_NUMBER')
    # ret_string = "_".join([str(property2), property1.lower()])
    return property1.replace(" ", "_")


def header_exists(dicom: pydicom.FileDataset) -> bool:
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
        logger.exception(e)
        return False


def parse_study_information(dicom):
    info = dict()
    info['echo_num'] = get_tags_by_name(dicom, 'echo_number')
    info['project'] = get_tags_by_name(dicom, 'study_id')
    info['modality'] = get_dicom_modality_tag(dicom)
    info['subject_name'] = get_tags_by_name(dicom, 'patient_name')
    info['session_name'] = get_tags_by_name(dicom, 'series_number')
    info['series_uid'] = get_tags_by_name(dicom, 'series_instance_uid')
    info['echo_time'] = get_tags_by_name(dicom, 'te')

    # dcm2niix detected 2 different series in a single folder
    # Even though Series Instance UID was same, there was
    # a difference in echo number, for gre_field_mapping
    info['run_name'] = info['series_uid'] + '_e' + str(info['echo_num'])
    return info


def parse_imaging_params(dicom_path: Union[str, Path]) -> dict:
    """
    Given a filepath to a .dcm file, the function reader DICOM metadata
    and extracts relevant parameter values for checking compliance.
    @param dicom_path:
    @return: dict
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

    for k in config.PARAMETER_TAGS.keys():
        value = get_param_value_by_name(dicom, k)
        # the value should be hashable
        # a dictionary will be used later to count the majority value
        if not utils.is_hashable(value):
            value = str(value)
        params[k] = value

    csa_values = csa_parser(dicom)
    params["slice_order"] = config.SODict[csa_values['so']]
    params['ipat'] = csa_values['ipat']
    params['shim'] = csa_values['shim']
    params['echo_train_length'] = get_param_value_by_name(dicom,
                                                          "echo_train_length")

    is3d = get_param_value_by_name(dicom, "mr_acquisition_type") == '3D'
    params["is3d"] = is3d
    params["effective_echo_spacing"] = effective_echo_spacing(dicom)
    params["phase_encoding_direction"] = get_phase_encoding(
                                dicom,
                                is3d=params['is3d'],
                                echo_train_length=params['echo_train_length'])
    return params


def get_param_value_by_name(dicom, name):
    data = dicom.get(config.PARAMETER_TAGS[name], None)
    if data:
        return data.value
    return None


def get_header(dicom, name):
    data = dicom.get(config.HEADER_TAGS[name], None)
    if data:
        return data.value
    return None


def get_tags_by_name(dicom, name):
    data = dicom.get(config.TAGS[name], None)
    if data is None:
        return None
    return data.value


def csa_parser(dicom):
    series_header = csareader.read(get_header(dicom, 'series_header_info'))
    items = utils.safe_get(series_header, 'tags.MrPhoenixProtocol.items')
    if items:
        text = items[0].split("\n")
    else:
        raise FileNotFoundError

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

    so = props.get("sKSpace.ucMultiSliceMode", None)
    ipat = props.get("sPat.lAccelFactPE", None)
    shim = props.get("sAdjData.uiAdjShimMode", None)
    return {
        'so': so,
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

    bwp_phase_encode = get_param_value_by_name(dicom, 'bwp_phase_encode')
    phase_encoding = get_param_value_by_name(dicom, 'phase_encoding_lines')

    if (bwp_phase_encode is None) or (phase_encoding is None):
        return None
    else:
        value = 1000 / (
            bwp_phase_encode * phase_encoding)

        # Match value to output of dcm2niix
        return value / 1000


def get_phase_encoding(dicom, is3d, echo_train_length, is_flipy=True):
    """
    https://github.com/rordenlab/dcm2niix/blob/23d087566a22edd4f50e4afe829143cb8f6e6720/console/nii_dicom_batch.cpp
    """
    # is_skip = False
    # if is3d:
    #     is_skip = True
    # if echo_train_length > 1:
    #     is_skip = False
    # image_header = csareader.read(get_header(dicom, 'image_header_info'))
    # phase_value = utils.safe_get(image_header,
    #                              'tags.PhaseEncodingDirectionPositive.items')
    # if phase_value:
    #     phpos = phase_value[0]
    # else:
    #     return None

    ped_dcm = get_param_value_by_name(dicom, "phase_encoding_direction")
    return ped_dcm
    # ped = ""
    # assert ped_dcm in ["COL", "ROW"]
    # if not is_skip and ped_dcm == "COL":
    #     ped = "j"
    # elif not is_skip and ped_dcm == "ROW":
    #     ped = "i"
    # if phpos >= 0 and not is_skip:
    #     if phpos == 0 and ped_dcm == 'ROW':
    #         ped += "-"
    #     elif ped_dcm == "COL" and phpos == 1 and is_flipy:
    #         ped += "-"
    #     elif ped_dcm == "COL" and phpos == 0 and not is_flipy:
    #         ped += "-"
    #     ped_dict = {
    #         'i': 'Left-Right',
    #         'i-': 'Right-Left',
    #         'j-': 'Anterior-Posterior',
    #         'j': 'Posterior-Anterior'
    #     }
    #     return ped_dict[ped]
    # else:
    #     return None
