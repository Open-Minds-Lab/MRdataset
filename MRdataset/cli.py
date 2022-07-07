"""Console script for MRdataset."""
import argparse
import sys
from pathlib import Path

from MRdataset import create_dataset


def main():
    """Console script for MRdataset."""
    parser = argparse.ArgumentParser(description='MRdataset, generate interface for dataset for analysis',
                                     add_help=False)
    required = parser.add_argument_group('required arguments')
    optional = parser.add_argument_group('optional arguments')

    required.add_argument('-d', '--data_root', type=str, required=True,
                          help='directory containing downloaded dataset with dicom files, supports nested hierarchies')
    optional.add_argument('-s', '--style', type=str, default='xnat',
                          help='choose type of dataset, one of [xnat|bids|other]')
    optional.add_argument('-n', '--name', type=str,
                          help='provide a identifier/name for dataset')
    optional.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS,
                          help='show this help message and exit')
    optional.add_argument('-r', '--reindex', action='store_true',
                          help='overwrite existing metadata files')
    optional.add_argument('-v', '--verbose', action='store_true',
                          help='allow verbose output on console')

    args = parser.parse_args()
    if not Path(args.data_root).is_dir():
        raise OSError('Expected valid directory for --data_root argument, Got {0}'.format(args.data_root))

    dataset = create_dataset(data_root=args.data_root,
                             style=args.style,
                             name=args.name,
                             reindex=args.reindex,
                             verbose=args.verbose)
    return dataset


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
