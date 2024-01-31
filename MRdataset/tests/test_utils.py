import json
import os
import re
import tempfile
from pathlib import Path

import pytest
from hypothesis import given, strategies as st, settings
from hypothesis.strategies import characters
from pydicom import dcmread

from MRdataset.dicom_utils import is_dicom_file, is_valid_inclusion
from MRdataset.utils import convert2ascii, read_json, \
    is_folder_with_no_subfolders, find_terminal_folders, \
    check_mrds_extension, valid_dirs, \
    folders_with_min_files  # Import your function from the correct module


def test_valid_dicom_file(tmp_path=None):
    if tmp_path is None:
        tmp_path = tempfile.gettempdir()
    # Create a temporary DICOM file
    dicom_file = Path(tmp_path) / "valid_dicom.dcm"
    with open(dicom_file, 'wb') as file_stream:
        file_stream.write(b'\x00' * 128)  # Fill with zeros to simulate a DICOM header
        file_stream.write(b'DICM')  # Add DICM marker

    assert is_dicom_file(str(dicom_file)) is True


def test_invalid_dicom_file(tmp_path=None):
    if tmp_path is None:
        tmp_path = tempfile.gettempdir()
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

    dcm.SeriesDescription = None
    assert not is_valid_inclusion(dcm, include_phantom=False)

    dcm.ImageType = None
    assert not is_valid_inclusion(dcm, include_phantom=False)

    dcm.SeriesDescription = 'localizer'
    assert not is_valid_inclusion(dcm, include_phantom=False)

    dcm.SeriesDescription = 'aahead_scout'
    assert not is_valid_inclusion(dcm, include_phantom=False)
    dcm.SeriesDescription = 'fmap_sbref'
    assert not is_valid_inclusion(dcm, include_sbref=False)
    assert not is_valid_inclusion(dcm, include_sbref=True)

    dcm.SeriesDescription = 'siemens_mosaic'
    dcm.ImageType = ['ORIGINAL', 'PRIMARY', 'M', 'ND', 'MOCO']
    assert not is_valid_inclusion(dcm, include_moco=False)
    dcm.ImageType = ['ORIGINAL', 'PRIMARY', 'M', 'ND', 'DERIVED']
    assert not is_valid_inclusion(dcm, include_derived=False)

    dcm.SeriesDescription = 't1w'
    dcm.PatientID = 'phantom'
    assert not is_valid_inclusion(dcm, include_phantom=False)
    dcm.PatientID = 'sub-001'
    dcm.PatientSex = 'o'
    assert not is_valid_inclusion(dcm, include_phantom=False)
    dcm.PatientID = 'sub-001'
    dcm.PatientSex = 'F'
    dcm.PatientAge = '001D'
    assert not is_valid_inclusion(dcm, include_phantom=False)

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


@given(st.integers())
def test_read_invalid_file_raises_error(filename):
    with pytest.raises(TypeError):
        read_json(filename)


@given(st.integers())
def test_invalid_mrds_ext_raises_error(filename):
    with pytest.raises(TypeError):
        check_mrds_extension(filename)


# Test when folder has subfolders
def test_has_subfolders():
    with tempfile.TemporaryDirectory() as tmpdirname:
        folder_path = Path(tmpdirname)
        subfolder = folder_path / "subfolder"
        subfolder.mkdir(parents=True, exist_ok=True)

        has_no_subfolders, subfolders = is_folder_with_no_subfolders(folder_path)
        assert has_no_subfolders is False
        assert subfolder in subfolders

# Test when folder has no subfolders
def test_no_subfolders():
    with tempfile.TemporaryDirectory() as tmpdirname:
        folder_path = Path(tmpdirname)

        has_no_subfolders, subfolders = is_folder_with_no_subfolders(folder_path)
        assert has_no_subfolders is True
        assert subfolders == []

# Test when folder doesn't exist
def test_nonexistent_folder():
    folder_path = Path("nonexistent_folder")

    with pytest.raises(FileNotFoundError):
        is_folder_with_no_subfolders(folder_path)


@pytest.fixture
def tmpdir():
    return '/tmp'


# Test find_terminal_folders with terminal folders
def test_find_terminal_folders_with_terminals():
    with tempfile.TemporaryDirectory() as tmpdirname:
        root = Path(tmpdirname)
        folder1 = root / "folder1"
        folder1.mkdir()
        folder2 = folder1 / "folder2"
        folder2.mkdir()

        terminal_folders = find_terminal_folders(root)
        assert terminal_folders == [folder2]

        folder3 = folder2 / "folder3"
        folder3.mkdir()

        terminal_folders = find_terminal_folders(root)
        assert terminal_folders == [folder3]


# Test find_terminal_folders with single folder
def test_find_terminal_folders_single_folder():
    with tempfile.TemporaryDirectory() as tmpdirname:
        root = Path(tmpdirname)
        folder = root / "folder"
        folder.mkdir()

        terminal_folders = find_terminal_folders(root)
        assert terminal_folders == [folder]


# Test find_terminal_folders with non-existent folder
def test_find_terminal_folders_nonexistent_folder():
    with tempfile.TemporaryDirectory() as tmpdirname:
        root = Path(tmpdirname) / "nonexistent_folder"

        terminal_folders = find_terminal_folders(root)
        assert terminal_folders == []

def test_folder_with_min_files_nonexistent_folder():
    with tempfile.TemporaryDirectory() as tmpdirname:
        root = Path(tmpdirname) / "nonexistent_folder"
        with pytest.raises(ValueError):
            a = list(folders_with_min_files(root, pattern="*.dcm", min_count=1))
        with pytest.raises(ValueError):
            a = list(folders_with_min_files([], pattern="*.dcm", min_count=0))


# Test find_terminal_folders with files
def test_find_terminal_folders_with_files():
    with tempfile.TemporaryDirectory() as tmpdirname:
        root = Path(tmpdirname)
        file = root / "file.txt"
        file.touch()

        terminal_folders = find_terminal_folders(root)
        assert terminal_folders == [root]


# Test find_terminal_folders with nested terminal folders
def test_find_terminal_folders_nested_terminals():
    with tempfile.TemporaryDirectory() as tmpdirname:
        root = Path(tmpdirname)
        folder1 = root / "folder1"
        folder1.mkdir()
        folder2 = folder1 / "folder2"
        folder2.mkdir()
        folder3 = folder2 / "folder3"
        folder3.mkdir()

        terminal_folders = find_terminal_folders(folder1)
        assert terminal_folders == [folder3]


# Test find_terminal_folders with multiple terminal folders
def test_find_terminal_folders_multiple_terminals():
    with tempfile.TemporaryDirectory() as tmpdirname:
        root = Path(tmpdirname)
        folder1 = root / "folder1"
        folder1.mkdir()
        folder2 = root / "folder2"
        folder2.mkdir()
        folder3 = root / "folder3"
        folder3.mkdir()

        terminal_folders = find_terminal_folders(root)
        assert set(terminal_folders) == {folder1, folder2, folder3}


def test_find_folders_with_min_files():
    with tempfile.TemporaryDirectory() as tmpdirname:
        root = Path(tmpdirname).resolve()
        thresh = 3
        expected = set()
        for idx, num_files in zip(range(5), [2, 3, 3, 5, 1]):
            folder = root / f"folder{idx}"
            folder.mkdir()
            for count in range(num_files):
                file = folder / f"file{count}.dcm"
                file.touch()

            if num_files >= thresh:
                expected.add(folder.resolve())

        terminal_folders = folders_with_min_files(root, "*.dcm", min_count=thresh)
        assert set(terminal_folders) == expected


# Define a strategy for generating valid paths (strings)
@st.composite
def valid_paths(draw):
    def _my_filter(path):
        # Filter out empty strings
        p = convert2ascii(path)
        return len(p) > 0

    text = draw(st.text(alphabet=characters(
        min_codepoint=1,
        max_codepoint=1000,
        categories=['Lu', 'Ll']).map(lambda s: s.strip()),
                        min_size=1, max_size=100).filter(_my_filter))
    return convert2ascii(text)


@settings(max_examples=50, deadline=None)
# Property-based test: the output should be a list of valid paths
@given(valid_paths())
def test_valid_dirs_with_single_path_returns_list(path):
    os.makedirs(path, exist_ok=True)
    result = valid_dirs(path)
    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], Path)

    for i in result:
        os.rmdir(i)


@settings(max_examples=50, deadline=None)
@given(valid_paths())
def test_valid_dirs_with_single_path_returns_list(path):
    with pytest.raises(OSError):
        result = valid_dirs(path)


@settings(max_examples=50, deadline=None)
@given(st.lists(valid_paths(), min_size=1, max_size=10))
def test_valid_dirs_with_list_of_paths_returns_list(paths):
    with tempfile.TemporaryDirectory() as tmpdirname:
        paths = [Path(tmpdirname) / path for path in paths]
        for p in paths:
            p.mkdir(exist_ok=True, parents=True)

        result = valid_dirs(paths)
        assert isinstance(result, list)
        assert all(isinstance(item, Path) for item in result)


@settings(max_examples=50, deadline=None)
@given(st.lists(valid_paths(), min_size=1, max_size=10))
def test_invalid_dirs(paths):
    with tempfile.TemporaryDirectory() as tmpdirname:
        paths = [Path(tmpdirname) / path for path in paths]

        with pytest.raises(OSError):
            result = valid_dirs(paths)


# Property-based test: calling with None should raise a ValueError
def test_valid_dirs_with_none_raises_error():
    with pytest.raises(ValueError):
        valid_dirs(None)


# Property-based test: calling with invalid input should raise an OSError
@given(st.integers() | st.floats() | st.booleans())
def test_valid_dirs_with_invalid_input_raises_error(invalid_input):
    with pytest.raises(ValueError):
        valid_dirs(invalid_input)
