from pathlib import Path

from MRdataset.dicom import DicomDataset

base_dir = Path('/media/sinhah/extremessd/ABCD/active_series/non-recommended/vertical_subset/dicom')
ds_name = 'vertical_subset_ABCD'  # 'ABCD'  # 'wpc7888'  #  'test_data'
dcm_root = base_dir / ds_name

# dcm_root = Path('/Users/Reddy/Downloads/dicom/wpc7888/2023.01.19-14.16.55/50250')

ds = DicomDataset(data_source=base_dir, pattern='*', name=ds_name, config_path='/home/sinhah/github/mrQA/examples/mri-config-full.json')
ds.load()

# {'ABCD-T1,_GE,_original_(baseline_year_1_arm_1)',
#  'ABCD-T1,_PHILIPS,_original_(baseline_year_1_arm_1)',
#  'tfl3d1_16ns'}

# s1 = 'tfl3d1_16ns'
# s2 = 'ABCD-T1,_GE,_original_(baseline_year_1_arm_1)'

# s1 = 'ABCD-DTI,_GE,_original_(baseline_year_1_arm_1)'
# s2 = 'ABCD-Diffusion-FM,_GE,_original_(baseline_year_1_arm_1)'


s1 = 'ABCD-Diffusion-FM-AP,_SIEMENS,_original_(baseline_year_1_arm_1)'
s2 = 'ABCD-Diffusion-FM-PA,_SIEMENS,_original_(baseline_year_1_arm_1)'

# s1 = 'ABCD-T1,_SIEMENS,_original_(baseline_year_1_arm_1)'
# s2 = 'ABCD-T1-NORM,_SIEMENS,_original_(baseline_year_1_arm_1)'

# s1 = 'SpinEchoFieldMap_AP_2mm'  # 'gre_FieldMap'  # 'T1_MPRAGE_Iso'  #
# s2 = 'reward_1'  # 'resting-state'
#
# s1 = 'gre_FieldMap'
# # s2 = 'diff_dir105_MB4_PA_copy_diff_35_PE_is_PA_straight_no_angle'
# s2 = 'diff_dir70_MB4_AP_copy_from_prior_diff_35_scan_PE_IS_AP_no_angle'

# s1 = 'reward_1'
# s2 = 'reward_2'

for subj, sess, r1, r2, seq1, seq2 in ds.traverse_vertical2(s1, s2):
    print(f'\n{subj} {sess:3} \n\t{str(seq1):>120} \n\t{str(seq2):>120}')

three_seqs = ['ABCD-DTI,_SIEMENS,_mosaic,_original_(baseline_year_1_arm_1)',
              'ABCD-Diffusion-FM-PA,_SIEMENS,_original_(baseline_year_1_arm_1)',
              'ABCD-Diffusion-FM-AP,_SIEMENS,_original_(baseline_year_1_arm_1)']

for subj, sess, runs, seqs in ds.traverse_vertical_multi(*three_seqs):
    print(f'\n{subj} {sess:3}')
    for rr, ss in zip(runs, seqs):
        print(f'\t{str(ss):>120}\t{rr}')


for seq in ds._seq_ids:
    print(f'\n{seq}')
    for subj, sess, run, seq in ds.traverse_horizontal(seq):
        print(f'\t {subj} {sess} {run}')


print('')

