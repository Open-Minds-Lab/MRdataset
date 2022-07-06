from pathlib import Path

import pydicom
from MRdataset.utils import config
from nibabel.nicom import csareader
from pydicom.multival import MultiValue
import logging

def get_project(dicom):
    return get_dicom_property(dicom, 'STUDY')


def get_session(dicom):
    return get_dicom_property(dicom, 'SESSION')


def get_echo_number(dicom):
    return get_dicom_property(dicom, 'ECHO_NUMBER')


def get_instance_number(dicom):
    return get_dicom_property(dicom, 'INSTANCE_NUMBER')


def get_series(dicom):
    a = get_dicom_property(dicom, 'SERIES_DESCRIPTION')

    if a is None:
        a = get_dicom_property(dicom, 'SEQUENCE_NAME')
    if a is None:
        a = get_dicom_property(dicom, 'PROTOCOL_NAME')

    # TODO need to decide on wether to use SERIES NUMBER as part of modality identification
    b = get_dicom_property(dicom, 'SERIES_NUMBER')
    ret_string = "_".join([str(b), a.lower()])
    return ret_string.replace(" ", "_")
    # return a.lower().replace(" ", "_")


def get_image_type(dicom):
    return get_dicom_property(dicom, 'IMAGE_TYPE')


def get_modality(dicom):
    mode = []
    sequence = get_dicom_property(dicom, 'SEQUENCE')
    variant = get_dicom_property(dicom, 'VARIANT')

    # If str, append to list
    # If "pydicom.multival.MultiValue", convert expression to list, append to list
    if isinstance(sequence, str):
        mode.append(sequence)
    elif isinstance(sequence, MultiValue):
        mode.append(list(sequence))
    else:
        logging.warning("Error reading <sequence>. Do you think its a phantom?")
    if isinstance(variant, str):
        mode.append(variant)
    elif isinstance(variant, MultiValue):
        mode.append(list(variant))
    else:
        logging.warning("Error reading <variant>. Do you think its a phantom?")

    return functional.flatten(mode)


def get_subject(dicom):
    return str(get_dicom_property(dicom, 'SUBJECT'))


def header_exists(dicom):
    try:
        series = dicom.get(config.SERIES_HEADER_INFO).value
        image = dicom.get(config.IMAGE_HEADER_INFO).value
        series_header = csareader.read(series)

        # just try reading these values, to bypass any errors, don't need these values now
        # image_header = \
        csareader.read(image)
        # items = \
        series_header['tags']['MrPhoenixProtocol']['items'][0].split('\n')
        return True
    except Exception as e:
        logging.exception(e)
        return False


def parse(dicom_path):
    filepath = Path(dicom_path)
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

    subj = SubjectNode(filepath)
    for k in config.PARAMETER_TAGS.keys():
        value = get_param_value_by_name(dicom, k)
        # the value should be hashable
        # a dictionary will be used later to count the majority value
        if not functional.is_hashable(value):
            value = str(value)
        subj.params[k] = value

    csa_values = csa_parser(dicom)
    subj.params["slice_order"] = config.SODict[csa_values['so']]
    subj.params['ipat'] = csa_values['ipat']
    subj.params['shim'] = csa_values['shim']

    subj.params["is3d"] = get_param_value_by_name(dicom, "mr_acquisition_type") == '3D'
    subj.params["modality"] = "_".join([
        str(get_header(dicom, "series_number")),
        get_header(dicom, "series_description")]).replace(" ", "_")
    subj.params["effective_echo_spacing"] = effective_echo_spacing(dicom)
    subj.params["phase_encoding_direction"] = get_phase_encoding(dicom,
                                                                 is3d=subj.params['is3d'],
                                                                 echo_train_length=subj.params['echo_train_length'])
    return subj


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


def csa_parser(dicom):
    series_header = csareader.read(get_header(dicom, 'series_header_info'))
    items = functional.safe_get(series_header, 'tags.MrPhoenixProtocol.items')
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
    #     check = (self.get("echo_train_length") == self.get("phase_encoding_lines"))
    #     if not check:
    #         print("PhaseEncodingLines is not equal to EchoTrainLength : {0}".format(self.filepath))
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
    is_skip = False
    if is3d:
        is_skip = True
    if echo_train_length > 1:
        is_skip = False
    image_header = get_header(dicom, 'image_header_info')
    phvalue = functional.safe_get(image_header, 'tags.PhaseEncodingDirectionPositive.items')
    if phvalue:
        phpos = phvalue[0]
    else:
        return None

    ped_dcm = get_param_value_by_name(dicom, "phase_encoding_direction")

    ped = ""
    assert ped_dcm in ["COL", "ROW"]
    if not is_skip and ped_dcm == "COL":
        ped = "j"
    elif not is_skip and ped_dcm == "ROW":
        ped = "i"
    if phpos >= 0 and not is_skip:
        if phpos == 0 and ped_dcm == 'ROW':
            ped += "-"
        elif ped_dcm == "COL" and phpos == 1 and is_flipy:
            ped += "-"
        elif ped_dcm == "COL" and phpos == 0 and not is_flipy:
            ped += "-"
        ped_dict = {
            'i': 'Left-Right',
            'i-': 'Right-Left',
            'j-': 'Anterior-Posterior',
            'j': 'Posterior-Anterior'
        }
        return ped_dict[ped]
    else:
        return None
