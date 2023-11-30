import argparse
from pathlib import Path

from MRdataset import import_dataset, save_mr_dataset, logger
from MRdataset.utils import is_writable


def get_parser():
    """Parser for MRdataset"""
    parser = argparse.ArgumentParser(
        description='MRdataset : generates dataset for analysis',
        add_help=False)
    required = parser.add_argument_group('required arguments')
    optional = parser.add_argument_group('optional arguments')

    required.add_argument('-d', '--data-source', type=str, required=True,
                          help='directory containing downloaded dataset with '
                               'dicom files, supports nested hierarchies')
    required.add_argument('--config', type=str,
                          help='path to config file')
    optional.add_argument('-o', '--output-dir', type=str,
                          help='specify the directory where the dataset would'
                               ' be saved.')
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
    return parser


def parse_args():
    """Parse command line arguments."""
    parser = get_parser()
    args = parser.parse_args()
    if not Path(args.data_source).is_dir():
        raise OSError('Expected valid directory for --data_source argument, '
                      f'Got {args.data_source}')
    if not args.config:
        THIS_DIR = Path(__file__).parent.resolve()
        args.config = THIS_DIR / 'resources/mri-config.json'
        logger.warning('Please provide a valid config file. '
                       f'Using default config file - {str(args.config)}')

    if args.output_dir:
        if not is_writable(args.output_dir):
            raise OSError('Expected a writable directory for --output_dir '
                          f'argument, Got {args.output_dir}')
    else:
        args.output_dir = Path.cwd()
        logger.warning('Please provide a valid output directory. '
                       'Got NoneType. Using current working directory.')
    return args


def cli():
    """
    The following arguments are supported:

    -d, --data-source : str
        directory containing downloaded dataset with dicom files, supports
        nested hierarchies
    --config : str
        path to config file
    -o, --output-dir : str
        specify the directory where the dataset would be saved.
    -f, --format : str
        choose type of dataset, expected one of [dicom|bids]
    -n, --name : str
        provide an identifier/name for dataset. If not provided, the name of
        the dataset will be a random string e.g. '54321'
    --is-partial : bool
        flag dataset as a partial dataset. The flag is useful while reading a
        dataset in chunks e.g. when the dataset is too large to fit in memory.
        If the dataset is complete, the flag should not be set.

    Examples
    --------
    .. code :: bash

        mrds -d /path/to/my/data/ --format dicom --name abcd_baseline
        --config mri-config.json --output-dir /path/to/my/output/dir/
    """
    args = parse_args()
    dataset = import_dataset(data_source=args.data_source,
                             ds_format=args.format,
                             name=args.name,
                             verbose=args.verbose,
                             is_complete=not args.is_partial,
                             config_path=args.config,
                             output_dir=args.output_dir)
    save_mr_dataset(f"{args.output_dir}/{dataset.name}.mrds.pkl", dataset)
    return dataset


if __name__ == '__main__':
    cli()  # pragma: no cover
