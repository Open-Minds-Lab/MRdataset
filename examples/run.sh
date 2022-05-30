#!/usr/bin/env bash

# INPUT_DIR="/media/harsh/My Passport/MRI_Datasets/sinhah-20220514_140054/"
# OUTPUT_DIR="/home/harsh/PycharmProjects/MRdataset/MRdataset/resources/"
# python /home/harsh/PycharmProjects/MRdataset/MRdataset/cli.py --dataroot "$INPUT_DIR" --metadataroot "$OUTPUT_DIR" --style xnat --name mind

# INPUT_DIR="/media/harsh/My Passport/MRI_Datasets/sinhah-20220520_153204/"
# OUTPUT_DIR="/home/harsh/PycharmProjects/MRdataset/MRdataset/resources/"
# python /home/harsh/PycharmProjects/MRdataset/MRdataset/cli.py --dataroot "$INPUT_DIR" --metadataroot "$OUTPUT_DIR" --style xnat --name scan --verbose

 INPUT_DIR="/media/harsh/My Passport/MRI_Datasets/sinhah-20220520_201328/"
 OUTPUT_DIR="/home/harsh/My Passport/MRI_Datasets/metadata/"
 python /home/harsh/PycharmProjects/MRdataset/MRdataset/cli.py --dataroot "$INPUT_DIR" --metadataroot "$OUTPUT_DIR" --style xnat --name cha_mjff --verbose -c

#INPUT_DIR="/media/harsh/My Passport/MRI_Datasets/sinhah-20220520_210659/"
#OUTPUT_DIR="/home/harsh/PycharmProjects/MRdataset/MRdataset/resources/"
#python /home/harsh/PycharmProjects/MRdataset/MRdataset/cli.py --dataroot "$INPUT_DIR" --metadataroot "$OUTPUT_DIR" --style xnat --name adrc_nic --verbose
