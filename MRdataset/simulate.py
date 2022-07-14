import tempfile
from pathlib import Path

import pydicom

anon_data_dir = '/home/sinhah/datasets/anonymous_data'


def make_compliant_test_dataset(num_subjects,
                                repetition_time,
                                echo_train_length,
                                flip_angle) -> Path:
    src_dir, dest_dir = setup_directories(anon_data_dir)
    dcm_list = list(src_dir.glob('**/*.dcm'))

    subject_names = set()
    i = 0
    while len(subject_names) < num_subjects:
        filepath = dcm_list[i]
        dicom = pydicom.read_file(filepath)

        dicom.RepetitionTime = repetition_time
        dicom.EchoTrainLength = echo_train_length
        dicom.FlipAngle = flip_angle

        export_file(dicom, filepath, dest_dir)
        subject_names.add(dicom.PatientName)
        i += 1
    return dest_dir


def setup_directories(src):
    src_dir = Path(src).resolve()
    if not src_dir.exists():
        print(src_dir)
        raise FileNotFoundError("Source Directory {} not found".format(src_dir))

    temp_dir = tempfile.mkdtemp()
    dest_dir = Path(temp_dir).resolve()
    if not dest_dir.exists():
        raise FileNotFoundError("Temporary directory not found")

    return src_dir, dest_dir


def make_non_compliant_test_dataset(num_subjects,
                                    num_compliant_subjects,
                                    repetition_times,
                                    echo_train_lengths,
                                    flip_angles
                                    ):
    # src_dir, dest_dir = setup_directories(anon_data_dir) # noqa
    dest_dir = make_compliant_test_dataset(num_compliant_subjects,
                                           repetition_times[0],
                                           echo_train_lengths[0],
                                           flip_angles[0])

    src_dir = Path(anon_data_dir)
    dcm_list = list(src_dir.glob('**/*.dcm'))

    compliant_subject_names = set([i.name for i in dest_dir.iterdir()])
    non_compliant_subject_names = set()

    i = 0
    # Adding non_compliant subjects
    while len(non_compliant_subject_names) < \
        num_subjects - num_compliant_subjects:
        filepath = dcm_list[len(dcm_list) - i - 1]
        dicom = pydicom.read_file(filepath)
        patient_name = str(dicom.PatientName)
        if patient_name in compliant_subject_names:
            i += 1
            continue
        dicom.RepetitionTime = repetition_times[1]
        dicom.EchoTrainLength = echo_train_lengths[1]
        dicom.FlipAngle = flip_angles[1]

        export_file(dicom, filepath, dest_dir)
        non_compliant_subject_names.add(str(patient_name))
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
    test_data_path = make_test_dataset(3, 2000, 34.4, 80.0, 'ROW')
    print(test_data_path)
