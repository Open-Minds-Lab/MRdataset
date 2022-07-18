"""Console script for MRdataset."""
import argparse
import sys
from pathlib import Path

from MRdataset import import_dataset


def main():
    """Console script for MRdataset."""
    parser = argparse.ArgumentParser(
        description='MRdataset : generates dataset for analysis',
        add_help=False)
    required = parser.add_argument_group('required arguments')
    optional = parser.add_argument_group('optional arguments')

    required.add_argument('-d', '--data_root', type=str, required=True,
                          help='directory containing downloaded dataset with '
                               'dicom files, supports nested hierarchies')
    optional.add_argument('-s', '--style', type=str, default='xnat',
                          help='choose type of dataset, one of [xnat|other]')
    optional.add_argument('-n', '--name', type=str,
                          help='provide a identifier/name for dataset')
    optional.add_argument('-h', '--help', action='help',
                          default=argparse.SUPPRESS,
                          help='show this help message and exit')
    optional.add_argument('-r', '--reindex', action='store_true',
                          help='overwrite existing metadata files')
    optional.add_argument('-v', '--verbose', action='store_true',
                          help='allow verbose output on console')
    optional.add_argument('--include_phantom', action='store_true',
                          help='whether to include phantom, localizer, '
                               'aahead_scout')
    optional.add_argument('--metadata_root', type=str, required=False,
                          help='directory to store cache')
    args = parser.parse_args()
    if not Path(args.data_root).is_dir():
        raise OSError('Expected valid directory for --data_root argument, '
                      'Got {}'.format(args.data_root))

    dataset = import_dataset(data_root=args.data_root,
                             style=args.style,
                             name=args.name,
                             reindex=args.reindex,
                             include_phantom=args.include_phantom,
                             verbose=args.verbose,
                             metadata_root=args.metadata_root)
    return dataset


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
