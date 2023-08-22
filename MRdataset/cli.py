"""Console script for MRdataset."""
import argparse
import sys
from pathlib import Path

from MRdataset import import_dataset
from MRdataset import logger


def main():
    """Console script for MRdataset."""
    parser = argparse.ArgumentParser(
        description='MRdataset : generates dataset for analysis',
        add_help=False)
    required = parser.add_argument_group('required arguments')
    optional = parser.add_argument_group('optional arguments')

    required.add_argument('-d', '--data-source', type=str, required=True,
                          help='directory containing downloaded dataset with '
                               'dicom files, supports nested hierarchies')
    optional.add_argument('-f', '--format', type=str, default='dicom',
                          help='choose type of dataset, expected'
                               'one of [dicom|bids|pybids]')
    optional.add_argument('-n', '--name', type=str,
                          help='provide a identifier/name for dataset')
    optional.add_argument('-h', '--help', action='help',
                          default=argparse.SUPPRESS,
                          help='show this help message and exit')
    optional.add_argument('--is-partial', action='store_true',
                          help='flag dataset as a partial dataset')
    optional.add_argument('-v', '--verbose', action='store_true',
                          help='allow verbose output on console')
    args = parser.parse_args()
    if not Path(args.data_source).is_dir():
        raise OSError('Expected valid directory for --data_source argument, '
                      f'Got {args.data_source}')
    if args.verbose:
        logger.setLevel('INFO')
    else:
        logger.setLevel('WARNING')

    dataset = import_dataset(data_source=args.data_source,
                             ds_format=args.format,
                             name=args.name,
                             verbose=args.verbose,
                             is_complete=not args.is_partial)
    return dataset


if __name__ == '__main__':
    sys.exit(main())  # pragma: no cover
