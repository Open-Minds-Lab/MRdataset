import glob
import shutil
import tempfile
from pathlib import Path

import hypothesis.strategies as st
import pytest
from hypothesis import given, settings, HealthCheck

from MRdataset import import_dataset
from MRdataset.tests.simulate import make_compliant_bids_dataset

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
        for subject, _, _, seq in mrd.traverse_horizontal(seq_id):
            mrd_num_subjects.add(subject)
            assert seq['RepetitionTime'].get_value() == repetition_time
            assert seq['EchoTrainLength'].get_value() == echo_train_length
            assert seq['FlipAngle'].get_value() == flip_angle
        assert set(mrd.get_subject_ids(seq_id)) == mrd_num_subjects
    shutil.rmtree(fake_ds_dir)
    return


def test_config_dict():
    fake_ds_dir = make_compliant_bids_dataset(1, 1, 1, 1)
    with pytest.raises(FileNotFoundError):
        import_dataset(fake_ds_dir, config_path='non-existent.json',
                       output_dir=fake_ds_dir, name='test_dataset',
                       ds_format='bids')


def test_invalid_output_dir():
    fake_ds_dir = make_compliant_bids_dataset(1, 1, 1, 1)
    with pytest.raises(TypeError):
        import_dataset(fake_ds_dir,
                       config_path=THIS_DIR / 'resources/bids-config.json',
                       output_dir=1, name='test_dataset',
                       ds_format='bids')


def test_invalid_datatype():
    fake_ds_dir = make_compliant_bids_dataset(4, 1, 1, 1)

    def rename_folders(directory):
        # rename all folders to "mnat"
        for folder in glob.glob(str(directory) + '/*/'):
            folder = Path(folder)
            if ('sub' not in folder.name) and ('ses' not in folder.name):
                folder.rename(folder.parent / 'mnat')
                rename_folders(folder.parent / 'mnat')
            else:
                if folder.is_dir():
                    rename_folders(folder)

    rename_folders(fake_ds_dir)
    with pytest.raises(TypeError):
        import_dataset(fake_ds_dir,
                       config_path=THIS_DIR / 'resources/bids-config.json',
                       output_dir=1, name='test_dataset',
                       ds_format='bids')


def test_empty_folders():
    with tempfile.TemporaryDirectory() as tmpdirname:
        folder_path = Path(tmpdirname)
        subfolder = folder_path / "derivatives"
        subfolder.mkdir(parents=True, exist_ok=True)
        filepath = subfolder / "test.json"
        filepath.touch()

        mrd = import_dataset(folder_path,
                             config_path=THIS_DIR / 'resources/mri-config.json',
                             output_dir=folder_path, name='test_dataset',
                             ds_format='bids')
        assert len(mrd.get_sequence_ids()) == 0
