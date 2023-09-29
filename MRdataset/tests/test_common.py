"""Tests for functions in common.py"""
import os
import shutil

# use hypothesis to generate multiple test cases
import hypothesis.strategies as st
import pytest
from hypothesis import given, settings

from MRdataset import import_dataset, save_mr_dataset, load_mr_dataset
from MRdataset.bids import BidsDataset
from MRdataset.common import find_dataset_using_ds_format
from MRdataset.dicom import DicomDataset
from MRdataset.tests.simulate import make_compliant_test_dataset


@settings(max_examples=50, deadline=None)
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
    mrd = import_dataset(fake_ds_dir, config_path='./mri-config.json')
    save_mr_dataset(filepath='test.mrds.pkl', mrds_obj=mrd)
    mrd2 = load_mr_dataset('test.mrds.pkl')
    assert mrd == mrd2
    os.remove('test.mrds.pkl')
    shutil.rmtree(fake_ds_dir)
    return


@settings(max_examples=50, deadline=None)
@given(st.text(min_size=1, max_size=10))
def test_find_dataset_using_ds_format(ds_format):
    """Test find_dataset_using_ds_format"""
    assert find_dataset_using_ds_format('dicom') == DicomDataset
    assert find_dataset_using_ds_format('bids') == BidsDataset
    # check that any other dataset style raises an error

    if ds_format not in ['dicom', 'bids']:
        with pytest.raises(NotImplementedError):
            find_dataset_using_ds_format(ds_format)
    return
