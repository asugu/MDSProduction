#!/bin/bash
# CRAB scriptExe: GEN-SIM (PSet.py = gensim_cfg.py as tweaked by CRAB) -> DIGI -> RECO.
set -e
cmsRun -j gensim_fjr.xml -p PSet.py
cmsRun -j digi_fjr.xml digi_cfg.py
rm -f gensim.root
# CRAB reads FrameworkJobReport.xml, so the last step writes it
cmsRun -j FrameworkJobReport.xml reco_cfg.py
rm -f digi.root
