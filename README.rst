=====================================================================
MRdataset : unified interface to various neuroimaging dataset formats
=====================================================================

.. image:: https://img.shields.io/pypi/v/MRdataset.svg
        :target: https://pypi.python.org/pypi/MRdataset

.. image:: https://app.codacy.com/project/badge/Grade/4e6e129acb3340e3b422541be3924a90
        :target: https://app.codacy.com/gh/sinhaharsh/MRdataset/dashboard?utm_source=gh&utm_medium=referral&utm_content=&utm_campaign=Badge_grade

.. image:: https://github.com/sinhaharsh/MRdataset/actions/workflows/continuous-integration.yml/badge.svg
        :target: https://github.com/sinhaharsh/MRdataset/actions/workflows/continuous-integration.yml


.. image:: ./docs/images/hierarchy.jpg

Description
------------

* Provides a unified interface for horizontal and vertical traversal of various neuroimaging datasets (DICOM) and any other generic format etc.
* Ensures that the DICOM files are valid imaging DICOMs and provides the option to skip phantoms, localizer, head scouts etc.
* Provides flexibility to ignore automatically generated derived scans such as MoCo series, Single-band references, perfusion weighted scans.
* Verifies if each DICOM slice belongs to the same scan volume and, then subsequently organizes all scans are hierarchical fashion (Subject > Session > Sequence > Run)
* Identifies sequences acquired within the same session, which is especially useful for associating field maps with their corresponding functional (EPI) scans.


Documentation 
-------------

https://open-minds-lab.github.io/MRdataset/



