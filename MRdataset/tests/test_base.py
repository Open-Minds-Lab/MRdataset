from copy import deepcopy
from itertools import product
from pathlib import Path

import pytest
from hypothesis import given, settings, HealthCheck

from MRdataset.tests.conftest import dcm_dataset_strategy, \
    vertical_dataset_strategy
from MRdataset.utils import convert2ascii

THIS_DIR = Path(__file__).parent.resolve()


@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=50, deadline=None)
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
            assert seq['RepetitionTime'].get_value() == attributes['repetition_time']
            assert seq['EchoTrainLength'].get_value() == attributes['echo_train_length']
            assert seq['FlipAngle'].get_value() == attributes['flip_angle']
            subjects = ds.get_subject_ids(seq_id)
            assert subject in subjects
    assert not ds.get_subject_ids('non-existent-seq-id')
    with pytest.raises(TypeError):
        ds.get_subject_ids(None)
    return


# def test_accept_valid_dataset_format():
#     fake_ds_dir = make_compliant_test_dataset(1, 1, 1, 1)
#     with pytest.raises(ValueError):
#         ds = import_dataset(name='invalid_format',
#                             data_source=fake_ds_dir,
#                             config_path=THIS_DIR / 'resources/mri-config.json')


@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=50, deadline=None)
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


@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=50, deadline=None)
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


@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=50, deadline=None)
@given(args=dcm_dataset_strategy)
def test_horizontal_traversal(args):
    ds1, attributes = args
    ds1.load()

    # true attributes
    num_subjects_on_disk = attributes['num_subjects']
    sequences_on_disk = {}
    for subfolder in attributes['fake_ds_dir'].iterdir():
        seq_name = subfolder.name

        if seq_name not in sequences_on_disk:
            sequences_on_disk[seq_name] = []
        for seq_folder in subfolder.iterdir():
            subject_name = seq_folder.name
            sequences_on_disk[seq_name].append(subject_name)

    seq_ids = ds1.get_sequence_ids()
    for seq_id in seq_ids:
        for subject, session, run, seq in ds1.traverse_horizontal(seq_id):
            assert subject in sequences_on_disk[seq_id]


# suppress healthcheck.too_slow
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=10, deadline=None)
@given(args=vertical_dataset_strategy)
def test_vertical_traversal(args):
    ds1, attributes = args
    ds1.load()

    # true attributes
    sequences_on_disk = {}
    for subfolder in attributes['fake_ds_dir'].iterdir():
        seq_name = subfolder.name
        if seq_name not in sequences_on_disk:
            sequences_on_disk[seq_name] = []
        for seq_folder in subfolder.iterdir():
            subject_name = seq_folder.name
            sequences_on_disk[seq_name].append(subject_name)

    seq_ids = ds1.get_sequence_ids()
    for seq_id1, seq_id2 in product(seq_ids, seq_ids):
        if seq_id1 == seq_id2:
            continue
        for subject, session, run1, run2, seq1, seq2 in ds1.traverse_vertical2(seq_id1, seq_id2):
            assert seq1.run_id != seq2.run_id
            assert seq1.subject_id == seq2.subject_id
            assert seq1.session_id == seq2.session_id
            assert seq1.path != seq2.path
            assert seq1.name != seq2.name


@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=10, deadline=None)
@given(args=vertical_dataset_strategy)
def test_vertical_traversal_multi(args):
    ds1, attributes = args
    ds1.load()

    # true attributes
    sequences_on_disk = {}
    for subfolder in attributes['fake_ds_dir'].iterdir():
        seq_name = subfolder.name
        if seq_name not in sequences_on_disk:
            sequences_on_disk[seq_name] = []
        for seq_folder in subfolder.iterdir():
            subject_name = seq_folder.name
            sequences_on_disk[seq_name].append(subject_name)

    seq_ids = ds1.get_sequence_ids()
    for seq_id1, seq_id2, seq_id3 in product(seq_ids, repeat=3):
        if seq_id1 == seq_id2 or seq_id1 == seq_id3 or seq_id2 == seq_id3:
            continue
        seqs = [seq_id1, seq_id2, seq_id3]
        for subject, session, runs, seqs in ds1.traverse_vertical_multi(*seqs):
            assert seqs[1].run_id != seqs[2].run_id
            assert seqs[1].subject_id == seqs[2].subject_id
            assert seqs[1].session_id == seqs[2].session_id
            assert seqs[1].path != seqs[2].path
            assert seqs[1].name != seqs[2].name

            assert seqs[1].run_id != seqs[0].run_id
            assert seqs[1].subject_id == seqs[0].subject_id
            assert seqs[1].session_id == seqs[0].session_id
            assert seqs[1].path != seqs[0].path
            assert seqs[1].name != seqs[0].name

            assert seqs[0].run_id != seqs[2].run_id
            assert seqs[0].subject_id == seqs[2].subject_id
            assert seqs[0].session_id == seqs[2].session_id
            assert seqs[0].path != seqs[2].path
            assert seqs[0].name != seqs[2].name
