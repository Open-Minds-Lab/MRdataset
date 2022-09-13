===========
Quickstart
===========


.. image:: https://img.shields.io/pypi/v/MRdataset.svg
        :target: https://pypi.python.org/pypi/MRdataset

MRdataset
----------
* a unified interface to various neuroimaging datasets such as DICOM, BIDS and any other generic format etc
* Documentation: https://open-minds-lab.github.io/MRdataset/

CLI usage
----------
MRdataset can be used on the command line interface. For a DICOM dataset::

    mrds --data_root /path/to/dataset --style xnat

For a BIDS dataset::

    mrds --data_root /path/to/dataset --style bids

Python usage
------------
To use MRdataset in a project::

    import MRdataset

The most important method is ``import_dataset``. It
creates an appropriate object depending as per ``style`` argument.

First of all, you have to import the relevant module::

    from MRdataset import import_dataset

Given a valid folder path to a dataset of MR images (e.g. DICOM images),
it creates a ``MRdataset.base.Project`` object.::

    data_root = '/home/user/datasets/ABCD'
    dataset = import_dataset(data_root=data_root,
                             style='xnat',
                             name='ABCD')

By default, the ``import_dataset`` expects a DICOM dataset. However, this can
be changed using ``style`` argument. For example, use ``style='bids'`` for
importing a BIDS dataset.

The library is highly extensible, and a developer can extend it to their own
neuroimaging formats. For example, to create an interface with a new format, say
NID (NeuroImaging Dataset), inherit ``MRdataset.base.Project`` in a file
``NID_dataset.py``::

    from MRdataset import Project
    class NIDDataset(Project):
        def __init__():
            pass

         def walk():
            pass


Implement, these two functions. You can directly use ``style='nid'``. Thats it!
No more changes required.



