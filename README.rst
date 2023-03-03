===========
Quickstart
===========


.. image:: https://img.shields.io/pypi/v/MRdataset.svg
        :target: https://pypi.python.org/pypi/MRdataset

MRdataset
----------
* a unified interface to various neuroimaging datasets such as DICOM, BIDS and any other generic format etc
* Documentation: https://open-minds-lab.github.io/MRdataset/


API/programmatic usage
----------------------

To use MRdataset in a project. use the ``import_dataset`` with a valid folder path to a dataset of MR images (e.g. DICOM images):

.. code-block:: python

    from MRdataset import import_dataset
    
    data_root = '/home/user/datasets/ABCD'
    dataset = import_dataset(data_root=data_root,
                             style='dicom',
                             name='ABCD')

By default, the ``import_dataset`` expects a DICOM dataset. However, this can be changed using ``style`` argument. For example, use ``style='bids'`` for
importing a BIDS dataset.

The library is highly and easily **extensible**, and a developer can extend it to their own generic MRI /
neuroimaging formats by creating a custom interface for the new format e.g., for
a Generic My NeuroImaging Dataset, inherit ``MRdataset.base.Project`` in a file called
``MyNIdataset.py`` and implement the `.walk()` method after appropriate constructor `.__init()__` implementation:

.. code-block:: python

    from MRdataset import Project
    class MyNIdataset(Project):
        def __init__():
        
            # initialize and validate

         def walk():
         
            # implement the hierarchy and ways to traverse the dataset
            
            # add your logic to parse and handle edge cases etc


That's it! You would be able parse and zip through your dataset easily e.g., when interfacing with `mrQA` or similar.



Command line usage
------------------

MRdataset can also be used on the command line interface. 

For a DICOM dataset:

.. code-block:: bash

    mrds --data_root /path/to/dataset --style dicom


For a BIDS dataset:

.. code-block:: bash

    mrds --data_root /path/to/dataset --style bids
