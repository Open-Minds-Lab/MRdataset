API usage
----------------------
The following section provides a brief overview of the API. For more details,
please refer to the Jupyter Notebook `tutorial`_.

To use MRdataset in a project -

.. code:: python

    import MRdataset

The most important method is ``import_dataset``. The dataset type
such as ``dicom`` or ``bids`` can be specified using the ``ds_format`` argument.

First of all, you have to import the relevant module

.. code:: python

    from MRdataset import import_dataset

Given a valid folder path to a dataset of MR images (e.g. DICOM images),
it creates a dataset.

.. code:: python

    data_folder = '/home/user/datasets/XYZ'
    dataset = import_dataset(data_source=data_folder,
                             ds_format='dicom',
                             config_file='mri_config.json',
                             output_dir='/home/user/datasets/XYZ',

By default, the ``import_dataset`` expects a DICOM dataset. However, this can
be changed using ``ds_format`` argument. For example, use ``ds_format='bids'`` for
importing a BIDS dataset.

The library is highly extensible, and a developer can extend it to their own
neuroimaging formats. For example, to create an interface with a new format, say
NID (NeuroImaging Dataset), inherit ``MRdataset.base.BaseDataset`` in a file
``NID_dataset.py``

.. code:: python

    from MRdataset.base import BaseDataset
    class NIDDataset(BaseDataset):
        def __init__(data_source):
            super().init(data_source)
            pass

         def load():
            pass

Finally, ``save_mr_dataset`` and ``load_mr_dataset`` can be used to save and load a
dataset. For example, to save a dataset

.. code:: python

    from MRdataset import save_mr_dataset
    save_mr_dataset(dataset, '/home/user/datasets/xyz.mrds.pkl')


Similarly, to load a dataset

.. code:: python

    from MRdataset import load_mr_dataset
    dataset = load_mr_dataset('/home/user/datasets/xyz.mrds.pkl')

Note that the dataset is saved as a pickle file with an extension ``.mrds.pkl``.

Command line usage
------------------

MRdataset can be used on the command line interface. For a DICOM dataset

.. code:: bash

    mrds --data-source /path/to/dataset --format dicom

For a BIDS dataset

.. code:: bash

    mrds --data-source /path/to/dataset --format bids

.. automodule:: MRdataset.cli
   :members:
   :undoc-members:
   :show-inheritance:
   :exclude-members: get_parser, parse_args
   :noindex:


Configuration file
------------------

The configuration file is a JSON file that contains the following keys. The
values of these keys are used to include or exclude certain scans from the
dataset.

* **begin**: The scans acquired before this date are
  excluded from the dataset. This is a string in the format ``YYYY-MM-DD``.
  For example, ``2019-01-01``.
* **end**: The scans acquired after this date are
  excluded from the dataset. This is a string in the format ``YYYY-MM-DD``.
  For example, ``2019-01-01``.
* **include_sequences**: The user can choose to skip phantoms, localizers, motion-correction
  scans (moco), derived sequences (perfusion-weighted) and single-band references (sbref)
  by setting the values for ``phantom``, ``moco`` and ``sbref`` as ``false``.
* **use_echonumbers**: In general (for Siemens) multi-echo sequences can be identified by
  the presence of ``EchoNumber`` in the DICOM header. However, this is not always the case.
  Then, the folder is scanned for the presence of multiple echo times. In the future, we
  plan to add support for GE and Philips scanners.
* **include_parameters**: The user can choose to include or exclude certain parameters
  from the dataset. For example, ``include_parameters: ['RepetitionTime', 'EchoTime']``.
  Note that the parameters are case-sensitive. They should be specified in camel-case. A
  complete list of parameters can be found `here`_.
* **exclude_subjects**: The scans from the subjects in this list are excluded
  from the dataset. This is a list of strings. For example, ``['sub-01', 'sub-02']``.

.. literalinclude:: ../examples/mri-config.json
   :language: json
   :linenos:


.. _tutorial: https://nbviewer.org/github/Open-Minds-Lab/MRdataset/blob/parallel/docs/usage.ipynb
.. _here: config.html
