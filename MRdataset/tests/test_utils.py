import json
import re
from pathlib import Path

import pytest
from hypothesis import given, strategies as st
from pydicom import dcmread

from MRdataset.dicom_utils import is_dicom_file, is_valid_inclusion
from MRdataset.utils import convert2ascii, read_json  # Import your function from the correct module


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


# Define a strategy for generating strings
@st.composite
def strings(draw):
    return draw(st.text())


# Define a strategy for generating ASCII strings
@st.composite
def ascii_strings(draw):
    return draw(st.text(alphabet=st.characters(whitelist_categories=('L', 'N', 'P', 'Z', 'S'))))


# Define a strategy for generating booleans
@st.composite
def booleans(draw):
    return draw(st.booleans())


# Property-based test: the output should contain only ASCII characters
@given(strings())
def test_contains_only_ascii(value):
    result = convert2ascii(value, allow_unicode=False)
    assert all(ord(char) < 128 for char in result)


# Property-based test: the output should not contain spaces or dashes at the beginning or end
@given(ascii_strings(), booleans())
def test_no_spaces_or_dashes_at_ends(value, allow_unicode):
    result = convert2ascii(value, allow_unicode)
    assert not result.startswith((' ', '-'))
    assert not result.endswith((' ', '-'))


# Property-based test: the output should not contain consecutive spaces or dashes
@given(ascii_strings(), booleans())
def test_no_consecutive_spaces_or_dashes(value, allow_unicode):
    result = convert2ascii(value, allow_unicode)
    assert '  ' not in result
    assert '--' not in result


# Property-based test: the output should not contain any special characters
@given(ascii_strings())
def test_no_special_characters(value):
    result = convert2ascii(value, allow_unicode=False)
    assert re.match(r'^[a-zA-Z0-9_-]*$', result)


# Property-based test: converting twice should be the same as converting once
@given(ascii_strings(), booleans())
def test_double_conversion_is_same(value, allow_unicode):
    result1 = convert2ascii(value, allow_unicode)
    result2 = convert2ascii(result1, allow_unicode)
    assert result1 == result2


# Define a strategy for generating valid JSON strings
@st.composite
def json_strings(draw):
    data = draw(st.dictionaries(st.text(), st.text()))
    return json.dumps(data)


# Property-based test: reading a JSON file should return a dictionary
@given(json_strings())
def test_read_json_returns_dict(json_string):
    json_file = Path("test.json")
    json_file.write_text(json_string)
    try:
        result = read_json(json_file)
        assert isinstance(result, dict)
    finally:
        json_file.unlink()

# Property-based test: reading a non-existent file should raise a FileNotFoundError
@given(st.text())
def test_read_non_existent_file_raises_error(filename):
    non_existent_file = Path(filename)
    with pytest.raises(FileNotFoundError):
        read_json(non_existent_file)
