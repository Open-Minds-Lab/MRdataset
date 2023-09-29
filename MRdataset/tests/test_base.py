from copy import deepcopy

from hypothesis import given, settings

from MRdataset.tests.conftest import dcm_dataset_strategy

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
    return


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


@settings(max_examples=50, deadline=None)
@given(args=dcm_dataset_strategy)
def test_equality(args):
    ds1, attributes = args
    ds2, attributes = deepcopy(args)
    assert ds1 == ds2
