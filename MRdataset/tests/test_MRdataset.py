#!/usr/bin/env python

"""Tests for `MRdataset` package."""

import shutil

import hypothesis.strategies as st
from hypothesis import given

from MRdataset import create_dataset
from MRdataset.simulate import get_test_dataset


@given(st.integers(min_value=0, max_value=10),
       st.floats(allow_nan=False,
                 allow_infinity=False),
       st.floats(allow_nan=False,
                 allow_infinity=False),
       st.floats(allow_nan=False,
                 allow_infinity=False),
       st.sampled_from(['ROW', 'COL']))
def test_parse_dataset(num_subjects,
                       repetition_time,
                       echo_time,
                       flip_angle,
                       phase_enc_direction):
    fake_ds_dir = get_test_dataset(num_subjects,
                                   repetition_time,
                                   echo_time,
                                   flip_angle,
                                   phase_enc_direction)
    mrd = create_dataset(fake_ds_dir, include_phantom=True)
    mrd_num_subjects = set()
    for modality in mrd.modalities:
        for subject in modality.subjects:
            mrd_num_subjects.add(subject.name)
            for session in subject.sessions:
                for run in session.runs:
                    assert run.params['tr'] == repetition_time
                    assert run.params['te'] == echo_time
                    assert run.params['flip_angle'] == flip_angle
                    assert run.params['phase_encoding_direction'] == \
                           phase_enc_direction
    assert len(mrd_num_subjects) == num_subjects
    shutil.rmtree(fake_ds_dir)
    return


if __name__ == '__main__':
    test_parse_dataset(11, 30.0, 40.0, 50.0, 'ROW')
