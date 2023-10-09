#!/bin/bash

make clean
make html
cp -r build/html/* ../../MRdataset-gh-pages/
