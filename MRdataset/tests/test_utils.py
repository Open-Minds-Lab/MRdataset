from MRdataset.dicom_utils import is_dicom_file, is_valid_inclusion
from pathlib import Path


def test_valid_dicom_file(tmp_path='/tmp'):
    # Create a temporary DICOM file
    dicom_file = Path(tmp_path) / "valid_dicom.dcm"
    with open(dicom_file, 'wb') as file_stream:
        file_stream.write(b'\x00' * 128)  # Fill with zeros to simulate a DICOM header
        file_stream.write(b'DICM')  # Add DICM marker

    assert is_dicom_file(str(dicom_file)) is True


def test_invalid_dicom_file(tmp_path='/tmp'):
    # Create a temporary file that is not a DICOM file
    non_dicom_file = Path(tmp_path) / "non_dicom.txt"
    with open(non_dicom_file, 'w') as file_stream:
        file_stream.write("This is not a DICOM file")

    assert is_dicom_file(str(non_dicom_file)) is False


def test_nonexistent_file():
    # Test a file that does not exist
    nonexistent_file = "nonexistent_file.dcm"
    assert is_dicom_file(nonexistent_file) is False


def test_valid_inclusion(sample_dicom_object):
    filepath = "/path/to/dicom_file.dcm"  # Replace with the actual path
    result = is_valid_inclusion(filepath, sample_dicom_object)
    assert result is True


def test_invalid_inclusion_localizer(sample_dicom_object):
    result = is_valid_inclusion(sample_dicom_object)
    assert result is False

def test_invalid_inclusion_aahead(sample_dicom_object):
    filepath = "/path/to/aahead_dicom_file.dcm"  # Replace with the actual path
    result = is_valid_inclusion(filepath, sample_dicom_object)
    assert result is False

def test_invalid_inclusion_phantom(sample_dicom_object):
    filepath = "/path/to/phantom_dicom_file.dcm"  # Replace with the actual path
    result = is_valid_inclusion(filepath, sample_dicom_object)
    assert result is False

def test_missing_series_description(sample_dicom_object):
    filepath = "/path/to/dicom_file.dcm"  # Replace with the actual path
    sample_dicom_object.SeriesDescription = None
    result = is_valid_inclusion(filepath, sample_dicom_object)
    assert result is True  # No SeriesDescription, should not affect inclusion

def test_non_dicom_object():
    with pytest.raises(AttributeError):
        is_valid_inclusion("/path/to/non_dicom_file.txt", "not_a_dicom_object")

if __name__ == "__main__":
    pytest.main([__file__])
