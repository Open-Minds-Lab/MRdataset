from copy import deepcopy

import pytest
from hypothesis import given, settings

from MRdataset.dicom import DicomDataset
from MRdataset.tests.conftest import dcm_dataset_strategy
from MRdataset.tests.simulate import make_compliant_test_dataset
from MRdataset.utils import convert2ascii


@settings(max_examples=50, deadline=None)
@given(args=dcm_dataset_strategy)
def test_load(args):
    ds, attributes = args
    assert attributes['fake_ds_dir'] in ds.data_source
    assert convert2ascii(attributes['name']) == ds.name
    assert len(ds._subj_ids) == 0
    ds.load()
    assert attributes['num_subjects'] == len(ds._subj_ids)
    for seq_id in ds.get_sequence_ids():
        for subject, session, run, seq in ds.traverse_horizontal(seq_id):
            assert seq['RepetitionTime']._value == attributes['repetition_time']
            assert seq['EchoTrainLength']._value == attributes['echo_train_length']
            assert seq['FlipAngle']._value == attributes['flip_angle']
            subjects = ds.get_subject_ids(seq_id)
            assert subject in subjects
    assert not ds.get_subject_ids('non-existent-seq-id')
    with pytest.raises(TypeError):
        ds.get_subject_ids(None)
    return


def test_accept_valid_dataset_format():
    fake_ds_dir = make_compliant_test_dataset(1, 1, 1, 1)
    with pytest.raises(ValueError):
        ds = DicomDataset(name='invalid_format',
                          data_source=fake_ds_dir,
                          ds_format='invalid_format',
                          config_path='../../examples/mri-config.json')

@settings(max_examples=50, deadline=None)
@given(args=dcm_dataset_strategy)
def test_add(args):
    ds, attributes = args
    ds.load()
    for seq_id in ds.get_sequence_ids():
        for subject, session, run, seq in ds.traverse_horizontal(seq_id):
            assert (subject, session, run) in ds._seqs_map[seq_id]
            assert seq_id in ds._sess_map[session]
            assert subject in ds._subj_ids
            assert ds._flat_map[(subject, session, seq_id, run)] == ds[subject][session][seq_id][run]

            assert ds.get(subject, session, run, seq_id) is None
            with pytest.raises(TypeError):
                ds.add(subject, session, seq_id, run, None)


@settings(max_examples=50, deadline=None)
@given(args=dcm_dataset_strategy)
def test_equality(args):
    ds1, attributes = args
    ds2, attributes = deepcopy(args)
    assert ds1 == ds2

    with pytest.raises(TypeError):
        assert ds1 == None
    with pytest.raises(ValueError):
        ds1.format = 'invalid'
        assert ds1 == ds2


