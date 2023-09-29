from pydicom import dcmread
import pytest
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


def test_valid_inclusion(valid_dicom_file):
    dcm = dcmread(valid_dicom_file)  # Replace with the actual path
    result = is_valid_inclusion(dcm)
    assert result is True


def test_invalid_inclusion_derived(derived_dicom_file):
    dcm = dcmread(derived_dicom_file)  # Replace with the actual path
    result = is_valid_inclusion(dcm)
    assert result is False


def test_invalid_inclusion(invalid_dicom_file):
    dcm = dcmread(invalid_dicom_file)  # Replace with the actual path
    result = is_valid_inclusion(dcm)
    assert result is False


if __name__ == "__main__":
    pytest.main([__file__])
