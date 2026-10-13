#!/bin/bash
# GEN-SIM (LLP filter) -> DIGI (classical mixing) -> RECO (FEVTSIM), CMSSW_13_3_0, inside cmssw-el8.
# Called by run_chain.sh; inputs come as env vars: JOB_ID NGEN WORKDIR FRAGMENT PU_LIST LUMI
set -e
set -x
source /cvmfs/cms.cern.ch/cmsset_default.sh
cd /data/dust/user/guvenlia/cmssw/CMSSW_13_3_0/src && eval "$(scramv1 runtime -sh)"
cd "$WORKDIR"

# same keep lists as the validated 10-event test (CSC + DT crossing frames, DT digis)
XF="process.mix.mixObjects.mixSH.pcrossingFrames = cms.untracked.vstring('MuonCSCHits','MuonDTHits')"
KEEPS="['keep *_mix_g4SimHitsMuonCSCHits_*','keep *_mix_g4SimHitsMuonDTHits_*','keep *_simMuonDTDigis_*_*']"

# 1. GEN-SIM; unique lumi per job keeps run/lumi/event unique
cmsDriver.py Configuration/GenProduction/python/$FRAGMENT \
  --fileout file:gensim.root --mc --eventcontent RAWSIM --datatier GEN-SIM \
  --conditions 133X_mcRun3_2024_realistic_v7 --beamspot Realistic25ns13p6TeVEarly2023Collision \
  --step GEN,SIM --geometry DB:Extended --era Run3_2023 -n $NGEN \
  --python_filename gensim_cfg.py --no_exec \
  --customise Configuration/GenProduction/setRandomSeed.py \
  --customise_commands "process.source.firstLuminosityBlock = cms.untracked.uint32($LUMI)"
cmsRun -j gensim_fjr.xml gensim_cfg.py > gensim.log 2>&1

# 2. DIGI with classical mixing (pileup read via /store names -> site fallback)
cmsDriver.py step1 --filein file:gensim.root --fileout file:digi.root \
  --pileup_input "filelist:$PU_LIST" \
  --mc --eventcontent RAWSIM --pileup 2023_LHC_Simulation_12p5h_9h_hybrid2p23 \
  --datatier GEN-SIM-RAW --conditions 133X_mcRun3_2024_realistic_v8 \
  --step DIGI,L1,DIGI2RAW,HLT:2023v12 --geometry DB:Extended --era Run3_2023 --nThreads 4 \
  -n -1 --python_filename digi_cfg.py --no_exec \
  --customise Configuration/GenProduction/setRandomSeed.py \
  --customise_commands "$XF\nprocess.RAWSIMoutput.outputCommands.extend($KEEPS)\nprocess.options.wantSummary = True"
cmsRun -j digi_fjr.xml digi_cfg.py > digi.log 2>&1
rm -f gensim.root

# 3. RECO -> FEVTSIM (SimHits + crossing frames + DT digis kept)
cmsDriver.py step1 --filein file:digi.root --fileout file:fevtsim.root \
  --mc --eventcontent FEVTSIM --datatier GEN-SIM-RECO --conditions 133X_mcRun3_2024_realistic_v8 \
  --step RAW2DIGI,L1Reco,RECO,RECOSIM --geometry DB:Extended --era Run3_2023 --nThreads 4 \
  -n -1 --python_filename reco_cfg.py --no_exec \
  --customise_commands "process.FEVTSIMoutput.outputCommands.extend($KEEPS)\nprocess.options.wantSummary = True"
cmsRun -j reco_fjr.xml reco_cfg.py > reco.log 2>&1
rm -f digi.root
