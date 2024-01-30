API Reference
=================

The page holds MRdataset's API documentation, which might be helpful for users or
developers to create interface with their own neuroimaging datasets. Among the
different sub-packages and modules, there are two categories: core API and
high-level API. The core api contains modules for important elements (e.g.
BaseDataset).

High level API
------------------------------
The high-level API contains functions that are useful for
importing datasets from disk. After importing these objects can be saved/reloaded as
pickle files.

.. automodule:: MRdataset.common
   :members:
   :undoc-members:
   :show-inheritance:
   :exclude-members: find_dataset_using_ds_format


Core API
---------------------
The Core API contains modules for important elements (e.g. Modality,
Subject, Run etc.in a neuroimaging experiment.

.. automodule:: MRdataset.dicom
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: MRdataset.bids
   :members:
   :undoc-members:
   :show-inheritance:


.. automodule:: MRdataset.base
   :members:
   :undoc-members:
   :show-inheritance:

