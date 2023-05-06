import logging
from functools import lru_cache
from pathlib import Path

# Constant Dicom Identifiers Used for dataset creation and manipulation
TAGS = {
    "series_instance_uid": (0x20, 0x0e),
    "sequence": (0x18, 0x20),
    "variant": (0x18, 0x21),
    "patient_name": (0x10, 0x10),
    "patient_id": (0x10, 0x20),
    "study_id": (0x08, 0x1030),
    "series_description": (0x08, 0x103E),
    "series_number": (0x20, 0x11),
    "protocol_name": (0x18, 0x1030),
    "sequence_name": (0x18, 0x24),
    "image_type": (0x08, 0x08),
    "echo_number": (0x18, 0x86),
    "te": [0x18, 0x81],
    "patient_sex": [0x10, 0x40],
    "patient_age": [0x10, 0x1010],
}

# Constant Paths
CACHE_DIR_NAME = ".mrdataset"
CACHE_DIR = Path.home().resolve() / CACHE_DIR_NAME
CACHE_DIR.mkdir(exist_ok=True)

MRDS_EXT = '.mrds.pkl'
VALID_DATASET_STYLES = [
    'dicom',
    'bids',
    'fastbids',
]

VALID_BIDS_EXTENSIONS = ['.json', '.nii', '.nii.gz']

PARAMETER_NAMES = {
    # 'Manufacturer': [0x08, 0x70],
    'EchoNumbers': [0x18, 0x86],
    'BodyPartExamined': [0x18, 0x15],
    'EchoTime': [0x18, 0x81],
    'RepetitionTime': [0x18, 0x80],
    'MagneticFieldStrength': [0x18, 0x87],
    'FlipAngle': [0x18, 0x1314],
    'PhaseEncodingDirection': [0x18, 0x1312],
    'EchoTrainLength': [0x18, 0x0091],
    'PixelBandwidth': [0x18, 0x95],
    'ScanningSequence': [0x18, 0x20],
    'SequenceVariant': [0x18, 0x21],
    'MRAcquisitionType': [0x18, 0x23],
    'PhaseEncodingSteps': [0x18, 0x89],
    # 'Model': [0x08, 0x1090],
    # 'SoftwareVersions': [0x18, 0x1020],
    # 'InstitutionName': [0x08, 0x0080],
}

VALID_DATATYPES = [
    'anat',
    'beh',
    'dwi',
    'eeg',
    'fmap',
    'func',
    'ieeg',
    'meg',
    'micr',
    'perf',
    'pet'
]
# Check  QualityControlSubject

# Constant dicom Identifiers used to extract dicom headers
HEADER_TAGS = {
    "image_header_info": [0x29, 0x1010],
    "series_header_info": [0x29, 0x1020],
}
SLICE_MODE = {
    "1": "sequential",
    "2": "interleaved",
    "4": "singleshot"
}
SSDict = {
    "SE": "Spin Echo",
    "IR": "Inversion Recovery",
    "GR": "Gradient Recalled",
    "EP": "Echo Planar",
    "RM": "Research Mode"
}
SVDict = {
    "SK": "segmented k-space",
    "MTC": "magnetization transfer contrast",
    "SS": "steady state",
    "TRSS": "time reversed steady state",
    "SP": "spoiled",
    "MP": "MAG prepared",
    "OSP": "oversampling phase",
    "NONE": "no sequence variant"
}

PAT = {
    "1": 'Not Selected',
    "2": 'Grappa',
    "3": 'Sense'
}

SHIM = {
    "1": 'tune_up',
    "2": 'standard',
    "4": 'advanced'
}

ATDict = ["2D", "3D"]


# Suppress duplicated warnings
@lru_cache(1)
def warn_once(logger: logging.Logger, msg: str):
    logger.warning(msg)


class MRException(Exception):
    """
    Custom error that is raised when some critical properties are not found
    in dicom file
    """

    def __init__(self, message, **kwargs):
        super().__init__(message)


class MRdatasetWarning(Exception):
    """
    Custom error that is raised when some critical properties are not found
    in dicom file
    """

    def __init__(self, message, **kwargs):
        super().__init__(message)


#
# class EmptySubject(ComplianceException):
#     """"""
#     pass
#
#
# class NonCompliantSubject(ComplianceException):
#     """"""
#     pass

class DatasetEmptyException(MRException):
    def __init__(self):
        super().__init__('Expected Sidecar DICOM/JSON files in '
                         '--data_source. Got 0 DICOM/JSON files.')


class ChangingParamsInSeries(MRException):
    """Custom error that is raised when parameter values are different for
    different slices even though the SeriesInstanceUID is same."""

    def __init__(self, filepath):
        super().__init__("Expected all dicom slices to have same parameters. "
                         "Got changing parameters : {}".format(filepath))


class SlicesNotStacked(MRException):
    """Custom error that is raised when parameter values are different for
    different slices even though the SeriesInstanceUID is same."""

    def __init__(self, filepath, parameter_name):
        super().__init__(
            "Expected all dicom slices to have same {0}.".format(parameter_name,
                                                                 filepath))


class OrientationVaries(SlicesNotStacked):
    def __init__(self, filepath):
        super().__init__(filepath, "Orientation")


class AcquisitionNumberVaries(SlicesNotStacked):
    def __init__(self, filepath):
        super().__init__(filepath, "Acquisition Number")


class EchoTimeVaries(SlicesNotStacked):
    def __init__(self, filepath):
        super().__init__(filepath, "Echo Time")


class SliceDimensionVaries(SlicesNotStacked):
    def __init__(self, filepath):
        super().__init__(filepath, "Slice Dimension")


class StudyDateTimeVaries(SlicesNotStacked):
    def __init__(self, filepath):
        super().__init__(filepath, "Study Date/Time")


class PhaseVaries(SlicesNotStacked):
    def __init__(self, filepath):
        super().__init__(filepath, "Phase [Real/Imaginary]")


class CoilVaries(SlicesNotStacked):
    def __init__(self, filepath):
        super().__init__(filepath, "Coil")


class StudyIdVaries(SlicesNotStacked):
    def __init__(self, filepath):
        super().__init__(filepath, "Study ID/Description")


class MultipleProjectsInDataset(MRException):
    """
    Custom error that is raised when dcm files in directory have
    different study ids. Expected all dicom files belong to a single study
    id. Cross-Study is not supported.
    """

    def __init__(self, study_ids):
        super().__init__("Expected all dicom files to be in the same project"
                         "/study. Found study id(s): {}".format(study_ids))
