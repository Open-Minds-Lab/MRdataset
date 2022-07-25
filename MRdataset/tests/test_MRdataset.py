#!/usr/bin/env python

"""Tests for `MRdataset` package."""

import shutil

import hypothesis.strategies as st
from MRdataset import import_dataset
from MRdataset.simulate import make_compliant_test_dataset
from hypothesis import given, settings


@settings(max_examples=50, deadline=None)
@given(st.integers(min_value=0, max_value=10),
       st.floats(allow_nan=False,
                 allow_infinity=False),
       st.integers(min_value=-10000000, max_value=10000000),
       st.floats(allow_nan=False,
                 allow_infinity=False))
def test_parse_compliant_dataset(num_subjects,
                                 repetition_time,
                                 echo_train_length,
                                 flip_angle):
    print(num_subjects,
          repetition_time,
          echo_train_length,
          flip_angle)
    fake_ds_dir = make_compliant_test_dataset(num_subjects,
                                              repetition_time,
                                              echo_train_length,
                                              flip_angle)
    mrd = import_dataset(fake_ds_dir, include_phantom=True)
    mrd_num_subjects = set()
    for modality in mrd.modalities:
        for subject in modality.subjects:
            mrd_num_subjects.add(subject.name)
            for session in subject.sessions:
                for run in session.runs:
                    assert run.params['tr'] == repetition_time
                    assert run.params['echo_train_length'] == echo_train_length
                    assert run.params['flip_angle'] == flip_angle
    assert len(mrd_num_subjects) == num_subjects
    shutil.rmtree(fake_ds_dir)
    return
