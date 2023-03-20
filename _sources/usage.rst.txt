Command line usage
------------------

MRdataset can be used on the command line interface. For a DICOM dataset::

    mrds --data-source /path/to/dataset --format dicom

For a BIDS dataset::

    mrds --data-source /path/to/dataset --format bids


API usage
----------------------
The following section provides a brief overview of the API. For more details,
please refer to the Jupyter Notebook `tutorial`_.

To use MRdataset in a project::

    import MRdataset

The most important method is ``import_dataset``. The dataset type
such as ``dicom`` or ``bids`` can be specified using the ``ds_format`` argument.

First of all, you have to import the relevant module::

    from MRdataset import import_dataset

Given a valid folder path to a dataset of MR images (e.g. DICOM images),
it creates a dataset.::

    data_folder = '/home/user/datasets/ABCD'
    dataset = import_dataset(data_source=data_folder,
                             ds_format='dicom',
                             name='ABCD')

By default, the ``import_dataset`` expects a DICOM dataset. However, this can
be changed using ``ds_format`` argument. For example, use ``ds_format='bids'`` for
importing a BIDS dataset.

The library is highly extensible, and a developer can extend it to their own
neuroimaging formats. For example, to create an interface with a new format, say
NID (NeuroImaging Dataset), inherit ``MRdataset.base.BaseDataset`` in a file
``NID_dataset.py``::

    from MRdataset.base import BaseDataset
    class NIDDataset(BaseDataset):
        def __init__(data_source):
            super().init(data_source)
            pass

         def walk():
            pass

Finally, ``save_mr_dataset`` and ``load_mr_dataset`` can be used to save and load a
dataset. For example, to save a dataset::

    from MRdataset import save_mr_dataset
    save_mr_dataset(dataset, '/home/user/datasets/xyz.mrds.pkl')


Similarly, to load a dataset::

    from MRdataset import load_mr_dataset
    dataset = load_mr_dataset('/home/user/datasets/xyz.mrds.pkl')

Note that the dataset is saved as a pickle file with an extension ``.mrds.pkl``.

.. _tutorial: https://nbviewer.org/github/Open-Minds-Lab/MRdataset/blob/parallel/docs/usage.ipynb

