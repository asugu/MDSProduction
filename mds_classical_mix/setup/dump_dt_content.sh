#!/bin/bash
source /cvmfs/cms.cern.ch/cmsset_default.sh
cd /data/dust/user/guvenlia/cmssw/CMSSW_13_3_0/src && eval $(scramv1 runtime -sh)
edmDumpEventContent /data/dust/user/guvenlia/production/mds_classical_mix/test/test_fevtsim.root | grep -iE "DT|MuonDTHits"
