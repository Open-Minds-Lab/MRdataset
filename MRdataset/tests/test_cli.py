import subprocess

from hypothesis import given, settings, assume

from MRdataset import load_mr_dataset, BaseDataset
from MRdataset.tests.conftest import dcm_dataset_strategy


@settings(max_examples=50, deadline=None)
@given(args=dcm_dataset_strategy)
def test_load(args):
    ds1, attributes = args
    assume(len(ds1.name) > 0)
    ds1.load()

    subprocess.run(['mrds',
                    '--data-source', attributes['fake_ds_dir'],
                    '--config', attributes['config_path'],
                    '--name', ds1.name,
                    '--format', 'dicom',
                    '--output-dir', '/tmp'])

    ds2 = load_mr_dataset(f"/tmp/{ds1.name}.mrds.pkl")
    assert ds1 == ds2
    return
