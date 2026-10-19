#!/bin/bash
# Writes fragment + 3 step configs for one sample into points/<tag>/; prints the tag on the last line.
# Usage: ./make_cfgs.sh HToSSTo4b MH MS CTAU_MM  |  ./make_cfgs.sh DYto2Mu MLL_BIN
# TRACKER=1 adds the tracker hits/clusters for global muon reco; the tag then gets _trk.
# Run inside cmssw-el8 with CMSSW_13_3_0 cmsenv. EVENTS_PER_JOB must match the CRAB submit (LHE needs it).
set -e
cd "$(dirname "$0")"
here=$PWD
NEV=${EVENTS_PER_JOB:-100}
PU_LIST=$here/../condor/pu_disk_lfns.txt
XF="process.mix.mixObjects.mixSH.pcrossingFrames = cms.untracked.vstring('MuonCSCHits','MuonDTHits','MuonRPCHits','MuonGEMHits')"
# DIGI output (intermediate): pileup muon SimHit crossing frames, needed by the RECO step
XF_KEEPS="'keep *_mix_g4SimHitsMuonCSCHits_*','keep *_mix_g4SimHitsMuonDTHits_*','keep *_mix_g4SimHitsMuonRPCHits_*','keep *_mix_g4SimHitsMuonGEMHits_*'"
# RECO output = muon skim: AODSIM + muon SimHits, crossing frames, unpacked muon digis, muon local reco (as setup/skim_test_cfg.py)
SKIM_KEEPS="$XF_KEEPS,'keep *_g4SimHits_MuonCSCHits_*','keep *_g4SimHits_MuonDTHits_*','keep *_g4SimHits_MuonRPCHits_*','keep *_g4SimHits_MuonGEMHits_*'"
SKIM_KEEPS+=",'keep *_muonCSCDigis_*_*','keep *_muonDTDigis_*_*','keep *_muonRPCDigis_*_*','keep *_muonGEMDigis_*_*'"
SKIM_KEEPS+=",'keep *_csc2DRecHits_*_*','keep *_cscSegments_*_*','keep *_dt1DRecHits_*_*','keep *_dt4DSegments_*_*'"
SKIM_KEEPS+=",'keep *_rpcRecHits_*_*','keep *_gemRecHits_*_*','keep *_gemSegments_*_*'"
# TRACKER=1: tracker hits + clusters that the global muon fit refits
TRACKER_KEEPS=",'keep recoTrackExtras_generalTracks_*_*','keep TrackingRecHitsOwned_generalTracks_*_*','keep *_siPixelClusters_*_*','keep *_siStripClusters_*_*'"

# fragment goes into the release so CRAB ships it in the sandbox
read -r frag tag < <(python3 ../setup/make_fragment.py "$@" $CMSSW_BASE/src/Configuration/GenProduction/python)
[ -n "$tag" ] || exit 1
steps=GEN,SIM
[ "$1" = "DYto2Mu" ] && steps=LHE,GEN,SIM
if [ "${TRACKER:-0}" = 1 ]; then SKIM_KEEPS+=$TRACKER_KEEPS; tag=${tag}_trk; fi
mkdir -p points/$tag && cd points/$tag

# CRAB sets events, lumi and seeds of this one per job
# GEN-SIM writes skim.root too: CRAB only stages out/publishes the PSet's output file name, the RECO step overwrites it
cmsDriver.py Configuration/GenProduction/python/$frag \
  --fileout file:skim.root --mc --eventcontent RAWSIM --datatier GEN-SIM \
  --conditions 133X_mcRun3_2024_realistic_v7 --beamspot Realistic25ns13p6TeVEarly2023Collision \
  --step $steps --geometry DB:Extended --era Run3_2023 -n $NEV --nThreads 4 \
  --python_filename gensim_cfg.py --no_exec

cmsDriver.py step1 --filein file:skim.root --fileout file:digi.root \
  --pileup_input "filelist:$PU_LIST" \
  --mc --eventcontent RAWSIM --pileup 2023_LHC_Simulation_12p5h_9h_hybrid2p23 \
  --datatier GEN-SIM-RAW --conditions 133X_mcRun3_2024_realistic_v8 \
  --step DIGI,L1,DIGI2RAW,HLT:2023v12 --geometry DB:Extended --era Run3_2023 --nThreads 4 \
  -n -1 --python_filename digi_cfg.py --no_exec \
  --customise Configuration/GenProduction/setRandomSeed.py \
  --customise_commands "$XF\nprocess.RAWSIMoutput.outputCommands.extend([$XF_KEEPS])"

cmsDriver.py step1 --filein file:digi.root --fileout file:skim.root \
  --mc --eventcontent AODSIM --datatier AODSIM --conditions 133X_mcRun3_2024_realistic_v8 \
  --step RAW2DIGI,L1Reco,RECO,RECOSIM --geometry DB:Extended --era Run3_2023 --nThreads 4 \
  -n -1 --python_filename reco_cfg.py --no_exec \
  --customise_commands "process.AODSIMoutput.outputCommands.extend([$SKIM_KEEPS])"

echo "$tag"
