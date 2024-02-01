.. highlight:: shell

============
Installation
============


Stable release
--------------

To install MRdataset, run this command in your terminal:

.. code-block:: console

    $ pip install -U MRdataset


If you don't have `pip`_ installed, this `Python installation guide`_ can guide
you through the process.

.. _pip: https://pip.pypa.io
.. _Python installation guide: http://docs.python-guide.org/en/latest/starting/installation/


From sources
------------

The sources for MRdataset can be downloaded from the `Github repo`_.

You can clone the public repository:

.. code-block:: console

    $ git clone git://github.com/Open-Minds-Lab/MRdataset

Once you have a copy of the source, you can install it with:

.. code-block:: console

    $ python -m pip install --upgrade pip
    $ cd MRdataset/
    $ if [ -f requirements_dev.txt ]; then pip install -r requirements_dev.txt; fi
    $ pip install .


.. _Github repo: https://github.com/Open-Minds-Lab/MRdataset
.. _tarball: https://github.com/Open-Minds-Lab/MRdataset/tarball/master
