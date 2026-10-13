#!/bin/bash
# Sets up CMSSW_13_3_0 (el8) with the fragments, seed customise and LLP filter. Run inside cmssw-el8.
set -e
repo=/data/dust/user/guvenlia/production/mds_classical_mix
source /cvmfs/cms.cern.ch/cmsset_default.sh
export SCRAM_ARCH=el8_amd64_gcc12
cd /data/dust/user/guvenlia/cmssw
[ -d CMSSW_13_3_0 ] || cmsrel CMSSW_13_3_0
cd CMSSW_13_3_0/src && eval $(scramv1 runtime -sh)

cp -r $repo/cmssw_src/* .
cp $repo/fragments/original_ggH_HToSSTo4b_fragment.py Configuration/GenProduction/python/ggH_HToSSTo4b_test.py
cp $repo/fragments/ggH_HToSSTo4b_LLPfilter.py Configuration/GenProduction/python/
scram b -j4 2>&1 | tail -3

python3 -c "import Configuration.GenProduction.ggH_HToSSTo4b_LLPfilter as f; print('fragment OK:', f.LLPDecayInDTorCSCFilter.type_())"
