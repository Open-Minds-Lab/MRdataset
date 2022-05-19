from nibabel.nicom import csareader
import pydicom
import warnings
from MRdataset.experimental import tags
from MRdataset.experimental import node


class DicomNode(node.Node):
    def __init__(self, filepath):
        super().__init__()
        self.filepath = filepath
        self.populate()
        del self.dicom
        del self.csaprops

    def populate(self):
        self._read()
        self.set_property()
        self._csa_parser()
        self._adhoc_property()
        self._get_phase_encoding()

    def _read(self):
        try:
            self.dicom = pydicom.dcmread(self.filepath)
        except OSError:
            print("Unable to read dicom file from disk.{0}".format(self.filepath))

    def get_value(self, name):
        data = self.dicom.get(tags.PARAMETER_TAGS[name], None)
        if data:
            return data.value
        return None

    def _get_header(self, name):
        data = self.dicom.get(tags.HEADER_TAGS[name], None)
        if data:
            return data.value
        return None

    def get_property(self, name):
        """abstract method to retrieve a specific dicom property"""
        value = self.fparams.get(name, None)
        if value:
            return value
        else:
            warnings.warn(
                '{0} parameter at tag {1} does not exit in this DICOM file'.format(
                    name,
                    tags.PARAMETER_TAGS[name]
                )
            )
            return None

    def set_property(self):
        for k in tags.PARAMETER_TAGS.keys():
            self.fparams[k] = self.get_value(k)

    def _csa_parser(self):
        self.image_header = csareader.read(self._get_header('ImageHeaderInfo'))
        self.series_header = csareader.read(self._get_header('SeriesHeaderInfo'))
        text = self.series_header['tags']['MrPhoenixProtocol']['items'][0].split("\n")
        start = False
        end = False
        props = {}
        for e in text:
            if e[:15] == '### ASCCONV END':
                end = True
            if start and not end:
                ele = e.split()
                if ele[1].strip() == "=":
                    props[ele[0]] = ele[2]
            if e[:17] == '### ASCCONV BEGIN':
                start = True
        self.csaprops = props
        return

    def _adhoc_property(self):
        self.fparams["MultiBandComment"] = self.fparams["Comments"]
        so = str(eval(self.csaprops["sKSpace.ucMultiSliceMode"]))
        self.fparams["SliceOrder"] = tags.SODict[so]
        if self.fparams["EchoTrainLength"] > 1:
            check = (self.fparams["EchoTrainLength"] == self.fparams["PhaseEncodingLines"])
            if not check:
                print("PhaseEncodingLines is not equal to EchoTrainLength : {0}".format(self.filepath))
        try:
            self.fparams['EffectiveEchoSpacing'] = 1000 / (
                    self.fparams['BandwidthPerPixelPhaseEncode'] * self.fparams["PhaseEncodingLines"])
        except Exception as e:
            if self.verbose:
                if self.fparams['PhaseEncodingLines'] is None:
                    warnings.warn('PhaseEncodingLines is None')
                else:
                    warnings.warn("Could not calculate EffectiveEchoSpacing : ")
            self.fparams['EffectiveEchoSpacing'] = None
        # three modes: warm-up, standard, advanced
        self.fparams["iPAT"] = self.csaprops.get("sPat.lAccelFactPE", None)
        self.fparams["ShimMethod"] = self.csaprops["sAdjData.uiAdjShimMode"]
        self.fparams["is3D"] = self.fparams["MRAcquisitionType"] == '3D'

    def _get_phase_encoding(self, isFlipY=True):
        """
        https://github.com/rordenlab/dcm2niix/blob/23d087566a22edd4f50e4afe829143cb8f6e6720/console/nii_dicom_batch.cpp
        """
        is_skip = False
        if self.fparams['is3D']:
            is_skip = True
        if self.fparams['EchoTrainLength'] > 1:
            is_skip = False
        phPos = self.image_header["tags"]['PhaseEncodingDirectionPositive']['items'].pop()
        ped_dcm = self.get_value("PedDCM")
        ped = ""
        assert ped_dcm in ["COL", "ROW"]
        if not is_skip and ped_dcm == "COL":
            ped = "j"
        elif not is_skip and ped_dcm == "ROW":
            ped = "i"
        if phPos >= 0 and not is_skip:
            if phPos == 0 and ped_dcm == 'ROW':
                ped += "-"
            elif ped_dcm == "COL" and phPos == 1 and isFlipY:
                ped += "-"
            elif ped_dcm == "COL" and phPos == 0 and not isFlipY:
                ped += "-"
            pedDict = {'i': 'Left-Right', 'i-': 'Right-Left',
                       'j-': 'Anterior-Posterior', 'j': 'Posterior-Anterior'}
            self.fparams["PhaseEncodingDirection"] = pedDict[ped]
        else:
            self.fparams["PhaseEncodingDirection"] = None

    def __str__(self):
        return self.fparams


if __name__ == "__main__":
    filepath = "/media/harsh/My Passport/MRI_Datasets/sinhah-20220514_140054/MIND016/scans/10-gre_field_mapping/resources/DICOM/1.3.12.2.1107.5.2.43.67078.30000019082010561171200000019-10-1-13j6l3y.dcm"
    l = DicomNode(filepath)
    print(l.fparams)
