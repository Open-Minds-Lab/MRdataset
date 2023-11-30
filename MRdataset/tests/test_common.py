"""Tests for functions in common.py"""
import os
import pickle
import shutil
from pathlib import Path

# use hypothesis to generate multiple test cases
import hypothesis.strategies as st
import pytest
from hypothesis import given, settings, HealthCheck

from MRdataset import import_dataset, save_mr_dataset, load_mr_dataset, \
    BaseDataset
from MRdataset.common import find_dataset_using_ds_format
from MRdataset.config import MRException, MRdatasetWarning, \
    DatasetEmptyException
from MRdataset.dicom import DicomDataset
from MRdataset.tests.simulate import make_compliant_test_dataset

THIS_DIR = Path(__file__).parent.resolve()


@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=50, deadline=None)
@given(st.integers(min_value=1, max_value=10),
       st.floats(allow_nan=False,
                 allow_infinity=False),
       st.integers(min_value=-10000000, max_value=10000000),
       st.floats(allow_nan=False,
                 allow_infinity=False))
def test_save_load_mr_dataset(num_subjects,
                              repetition_time,
                              echo_train_length,
                              flip_angle):
    """Test save_mr_dataset"""
    fake_ds_dir = make_compliant_test_dataset(num_subjects, repetition_time, echo_train_length, flip_angle)
    mrd = import_dataset(fake_ds_dir, config_path=THIS_DIR / 'resources/mri-config.json',
                         output_dir=fake_ds_dir, name='test_dataset')
    save_mr_dataset(filepath='test.mrds.pkl', mrds_obj=mrd)
    mrd2 = load_mr_dataset('test.mrds.pkl')
    assert mrd == mrd2
    os.remove('test.mrds.pkl')
    shutil.rmtree(fake_ds_dir)
    return


@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=50, deadline=None)
@given(st.text(min_size=1, max_size=10))
def test_find_dataset_using_ds_format(ds_format):
    """Test find_dataset_using_ds_format"""
    assert find_dataset_using_ds_format('dicom') == DicomDataset
    # assert find_dataset_using_ds_format('bids') == BidsDataset
    # check that any other dataset style raises an error

    if ds_format not in ['dicom', 'bids']:
        with pytest.raises(NotImplementedError):
            find_dataset_using_ds_format(ds_format)
    return


def test_import_dataset(capfd):
    """Test import_dataset"""
    fake_ds_dir = make_compliant_test_dataset(1, 1, 1, 1)
    mrd = import_dataset(fake_ds_dir,
                         verbose=True,
                         config_path=THIS_DIR / 'resources/mri-config.json',
                         output_dir=fake_ds_dir)
    assert mrd.name != 'test_dataset'
    out, err = capfd.readouterr()
    assert out == str(mrd) + '\n'

    mrd = import_dataset(fake_ds_dir,
                         verbose=False,
                         name='test_dataset',
                         config_path=THIS_DIR / 'resources/mri-config.json',
                         output_dir=fake_ds_dir)
    # assert logger.level == 30
    assert mrd.name == 'test_dataset'

    with pytest.raises(ValueError):
        mrd = import_dataset(None,
                             verbose=False,
                             config_path=THIS_DIR / 'resources/mri-config.json',
                             output_dir=fake_ds_dir, name='test_dataset')
    assert isinstance(mrd, BaseDataset)
    shutil.rmtree(fake_ds_dir)
    return


def test_save_mr_dataset():
    """Test save_mr_dataset on a non-writable directory"""
    fake_ds_dir = make_compliant_test_dataset(1, 1, 1, 1)
    mrd = import_dataset(fake_ds_dir, config_path=THIS_DIR / 'resources/mri-config.json',
                         output_dir=fake_ds_dir, name='test_dataset')
    with pytest.raises(OSError):
        save_mr_dataset(filepath='/sys/mycomputer/test.mrds.pkl', mrds_obj=mrd)
    shutil.rmtree(fake_ds_dir)
    return


def test_load_mr_dataset():
    """Test load_mr_dataset on a non-existent file"""
    with pytest.raises(FileNotFoundError):
        load_mr_dataset('non-existent-file.mrds.pkl')

    fake_ds = "invalid dataset object"
    # dump using pickle
    with open('test.mrds.pkl', 'wb') as f:
        pickle.dump(fake_ds, f)

    with pytest.raises(TypeError):
        loaded_ds = load_mr_dataset(Path('test.mrds.pkl'))

    # unlink the file
    os.remove('test.mrds.pkl')
    return


# Test MRException
def test_mrexception():
    with pytest.raises(MRException) as exc_info:
        raise MRException("Test MRException")
    assert str(exc_info.value) == "Test MRException"


# Test MRdatasetWarning
def test_mrdatasetwarning():
    with pytest.raises(MRdatasetWarning) as exc_info:
        raise MRdatasetWarning("Test MRdatasetWarning")
    assert str(exc_info.value) == "Test MRdatasetWarning"


# Test DatasetEmptyException
def test_datasetemptyexception():
    with pytest.raises(DatasetEmptyException) as exc_info:
        raise DatasetEmptyException()
    assert str(exc_info.value) == "Expected Sidecar DICOM/JSON files in --data_source. Got 0 DICOM/JSON files."
