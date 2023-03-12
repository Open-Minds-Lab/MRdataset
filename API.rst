API Reference
=================

The page holds MRdataset's API documentation, which might be helpful for users or
developers to create interface with their own neuroimaging datasets. Among the
different sub-packages and modules, there are two categories: core utilities and
high-level modules

High level API
------------------------------
The high level API of MRdataset shows how to interface with neuroimaging datasets
using the elements in Core API. Here is a summarized reference of classes
which can be used to import BIDS dataset and DICOM dataset.

.. automodule:: MRdataset.dicom
   :members:
   :undoc-members:
   :show-inheritance:


.. automodule:: MRdataset.naive_bids
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: MRdataset.fastbids
   :members:
   :undoc-members:
   :show-inheritance:



Core API
---------------------
The Core API contains modules for important elements (e.g. Modality,
Subject, Run etc.in a neuroimaging experiment.

.. automodule:: MRdataset.base
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: MRdataset.common
   :members:
   :undoc-members:
   :show-inheritance:
