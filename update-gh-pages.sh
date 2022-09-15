#!/bin/bash
cd docs
make clean
make html
cp -r * ../../MRdataset-gh-pages/
cd ../../MRdataset-gh-pages/
git add .
git commit -m "Update docs"
git push

