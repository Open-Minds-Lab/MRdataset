#!/usr/bin/env python

"""Tests for `MRdataset` package."""

import shutil
import tempfile
from pathlib import Path

import hypothesis.strategies as st
import pytest
# from MRdataset.dicom_utils import get_csa_props
from hypothesis import given, settings

from MRdataset import import_dataset
from MRdataset.tests.simulate import make_compliant_test_dataset, make_multi_echo_dataset


@settings(max_examples=50, deadline=None)
@given(st.integers(min_value=1, max_value=10),
       st.floats(allow_nan=False,
                 allow_infinity=False),
       st.integers(min_value=-10000000, max_value=10000000),
       st.floats(allow_nan=False,
                 allow_infinity=False))
def test_parse_compliant_dataset(num_subjects,
                                 repetition_time,
                                 echo_train_length,
                                 flip_angle):
    fake_ds_dir = make_compliant_test_dataset(num_subjects,
                                              repetition_time,
                                              echo_train_length,
                                              flip_angle)
    mrd = import_dataset(fake_ds_dir, config_path='./mri-config.json')
    seq_ids = mrd.get_sequence_ids()

    for seq_id in seq_ids:
        mrd_num_subjects = set()
        for subject, session, run, seq in mrd.traverse_horizontal(seq_id):
            mrd_num_subjects.add(subject)
            assert seq['RepetitionTime'].get_value() == repetition_time
            assert seq['EchoTrainLength'].get_value() == echo_train_length
            assert seq['FlipAngle'].get_value() == flip_angle
        assert set(mrd.get_subject_ids(seq_id)) == mrd_num_subjects
    shutil.rmtree(fake_ds_dir)
    return

@settings(max_examples=50, deadline=None)
@given(st.integers(min_value=4, max_value=10),
       st.floats(allow_nan=False,
                 allow_infinity=False),
       st.integers(min_value=-10000000, max_value=10000000),
       st.floats(allow_nan=False,
                 allow_infinity=False))
def test_parse_dataset_no_echo_numbers(num_subjects,
                                 repetition_time,
                                 echo_train_length,
                                 flip_angle):
    fake_ds_dir = make_multi_echo_dataset(num_subjects,
                                              repetition_time,
                                              echo_train_length,
                                              flip_angle)
    mrd = import_dataset(fake_ds_dir, config_path='./mri-config-2.json')
    seq_ids = mrd.get_sequence_ids()

    for seq_id in seq_ids:
        mrd_num_subjects = set()
        for subject, session, run, seq in mrd.traverse_horizontal(seq_id):
            mrd_num_subjects.add(subject)
            assert seq['RepetitionTime'].get_value() == repetition_time
            assert seq['EchoTrainLength'].get_value() == echo_train_length
            assert seq['FlipAngle'].get_value() == flip_angle
        assert set(mrd.get_subject_ids(seq_id)) == mrd_num_subjects
    shutil.rmtree(fake_ds_dir)
    return


def test_config_dict():
    fake_ds_dir = make_compliant_test_dataset(1, 1, 1, 1)
    with pytest.raises(FileNotFoundError):
        mrd = import_dataset(fake_ds_dir, config_path='non-existent.json')

def test_empty_folders():
    with tempfile.TemporaryDirectory() as tmpdirname:
        folder_path = Path(tmpdirname)
        subfolder = folder_path / "subfolder"
        subfolder.mkdir(parents=True, exist_ok=True)
        filepath = subfolder / "test.dcm"
        filepath.touch()

        mrd = import_dataset(folder_path, config_path='./mri-config.json')
        assert len(mrd.get_sequence_ids()) == 0

# def get_csa_props_test():
#     "CSA header looks funny in Pitt 7T (20221130)"
#     text = "blah = 0x1\nxy\nsAdjData.uiAdjShimMode                = 0x1\na = b"
#     shim_code = get_csa_props("sAdjData.uiAdjShimMode", text)
#     assert shim_code == '0x1'

