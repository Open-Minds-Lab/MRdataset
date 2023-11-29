import shlex
import sys
import tempfile

from hypothesis import given, settings, assume, HealthCheck

from MRdataset import load_mr_dataset
from MRdataset.cli import cli
from MRdataset.tests.conftest import dcm_dataset_strategy


@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=10, deadline=None)
@given(args=dcm_dataset_strategy)
def test_load(args):
    ds1, attributes = args
    assume(len(ds1.name) > 0)
    ds1.load()
    with tempfile.TemporaryDirectory() as tempdir:
        sys.argv = shlex.split(f'mrds --data-source {attributes["fake_ds_dir"]} '
                               f'--config {attributes["config_path"]} --name {ds1.name} '
                               f'--format dicom --output-dir {tempdir}')
        cli()
        ds2 = load_mr_dataset(f"/{tempdir}/{ds1.name}.mrds.pkl")
        assert ds1 == ds2
        return
