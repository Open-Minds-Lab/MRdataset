import tempfile
from pathlib import Path

import pydicom

anon_data_dir = '/home/sinhah/datasets/anonymous_data'


def get_test_dataset(num_subjects,
                     repetition_time,
                     echo_time,
                     flip_angle,
                     phase_enc_direction):
    src_dir = Path(anon_data_dir).resolve()
    if not src_dir.exists():
        print(src_dir)
        raise FileNotFoundError("Source Directory {} not found".format(src_dir))

    temp_dir = tempfile.mkdtemp()
    dest_dir = Path(temp_dir).resolve()
    if not dest_dir.exists():
        raise FileNotFoundError("Temporary directory not found")

    dcm_list = list(src_dir.glob('**/*.dcm'))

    subject_names = set()
    i = 0
    while len(subject_names) < num_subjects:
        filepath = dcm_list[i]
        dicom = pydicom.read_file(filepath)

        dicom.RepetitionTime = repetition_time
        dicom.EchoTime = echo_time
        dicom.FlipAngle = flip_angle

        export_file(dicom, filepath, dest_dir)
        subject_names.add(dicom.PatientName)
        i += 1
    return dest_dir


def export_file(dicom, filepath, out_dir):
    patient_name = str(dicom.data_element('PatientName').value)
    series_desc = str(dicom.data_element('SeriesDescription').value)
    series_desc = series_desc.replace(' ', '_')
    output_path = out_dir / patient_name / series_desc
    output_path.mkdir(exist_ok=True, parents=True)
    dicom.save_as(output_path / filepath.name)


if __name__ == '__main__':
    test_data_path = get_test_dataset(3, 2000, 34.4, 80.0, 'ROW')
    print(test_data_path)
