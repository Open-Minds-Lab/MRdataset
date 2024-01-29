import shutil
import tempfile
from collections import defaultdict
from pathlib import Path

import hypothesis.strategies as st
import pytest
from bids import BIDSLayout
from hypothesis import given, settings, HealthCheck

from MRdataset import import_dataset
from MRdataset.bids import BidsDataset
from MRdataset.tests.simulate import make_compliant_test_dataset, \
    make_multi_echo_dataset, copyeverything, make_compliant_bids_dataset

THIS_DIR = Path(__file__).parent.resolve()


@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=50,
          deadline=None)
@given(st.integers(min_value=1, max_value=10),
       st.floats(allow_nan=False,
                 allow_infinity=False),
       st.integers(min_value=-10000000, max_value=10000000),
       st.floats(allow_nan=False,
                 allow_infinity=False))
def test_dataset(num_subjects,
                 repetition_time,
                 echo_train_length,
                 flip_angle):
    fake_ds_dir = make_compliant_bids_dataset(num_subjects,
                                              repetition_time,
                                              echo_train_length,
                                              flip_angle)
    mrd = import_dataset(data_source=fake_ds_dir, ds_format='bids',
                         config_path=THIS_DIR / 'resources/bids-config.json',
                         output_dir=fake_ds_dir, name='test_dataset')
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
