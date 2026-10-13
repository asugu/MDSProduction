#!/bin/bash
source /cvmfs/cms.cern.ch/cmsset_default.sh
cd /data/dust/user/guvenlia/cmssw/CMSSW_13_3_0/src && eval $(scramv1 runtime -sh)
cd /data/dust/user/guvenlia/production/mds_classical_mix/test
echo "== crossing frame / simhit products in test_digi.root"
edmDumpEventContent test_digi.root | grep -iE "PCrossingFrame|g4SimHitsMuonCSCHits|MuonCSCHits"
echo "== LLP decays in test_gensim.root"
python3 ../setup/check_test_outputs.py test_gensim.root 2>&1 | grep -v Warning
