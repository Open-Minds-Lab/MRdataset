#!/bin/bash
cd docs
make clean && make html
cp -r build/html/* ../../MRdataset-gh-pages/
cd ../../MRdataset-gh-pages/
git add .
git commit -m "Update docs"
git push

