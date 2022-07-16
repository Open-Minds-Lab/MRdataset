import shutil
import tempfile
from pathlib import Path
from collections import defaultdict
import pydicom
import errno

anon_data_dir = '/home/sinhah/datasets/anonymous_data'
compl_data_dir = '/home/sinhah/datasets/compliant_data'


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
        subject_names.add(dicom.PatientID)
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
        patient_id = str(dicom.PatientID)
        if patient_id in compliant_subject_names:
            i += 1
            continue
        dicom.RepetitionTime = repetition_times[1]
        dicom.EchoTrainLength = echo_train_lengths[1]
        dicom.FlipAngle = flip_angles[1]

        export_file(dicom, filepath, dest_dir)
        non_compliant_subject_names.add(str(patient_id))
        i += 1
    return dest_dir


def make_compliant_test_dataset_w_info(num_subjects,
                                       repetition_time,
                                       echo_train_length,
                                       flip_angle) -> Path:
    src_dir, dest_dir = setup_directories()
    dcm_list = list(src_dir.glob('**/*.dcm'))
    dataset_info = defaultdict(lambda: defaultdict(dict))

    subject_names = set()
    i = 0
    while len(subject_names) < num_subjects:
        filepath = dcm_list[i]
        dicom = pydicom.read_file(filepath)
        patient_id = str(dicom.PatientID)

        dicom.RepetitionTime = repetition_time
        dicom.EchoTrainLength = echo_train_length
        dicom.FlipAngle = flip_angle
        modality = dicom.SeriesDescription.replace(' ', '_')
        export_file(dicom, filepath, dest_dir)
        subject_names.add(dicom.PatientID)

        dataset_info[modality][str(patient_id)]['tr'] = repetition_time
        dataset_info[modality][str(patient_id)]['etl'] = echo_train_length
        dataset_info[modality][str(patient_id)]['fa'] = flip_angle
        i += 1
    return dest_dir, dataset_info


def copyeverything(src, dst):
    if dst.exists():
        shutil.rmtree(dst)
    try:
        shutil.copytree(src, dst)
    except OSError as exc:
        if exc.errno in (errno.ENOTDIR, errno.EINVAL):
            shutil.copy(src, dst)
        else:
            raise


def make_non_compliant_test_dataset_w_info(
    num_noncompliant_subjects,
    repetition_time,
    echo_train_length,
    flip_angle
):
    src_dir, dest_dir = setup_directories(compl_data_dir)  # noqa
    print()
    copyeverything(src_dir, dest_dir)
    dataset_info = defaultdict(set)
    modalities = [s.name for s in src_dir.iterdir() if (s.is_dir() and
                                                        'mrdataset' not in
                                                        s.name)]

    for i, modality in enumerate(modalities):
        count = num_noncompliant_subjects[i]
        non_compliant_subjects = set()
        subject_paths = [s for s in (src_dir/modality).iterdir()]

        for j in range(count):
            sub_path = subject_paths[j]
            for filepath in sub_path.glob('**/*.dcm'):
                dicom = pydicom.read_file(filepath)
                patient_id = str(dicom.PatientID)
                dicom.RepetitionTime = repetition_time
                dicom.EchoTrainLength = echo_train_length
                dicom.FlipAngle = flip_angle
                export_file(dicom, filepath, dest_dir)
                modality = dicom.SeriesDescription.replace(' ', '_')
                dataset_info[modality].add(patient_id)

    return dest_dir, dataset_info


def export_file(dicom, filepath, out_dir):
    patient_id = str(dicom.data_element('PatientID').value)
    series_desc = str(dicom.data_element('SeriesDescription').value)
    series_desc = series_desc.replace(' ', '_')
    output_path = out_dir / series_desc / patient_id
    output_path.mkdir(exist_ok=True, parents=True)
    dicom.save_as(output_path / filepath.name)


if __name__ == '__main__':
    test_data_path = make_test_dataset(3, 2000, 34.4, 80.0, 'ROW')
    print(test_data_path)
