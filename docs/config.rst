=============
Configuration
=============


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
  complete list of parameters can be found here.
* **exclude_subjects**: The scans from the subjects in this list are excluded
  from the dataset. This is a list of strings. For example, ``['sub-01', 'sub-02']``.

.. literalinclude:: mri-config.json
   :language: json
   :linenos:


.. automodule:: MRdataset.config
   :members:
   :undoc-members:
   :show-inheritance:
   :exclude-members: DatasetEmptyException, MRException, MRdatasetWarning, configure_logger

