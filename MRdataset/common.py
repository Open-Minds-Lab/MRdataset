from MRdataset.utils import config
from nibabel.nicom import csareader
from pydicom.multival import MultiValue
import logging


def get_dicom_property(dicom, attribute):
    element = dicom.get(getattr(config, attribute), None)
    if not element:
        return None
    return element.value


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
