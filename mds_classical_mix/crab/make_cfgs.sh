#!/bin/bash
# Writes fragment + 3 step configs for one point into points/<tag>/. Run inside cmssw-el8 with CMSSW_13_3_0 cmsenv.
# Usage: ./make_cfgs.sh MH MS CTAU_MM
set -e
[ $# -eq 3 ] || { echo "usage: $0 MH MS CTAU_MM"; exit 1; }
cd "$(dirname "$0")"
here=$PWD
PU_LIST=$here/../condor/pu_disk_lfns.txt
XF="process.mix.mixObjects.mixSH.pcrossingFrames = cms.untracked.vstring('MuonCSCHits','MuonDTHits')"
KEEPS="['keep *_mix_g4SimHitsMuonCSCHits_*','keep *_mix_g4SimHitsMuonDTHits_*','keep *_simMuonDTDigis_*_*']"

# fragment goes into the release so CRAB ships it in the sandbox
frag=$(python3 ../setup/make_fragment.py $1 $2 $3 $CMSSW_BASE/src/Configuration/GenProduction/python)
tag=${frag#ggH_HToSSTo4b_}; tag=${tag%.py}
mkdir -p points/$tag && cd points/$tag

# CRAB sets events, lumi and seeds of this one per job
cmsDriver.py Configuration/GenProduction/python/$frag \
  --fileout file:gensim.root --mc --eventcontent RAWSIM --datatier GEN-SIM \
  --conditions 133X_mcRun3_2024_realistic_v7 --beamspot Realistic25ns13p6TeVEarly2023Collision \
  --step GEN,SIM --geometry DB:Extended --era Run3_2023 -n 100 --nThreads 4 \
  --python_filename gensim_cfg.py --no_exec

cmsDriver.py step1 --filein file:gensim.root --fileout file:digi.root \
  --pileup_input "filelist:$PU_LIST" \
  --mc --eventcontent RAWSIM --pileup 2023_LHC_Simulation_12p5h_9h_hybrid2p23 \
  --datatier GEN-SIM-RAW --conditions 133X_mcRun3_2024_realistic_v8 \
  --step DIGI,L1,DIGI2RAW,HLT:2023v12 --geometry DB:Extended --era Run3_2023 --nThreads 4 \
  -n -1 --python_filename digi_cfg.py --no_exec \
  --customise Configuration/GenProduction/setRandomSeed.py \
  --customise_commands "$XF\nprocess.RAWSIMoutput.outputCommands.extend($KEEPS)"

cmsDriver.py step1 --filein file:digi.root --fileout file:fevtsim.root \
  --mc --eventcontent FEVTSIM --datatier GEN-SIM-RECO --conditions 133X_mcRun3_2024_realistic_v8 \
  --step RAW2DIGI,L1Reco,RECO,RECOSIM --geometry DB:Extended --era Run3_2023 --nThreads 4 \
  -n -1 --python_filename reco_cfg.py --no_exec \
  --customise_commands "process.FEVTSIMoutput.outputCommands.extend($KEEPS)"

echo "$tag"
