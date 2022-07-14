import logging
from functools import lru_cache

# Constant Dicom Identifiers Used for dataset creation and manipulation
TAGS = {
    "series_instance_uid": (0x20, 0x0e),
    "sequence": (0x18, 0x20),
    "variant": (0x18, 0x21),
    "patient_name": (0x10, 0x10),
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
CACHE_DIR = ".mrdataset"

# Constant Dicom Identifiers used for protocol compliance.
# These are the parameters
# which are compared in the final report
PARAMETER_TAGS = {
    "manufacturer": [0x08, 0x70],
    "organ": [0x18, 0x15],
    "te": [0x18, 0x81],
    "tr": [0x18, 0x80],
    "b0": [0x18, 0x87],
    "flip_angle": [0x18, 0x1314],
    "bwpx": [0x18, 0x95],
    "echo_train_length": [0x18, 0x0091],
    "scanning_sequence": [0x18, 0x20],
    "sequence_variant": [0x18, 0x21],
    "mr_acquisition_type": [0x18, 0x23],
    "phase_encoding_lines": [0x18, 0x89],
    "bwp_phase_encode": [0x19, 0x1028],
    "phase_encoding_direction": [0x18, 0x1312],

}
PARAMETER_NAMES = [
    'Manufacturer',
    'BodyPartExamined',
    'EchoTime',
    'RepetitionTime',
    'MagneticFieldStrength',
    'FlipAngle',
    'InPlanePhaseEncodingDirection',
    'EchoTrainLength',
    'PixelBandwidth',
    'ScanningSequence',
    'SequenceVariant',
    'MRAcquisitionType',
    'NumberOfPhaseEncodingSteps',
]
# Check  QualityControlSubject

# Constant dicom Identifiers used to extract dicom headers
HEADER_TAGS = {
    "image_header_info": [0x29, 0x1010],
    "series_header_info": [0x29, 0x1020],
}
SODict = {
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
ATDict = ["2D", "3D"]


# Suppress duplicated warnings
@lru_cache(1)
def warn_once(logger: logging.Logger, msg: str):
    logger.warning(msg)


def setup_logger(name, filename):
    format_string = '%(asctime)s - %(levelname)s - %(module)s - %(message)s'
    formatter = logging.Formatter(fmt=format_string)
    handler = logging.FileHandler(filename)
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    return logger





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


