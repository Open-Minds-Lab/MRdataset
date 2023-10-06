import typing as tp
from typing import Tuple

import pytest
import pydicom
from pathlib import Path
import zipfile

from hypothesis import strategies as st
from hypothesis.strategies import SearchStrategy

from MRdataset.dicom import DicomDataset
from MRdataset.tests.simulate import make_compliant_test_dataset, make_vertical_test_dataset


@pytest.fixture
def sample_dicom_object(tmp_path='/tmp'):
    dicom_file = Path(tmp_path) / "sample_dicom.dcm"
    sample_dicom = pydicom.Dataset()
    sample_dicom.PatientName = "CITIZEN^Joan"
    sample_dicom.add_new(0x00100020, 'LO', '12345')
    sample_dicom[0x0010, 0x0030] = pydicom.DataElement(0x00100030, 'DA', '20010101')
    sample_dicom.SeriesDescription = "TestScan"
    yield sample_dicom
    sample_dicom.save_as(str(dicom_file))


@pytest.fixture
def valid_dicom_file(tmp_path):
    return Path('../../examples/valid.dcm').resolve()


@pytest.fixture
def invalid_dicom_file(tmp_path):
    return Path('../../examples/invalid.dcm').resolve()


@pytest.fixture
def derived_dicom_file(tmp_path):
    return Path('../../examples/derived.dcm').resolve()


param_strategy: tp.Final[SearchStrategy[Tuple]] = st.tuples(
    st.text(min_size=1, max_size=10),
    st.integers(min_value=2, max_value=10),
    st.floats(allow_nan=False,
              allow_infinity=False),
    st.integers(min_value=-10000000, max_value=10000000),
    st.floats(allow_nan=False,
              allow_infinity=False)
)


@st.composite
def create_dataset(draw_from: st.DrawFn) -> Tuple:
    name, num_subjects, repetition_time, echo_train_length, flip_angle = draw_from(param_strategy)
    fake_ds_dir = make_compliant_test_dataset(num_subjects,
                                              repetition_time,
                                              echo_train_length,
                                              flip_angle)
    ds = DicomDataset(name=name,
                      data_source=fake_ds_dir,
                      config_path='./mri-config.json')
    attributes = {
        'name': name,
        'num_subjects': num_subjects,
        'repetition_time': repetition_time,
        'echo_train_length': echo_train_length,
        'flip_angle': flip_angle,
        'fake_ds_dir': fake_ds_dir,
        'config_path': './mri-config.json'
    }
    return ds, attributes


# vertical_strategy: tp.Final[SearchStrategy[Tuple]] = st.tuples(
#     st.text(min_size=2, max_size=10),
# )


@st.composite
def create_vertical_dataset(draw_from: st.DrawFn) -> Tuple:
    # name, num_sequences = draw_from(vertical_strategy)
    name = 'vertical'
    num_sequences = 3
    fake_ds_dir = make_vertical_test_dataset(num_sequences)
    ds = DicomDataset(name=name,
                      data_source=fake_ds_dir,
                      config_path='./mri-config.json')
    attributes = {
        'name': name,
        'num_sequences': num_sequences,
        'fake_ds_dir': fake_ds_dir,
        'config_path': './mri-config.json'
    }
    return ds, attributes


dcm_dataset_strategy: tp.Final[SearchStrategy[Tuple]] = create_dataset()

vertical_dataset_strategy: tp.Final[SearchStrategy[Tuple]] = create_vertical_dataset()
