API usage
----------------------
.. The following section provides a brief overview of the API. For more details,
.. please refer to the Jupyter Notebook `tutorial`_.

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
                             ds_format='dicom')

By default, the ``import_dataset`` expects a DICOM dataset. However, this can
be changed using ``ds_format`` argument. For example, use ``ds_format='bids'`` for
importing a BIDS dataset.

We follow a hierarchical structure in our dataset as shown above. And we provide methods for
accessing each of these elements. These access-methods are ``traverse_horizontal``
and ``traverse_vertical2``. For example, we can traverse through all the subjects for a given sequence
using ``traverse_horizontal`` method.

.. code:: python

    seq_name = '3D_T2_FLAIR'
    for subject, session, run, sequence in dicom_dataset.traverse_horizontal(seq_name):
        print(f"Subject: {subject},\nSession: {session},\nRun: {run},\nSequence: {sequence}")

Similarly, we can traverse through all the sequences/modality for
a given subject using `traverse_vertical2` method. It is helpful for retrieving epi and
corresponding fieldmaps for a given subject. Let's see an example.

.. code:: python

    seq_id1 = 'me_fMRI'
    seq_id2 = 'me_FieldMap_GRE'

    for subject, session, run1, run2, seq1, seq2 in dicom_dataset.traverse_vertical2(seq_id1, seq_id2):
        print(seq1)
        print(seq2)
        break

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



.. _tutorial: https://nbviewer.org/github/Open-Minds-Lab/MRdataset/blob/parallel/docs/usage.ipynb
