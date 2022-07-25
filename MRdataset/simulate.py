import errno
import json
import shutil
import tempfile
from collections import defaultdict
from pathlib import Path

import MRdataset.config
import pydicom
from MRdataset.tests.config import anon_data_dir, compl_data_xnat, \
    compl_data_bids
from bids import BIDSLayout


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


def make_test_dataset(num_noncompliant_subjects,
                      repetition_time,
                      echo_train_length,
                      flip_angle):
    src_dir, dest_dir = setup_directories(compl_data_xnat)  # noqa
    print()
    copyeverything(src_dir, dest_dir)
    dataset_info = defaultdict(set)
    modalities = [s.name for s in src_dir.iterdir() if (s.is_dir() and
                                                        'mrdataset' not in
                                                        s.name)]

    for i, modality in enumerate(modalities):
        count = num_noncompliant_subjects[i]
        subject_paths = [s for s in (src_dir / modality).iterdir()]

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


def make_bids_test_dataset(num_noncompliant_subjects,
                           repetition_time,
                           magnetic_field_strength,
                           flip_angle):
    src_dir, dest_dir = setup_directories(compl_data_bids)  # noqa
    copyeverything(src_dir, dest_dir)
    dataset_info = defaultdict(set)

    layout = BIDSLayout(dest_dir.as_posix())
    subjects = layout.get_subjects()

    for i, modality in enumerate(MRdataset.config.datatypes):
        count = num_noncompliant_subjects[i]
        non_compliant_subjects = set()
        for sub in subjects:
            if count < 1:
                break
            filters = {'subject': sub,
                       'datatype': modality,
                       'extension': 'json'}
            files = layout.get(**filters)
            for bidsfile in files:
                with open(bidsfile.path, "r") as read_file:
                    parameters = json.load(read_file)
                parameters['RepetitionTime'] = repetition_time
                parameters['MagneticFieldStrength'] = magnetic_field_strength
                parameters['FlipAngle'] = flip_angle
                with open(bidsfile.path, 'w') as fh:
                    json.dump(parameters, fh)
            if files:
                dataset_info[modality].add(sub)
                if len(dataset_info[modality]) >= count:
                    break
    return dest_dir, dataset_info


def make_toy_bids_dataset(path):
    src_dir = Path(path).resolve()
    if not src_dir.exists():
        raise FileNotFoundError("input directory not found")
    dest_dir = src_dir.parent / 'toy_dataset'

    copyeverything(src_dir, dest_dir)

    # Delete all nii.gz files
    for filepath in dest_dir.glob('**/*.nii.gz'):
        filepath.unlink()

    # Delete all tsv files
    for filepath in dest_dir.glob('**/*.tsv'):
        filepath.unlink()

    # Delete a folder named 'sourcedata'. Not required
    # shutil.rmtree(Path(dest_dir/'sourcedata')

    # Create new subjects
    # for k in range(2):
    subjects = [f for f in dest_dir.iterdir() if f.name.startswith("sub")]
    for i, subject in enumerate(subjects):
        new_sub_name = '-'.join(
            ['sub', str(len(subjects) + i + 1).zfill(2)])
        for session in subject.iterdir():
            for datatype in session.iterdir():
                for file in datatype.iterdir():
                    name = str(file.name).split('_')[1:]
                    new_filename = '_'.join([new_sub_name] + name)
                    out_path = dest_dir / new_sub_name / session.name / datatype.name
                    out_path.mkdir(parents=True, exist_ok=True)
                    shutil.copy(file, out_path / new_filename)
