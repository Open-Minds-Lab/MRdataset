import pytest
import pydicom
from pathlib import Path
import zipfile


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


