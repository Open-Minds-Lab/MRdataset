#!/usr/bin/env python

"""The setup script."""

from setuptools import setup, find_packages

import versioneer

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = [
    'dicom2nifti>=2.4.2',
    'nibabel',
    'pydicom',
    'dictdiffer',
    'pandas',
    'pybids'
]

test_requirements = ['pytest>=3', ]

setup(
    author="Pradeep Raamana",
    author_email='raamana@gmail.com',
    python_requires='>=3.6',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    description="MRdataset",
    entry_points={
        'console_scripts': [
            'mrdataset=MRdataset.cli:main',
            'mrds=MRdataset.cli:main'
        ],
    },
    install_requires=requirements,
    license="Apache Software License 2.0",
    long_description=readme + '\n\n' + history,
    include_package_data=True,
    keywords='MRdataset',
    name='MRdataset',
    packages=find_packages(include=['MRdataset', 'MRdataset.*']),
    test_suite='tests',
    tests_require=test_requirements,
    url='https://github.com/Open-Minds-Lab/MRdataset',
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    zip_safe=False,
)
