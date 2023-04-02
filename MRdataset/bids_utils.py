import json
from json import JSONDecodeError
from pathlib import Path
from typing import Union
import re
import nibabel as nib
import numpy as np
from bids.layout import BIDSFile

from MRdataset.config import PARAMETER_NAMES, VALID_BIDS_EXTENSIONS, VALID_DATATYPES
from MRdataset.utils import make_hashable
from MRdataset.base import Run, Session


def is_valid_bidsfile(filepath) -> bool:
    if filepath.name.startswith('.'):
        return False
    if filepath.name.startswith('.bidsignore'):
        return False
    parents = [p.name for p in filepath.parents]
    check_sub = ['sub' in p for p in parents]
    if not any(check_sub):
        return False
    if 'sourcedata' in parents:
        return False
    if 'derivatives' in parents:
        return False
    ext = get_ext(filepath)
    if ext not in VALID_BIDS_EXTENSIONS:
        return False
    if filepath.parent.name not in VALID_DATATYPES:
        return False
    return True


def parse(session_node: Session,
          filepath: Path,
          include_nifti_header=False) -> Session:
    """
        Extracts parameters for a file. Adds the parameters as a
        new run node to given session node, returns modified session node.

        Parameters
        ----------
        filepath : Path
            path to the file
        session_node : MRdataset.base.Session
            session node to which the run node has to be added
        include_nifti_header :
            whether to check nifti headers for compliance,
            only used when --ds_format==bids

        Returns
        -------
        session_node : MRdataset.base.Session
            modified session_node which also contains the new run
        """

    filename = filepath.stem
    params_from_file = {}
    filepath = filepath.parent / (filepath.stem + '.json')
    if filepath.is_file():
        params_from_file.update(select_parameters(filepath))

    if include_nifti_header:
        filepath = filepath.parent / (filepath.stem + '.nii')
        if filepath.is_file():
            params_from_file.update(select_parameters(filepath))

        filepath = filepath.parent / (filepath.stem + '.nii.gz')
        if filepath.is_file():
            params_from_file.update(select_parameters(filepath))

    if params_from_file:
        run_node = session_node.get_run_by_name(filename)
        if run_node is None:
            run_node = Run(filename)
        for k, v in params_from_file.items():
            run_node.params[k] = v
        # ignore echo_time for BIDS dataset, already incorporated in
        # echo entity
        echo_time = 1.0
        # if not isinstance(echo_time, (int, float)):
        #     echo_time = 1.0
        run_node.echo_time = echo_time
        session_node.add_run(run_node)
    return session_node


def combine_entity_labels(filepath, datatype):
    filename = Path(filepath).stem
    # exts = ''.join(filepath.suffixes)
    # filename = str(filepath).replace(exts, '')
    # suffix = ''
    # match1 = re.search('(?<=ses-)[^_]+(_[^_]+)*$', filename)
    # if not match1:
    #     match1 = re.search('(?<=sub-)[^_]+(_[^_]+)*$', filename)
    # if match1:
    #     match1 = match1.group()
    #     match2 = re.search('(?<=_)[^_]+(_[^_]+)*$', match1)
    #     if match2:
    #         suffix = match2.group()
    #     else:
    #         suffix = match1
    # return f'{datatype}_{suffix}'
    split_kv_pairs = filename.split('_')
    if not split_kv_pairs:
        raise ValueError("Filename doesn't have any entity values")
    entity_dict = {}
    suffix = split_kv_pairs[-1]
    # Skipping the last item because it is the suffix
    # Skipped entties are: sub, ses, rec, run, recording
    # Entities not found any: ce, mod
    for item in split_kv_pairs[:-1]:
        key, value = item.split('-')
        if key not in ['sub', 'ses', 'rec', 'run', 'recording']:
            entity_dict[key] = value
    joined_entities = join_entities(entity_dict)
    complete_string = [datatype]
    if joined_entities:
        complete_string.append(joined_entities)
    complete_string.append(suffix)
    return '_'.join(complete_string)


def join_entities(entity_dict):
    format_str = None
    for key, value in entity_dict.items():
        if format_str:
            format_str = f'{format_str}_{key}-{value}'
        else:
            format_str = f'{key}-{value}'
    return format_str


def select_parameters(file) -> dict:
    """
    Reads parameters for BIDS datasets. The filepath can either point to a
     JSON file or a NIfTI file. In case of a NIfTI file the parameters are
     extracted from the header.

    Parameters
    ----------
    file : pathlib.Path or str
        Path pointing to either a JSON or NIfTI file
    Returns
    -------

    """
    # TODO: filepath should already have the extension, why do you need to
    #  pass separately? Modify the code.

    selected_params = dict()

    if isinstance(file, BIDSFile):
        file_path = file.path
    elif isinstance(file, Path):
        file_path = file
    else:
        raise NotImplementedError

    ext = get_ext(file)
    if file_path.name.startswith('.bidsignore'):
        return selected_params

    if ext == '.json':
        try:
            with open(file_path, "r") as read_file:
                parameters = json.load(read_file)
        except JSONDecodeError:
            return selected_params
        for key in parameters:
            for entry in PARAMETER_NAMES:
                if entry.lower() in key.lower():
                    selected_params[key] = make_hashable(parameters[key])
    elif ext in ['.nii', '.nii.gz']:
        nii_image = nib.load(file_path)
        selected_params['obliquity'] = np.any(
            nib.affines.obliquity(nii_image.affine) > 1e-4)
        selected_params['voxel_sizes'] = make_hashable(nii_image.header.get_zooms())
        selected_params['matrix_dims'] = make_hashable(nii_image.shape)
        for key, value in nii_image.header.items():
            if key not in ['sizeof_hdr', 'data_type', 'db_name',
                           'extents', 'session_error']:
                value = make_hashable(value)
                selected_params[key] = value
    return selected_params


def get_ext(file: Union[BIDSFile, Path]) -> str:
    """
    Extract the extension from a BIDSFile object.
    Parameters
    ----------
    file : A BIDSFile object

    Returns
    -------
    file extension as a string
    """
    if isinstance(file, BIDSFile):
        return file.tags['extension'].value
    elif isinstance(file, Path):
        return "".join(file.suffixes)
    else:
        raise NotImplementedError('File Format not supported')
