import errno
import json
import random
import shutil
import tempfile
import zipfile
from collections import defaultdict
from pathlib import Path

import pydicom
from MRdataset.dicom_utils import is_bids_file
from MRdataset.tests.config import compl_data_xnat
from MRdataset.utils import convert2ascii

# from bids import BIDSLayout

THIS_DIR = Path(__file__).parent.resolve()


def sample_dicom_dataset(tmp_path=None):
    if not tmp_path:
        tmp_path = tempfile.gettempdir()
    DATA_ARCHIVE = THIS_DIR / 'resources/example_dicom_data.zip'
    DATA_ROOT = Path(tmp_path)
    output_dir = DATA_ROOT / 'example_dicom_data'
    if not output_dir.exists():
        with zipfile.ZipFile(DATA_ARCHIVE, 'r') as zip_ref:
            zip_ref.extractall(DATA_ROOT)
    return DATA_ROOT / 'example_dicom_data'


def sample_bids_dataset(tmp_path=None):
    if not tmp_path:
        tmp_path = tempfile.gettempdir()
    DATA_ARCHIVE = THIS_DIR / 'resources/example_bids_data.zip'
    if not DATA_ARCHIVE.exists():
        raise FileNotFoundError(f'Please download example datasets from '
                                f' github')
    DATA_ROOT = Path(tmp_path)
    output_dir = DATA_ROOT / 'example_bids_dataset'
    if not output_dir.exists():
        with zipfile.ZipFile(DATA_ARCHIVE, 'r') as zip_ref:
            zip_ref.extractall(DATA_ROOT)
    return DATA_ROOT / 'example_bids_dataset'


def sample_vertical_dataset(tmp_path=None):
    if not tmp_path:
        tmp_path = tempfile.gettempdir()
    DATA_ARCHIVE = THIS_DIR / 'resources/vertical.zip'
    DATA_ROOT = Path(tmp_path)
    output_dir = DATA_ROOT / 'vertical/'
    if not output_dir.exists():
        with zipfile.ZipFile(DATA_ARCHIVE, 'r') as zip_ref:
            zip_ref.extractall(DATA_ROOT)
    return DATA_ROOT / 'vertical'


def make_vertical_test_dataset(num_sequences) -> Path:
    src_dir, dest_dir = setup_directories(sample_vertical_dataset())
    dcm_list = list(src_dir.glob('**/*.dcm'))

    seq_names = defaultdict(set)
    while True:
        filepath = random.choice(dcm_list)
        dicom = pydicom.read_file(filepath)
        export_dicom_file(dicom, filepath, dest_dir)
        subject_id = dicom.get('PatientID', None)
        seq_names[subject_id].add(dicom.get('SeriesDescription', None))
        if len(seq_names[subject_id]) >= num_sequences:
            break
    return dest_dir


def make_compliant_test_dataset(num_subjects,
                                repetition_time,
                                echo_train_length,
                                flip_angle) -> Path:
    src_dir, dest_dir = setup_directories(sample_dicom_dataset())
    dcm_list = list(src_dir.glob('**/*.dcm'))

    subject_names = set()
    i = 0
    while len(subject_names) < num_subjects:
        filepath = dcm_list[i]
        dicom = pydicom.read_file(filepath)

        dicom.RepetitionTime = repetition_time
        dicom.EchoTrainLength = echo_train_length
        dicom.FlipAngle = flip_angle

        export_dicom_file(dicom, filepath, dest_dir)
        subject_names.add(dicom.get('PatientID', None))
        i += 1
    return dest_dir


def make_compliant_bids_dataset(num_subjects,
                                repetition_time,
                                echo_train_length,
                                flip_angle) -> Path:
    src_dir, dest_dir = setup_directories(sample_bids_dataset())
    json_list = filter(is_bids_file, src_dir.glob('**/*.json'))
    subject_names = set()
    i = -1

    while len(subject_names) < num_subjects:
        i += 1

        try:
            filepath = next(json_list)
        except StopIteration:
            break

        try:
            with open(filepath, "r") as read_file:
                parameters = json.load(read_file)
        except (FileNotFoundError, ValueError):
            continue
        parameters['RepetitionTime'] = repetition_time
        parameters['EchoTrainLength'] = echo_train_length
        parameters['FlipAngle'] = flip_angle
        try:
            subject_name = str(filepath).split('/')[3]
            if subject_name in subject_names:
                continue
            subject_names.add(subject_name)
            export_bids_file(parameters, filepath, dest_dir, src_dir)
        except IndexError:
            pass
    return dest_dir


def make_multi_echo_dataset(num_subjects,
                            repetition_time,
                            echo_train_length,
                            flip_angle) -> Path:
    src_dir, dest_dir = setup_directories(sample_dicom_dataset())
    dcm_list = list(src_dir.glob('**/*.dcm'))

    subject_names = set()
    i = 0
    while len(subject_names) < num_subjects:
        filepath = dcm_list[i]
        dicom = pydicom.read_file(filepath)

        dicom.RepetitionTime = repetition_time
        dicom.EchoTrainLength = echo_train_length
        dicom.FlipAngle = flip_angle
        dicom.EchoTime = echo_train_length
        export_dicom_file(dicom, filepath, dest_dir)
        dicom.EchoTime = echo_train_length*2
        newfilepath = filepath.parent/(filepath.stem+'2.dcm')
        export_dicom_file(dicom, newfilepath, dest_dir)
        subject_names.add(dicom.get('PatientID', None))
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
    # copyeverything(src_dir, dest_dir)
    dataset_info = defaultdict(set)
    modalities = [s.name for s in src_dir.iterdir() if (s.is_dir() and
                                                        'mrdataset' not in
                                                        s.name)]
    for i, modality in enumerate(modalities):
        subject_paths = [s for s in (src_dir / modality).iterdir()]
        for sub_path in subject_paths:
            for filepath in sub_path.glob('*.dcm'):
                dicom = pydicom.read_file(filepath)
                export_dicom_file(dicom, filepath, dest_dir)

    for i, modality in enumerate(modalities):
        count = num_noncompliant_subjects[i]
        subject_paths = [s for s in (src_dir / modality).iterdir()]

        for j in range(count):
            sub_path = subject_paths[j]
            for filepath in sub_path.glob('**/*.dcm'):
                dicom = pydicom.read_file(filepath)
                patient_id = str(dicom.get('PatientID', None))
                dicom.RepetitionTime = repetition_time
                dicom.EchoTrainLength = echo_train_length
                dicom.FlipAngle = flip_angle
                export_dicom_file(dicom, filepath, dest_dir)
                modality = dicom.get('SeriesDescription', None).replace(' ', '_')
                dataset_info[modality].add(patient_id)

    return dest_dir, dataset_info


def export_dicom_file(dicom, filepath, out_dir):
    patient_id = dicom.get('PatientID', None)
    series_desc = dicom.get('SeriesDescription', None)
    series_number = dicom.get('SeriesNumber', None)
    series_desc = convert2ascii(series_desc.replace(' ', '_'))  # + '_' + str(series_number)
    output_path = out_dir / series_desc / patient_id
    number = dicom.get('InstanceNumber', None)
    output_path.mkdir(exist_ok=True, parents=True)
    filename = f'{patient_id}_{number}.dcm'
    dicom.save_as(output_path / filename)


def export_bids_file(parameters, filepath, out_dir, current_dir):
    relative_path = filepath.relative_to(current_dir)
    output_path = Path(out_dir)/relative_path
    output_path.parent.mkdir(exist_ok=True, parents=True)
    with open(output_path, 'w') as fh:
        json.dump(parameters, fh)

# def make_bids_test_dataset(num_noncompliant_subjects,
#                            repetition_time,
#                            magnetic_field_strength,
#                            flip_angle):
#     src_dir, dest_dir = setup_directories(compl_data_bids)  # noqa
#     copyeverything(src_dir, dest_dir)
#     dataset_info = defaultdict(set)
#
#     layout = BIDSLayout(dest_dir.as_posix())
#     subjects = layout.get_subjects()
#
#     for i, modality in enumerate(MRdataset.config.VALID_DATATYPES):
#         count = num_noncompliant_subjects[i]
#         non_compliant_subjects = set()
#         for sub in subjects:
#             if count < 1:
#                 break
#             filters = {'subject': sub,
#                        'datatype': modality,
#                        'extension': 'json'}
#             files = layout.get(**filters)
#             for bidsfile in files:
#                 with open(bidsfile.path, "r") as read_file:
#                     parameters = json.load(read_file)
#                 parameters['RepetitionTime'] = repetition_time
#                 parameters['MagneticFieldStrength'] = magnetic_field_strength
#                 parameters['FlipAngle'] = flip_angle
#                 with open(bidsfile.path, 'w') as fh:
#                     json.dump(parameters, fh)
#             if files:
#                 dataset_info[modality].add(sub)
#                 if len(dataset_info[modality]) >= count:
#                     break
#     return dest_dir, dataset_info
#
#
# def make_toy_bids_dataset(path):
#     src_dir = Path(path).resolve()
#     if not src_dir.exists():
#         raise FileNotFoundError("input directory not found")
#     dest_dir = src_dir.parent / 'toy_dataset'
#
#     copyeverything(src_dir, dest_dir)
#
#     # Delete all nii.gz files
#     for filepath in dest_dir.glob('**/*.nii.gz'):
#         filepath.unlink()
#
#     # Delete all tsv files
#     for filepath in dest_dir.glob('**/*.tsv'):
#         filepath.unlink()
#
#     # Delete a folder named 'sourcedata'. Not required
#     # shutil.rmtree(Path(dest_dir/'sourcedata')
#
#     # Create new subjects
#     # for k in range(2):
#     subjects = [f for f in dest_dir.iterdir() if f.name.startswith("sub")]
#     for i, subject in enumerate(subjects):
#         new_sub_name = '-'.join(
#             ['sub', str(len(subjects) + i + 1).zfill(2)])
#         for session in subject.iterdir():
#             for datatype in session.iterdir():
#                 for file in datatype.iterdir():
#                     name = str(file.name).split('_')[1:]
#                     new_filename = '_'.join([new_sub_name] + name)
#                     out_path = dest_dir / new_sub_name / session.name / datatype.name
#                     out_path.mkdir(parents=True, exist_ok=True)
#                     shutil.copy(file, out_path / new_filename)
