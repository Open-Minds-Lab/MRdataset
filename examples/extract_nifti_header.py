import nibabel as nib
"""Console script for MRdataset."""
import argparse
import sys
from pathlib import Path
import numpy as np
import json
import pickle
import bz2
import gzip


def files_under_folder(path, ext):
    if not Path(path).exists():
        raise FileNotFoundError("Folder doesn't exist")
    folder_path = Path(path).resolve()
    for file in folder_path.rglob('*'+ext):
        if file.is_file():
            yield file


def read(filepath):
    if not Path(filepath).exists():
        raise FileNotFoundError
    return nib.load(filepath)


def get_header(filepath):
    nii_image = read(filepath)
    params = dict()
    params['obliquity'] = np.any(nib.affines.obliquity(nii_image.affine) > 1e-4)
    params['voxel_sizes'] = nii_image.header.get_zooms()
    params['matrix_dims'] = nii_image.shape
    params['header'] = nii_image.header
    return params


def save_hdr2pkl(filename, data):
    if not Path(filename.parent).exists():
        Path(filename.parent).mkdir(parents=True)
    fullpath = filename
    # with open(fullpath, 'wb') as fp:
    #     pickle.dump(data, fp, protocol=pickle.HIGHEST_PROTOCOL)
    with gzip.open(fullpath.with_suffix('.gz'), "wb") as f:
        pickle.dump(data, f)
    # with bz2.BZ2File(fullpath.with_suffix('.pbz2'), 'wb') as f:
    #     pickle.dump(data, f)


def walk(data_dir):
    for filepath in files_under_folder(data_dir, '.nii'):
        try:
            print(filepath)
            params = get_header(filepath)
            filename = filepath.with_suffix('.pkl')
            # if not filename.exists():
            save_hdr2pkl(filename, params)
        except:
            continue

    for filepath in files_under_folder(data_dir, '.nii.gz'):
        try:
            print(filepath)
            filename = filepath.with_suffix('').with_suffix('.pkl')
            params = get_header(filepath)
            # if not filename.exists():
            save_hdr2pkl(filename, params)
        except:
            continue

def main():
    """Console script for MRdataset."""
    parser = argparse.ArgumentParser(
        description='export nifti headers for analysis',
        add_help=False)
    required = parser.add_argument_group('required arguments')
    optional = parser.add_argument_group('optional arguments')

    required.add_argument('-d', '--data_source', type=str, required=True,
                          help='directory containing downloaded dataset with '
                               'nifti files, supports nested hierarchies')

    args = parser.parse_args()
    if not Path(args.data_source).is_dir():
        raise OSError('Expected valid directory for --data_source argument, '
                      'Got {}'.format(args.data_source))
    walk(args.data_source)
    return


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover

