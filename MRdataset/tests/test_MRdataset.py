#!/usr/bin/env python

"""Tests for `MRdataset` package."""

import shutil

import hypothesis.strategies as st
from hypothesis import given, settings, assume

from MRdataset import import_dataset
from MRdataset.simulate import make_compliant_test_dataset, \
    make_non_compliant_test_dataset


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


@settings(max_examples=100, deadline=5000)
@given(st.integers(min_value=1, max_value=10),
       st.integers(min_value=0, max_value=10),
       st.tuples(
           st.floats(allow_nan=False, allow_infinity=False),
           st.floats(allow_nan=False, allow_infinity=False)),
       st.tuples(
           st.integers(min_value=-10000000, max_value=10000000),
           st.integers(min_value=-10000000, max_value=10000000)),
       st.tuples(
           st.floats(allow_nan=False, allow_infinity=False),
           st.floats(allow_nan=False, allow_infinity=False)))
def test_parse_non_compliant_dataset(num_subjects,
                                     num_compliant_subjects,
                                     repetition_times,
                                     echo_train_lengths,
                                     flip_angles):
    assume(num_compliant_subjects <= num_subjects)

    print(num_subjects,
          num_compliant_subjects,
          repetition_times,
          echo_train_lengths,
          flip_angles)
    fake_ds_dir = make_non_compliant_test_dataset(num_subjects,
                                                  num_compliant_subjects,
                                                  repetition_times,
                                                  echo_train_lengths,
                                                  flip_angles)
    mrd = import_dataset(fake_ds_dir, include_phantom=True)
    mrd_num_subjects = set()
    for modality in mrd.modalities:
        for subject in modality.subjects:
            mrd_num_subjects.add(subject.name)
            for session in subject.sessions:
                for run in session.runs:
                    assert run.params['tr'] in repetition_times
                    assert run.params['echo_train_length'] in echo_train_lengths
                    assert run.params['flip_angle'] in flip_angles
    assert len(mrd_num_subjects) == num_subjects
    shutil.rmtree(fake_ds_dir)
    return


if __name__ == '__main__':
    test_parse_non_compliant_dataset(3, 1, (0.0, 0.0), (0, 0), (0.0, 0.0))
