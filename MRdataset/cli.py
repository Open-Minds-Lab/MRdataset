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

    # Add help
    optional.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS,
                          help='show this help message and exit')
    required.add_argument('-i', '--dataroot', type=str,
                          help='directory containing downloaded dataset with dicom files, supports nested hierarchies')
    required.add_argument('-m', '--metadataroot', type=str,
                          help='directory to store metadata files')
    required.add_argument('-n', '--name', type=str,
                          help='provide a identifier/name for dataset')
    optional.add_argument('-r', '--reindex', action='store_true',
                          help='overwrite existing metadata files')
    optional.add_argument('-v', '--verbose', action='store_true',
                          help='allow verbose output on console')
    optional.add_argument('-c', '--create', action='store_true',
                          help='create directories if required')
    required.add_argument('-s', '--style', type=str,
                          help='choose type of dataset, one of [xnat|bids|other]')

    args = parser.parse_args()
    if not Path(args.dataroot).is_dir():
        raise OSError('Expected valid directory for --dataroot argument, Got {0}'.format(args.dataroot))
    output_dir = Path(args.metadataroot)
    if not output_dir.is_dir():
        if args.create:
            output_dir.mkdir(parents=True, exist_ok=True)
        else:
            raise OSError('Expected valid directory for --metadata argument. Use -c flag to create new directories automatically')
    dataset = create_dataset(args)
    return dataset


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
