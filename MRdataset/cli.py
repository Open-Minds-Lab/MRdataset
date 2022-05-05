"""Console script for MRdataset."""
import argparse
import sys


def main():
    """Console script for MRdataset."""
    parser = argparse.ArgumentParser()
    parser.add_argument('_', nargs='*')
    args = parser.parse_args()

    print("Arguments: " + str(args._))
    print("Replace this message by putting your code into "
          "MRdataset.cli.main")
    return 0


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover


    from MRdataset import XnatDataset

    ds = XnatDataset(path='/project/harsh/mrrc')

    params = dict()
    for project in ds.projects():
        params[project] = dict()
        for subj in ds.projects[project]:

            params[project][subj] = dict()
            for sess in ds.projects[project][subj]:
                params[project][subj][sess] = DicomParser(
                    ds.path[project, subj, sess])


    #
