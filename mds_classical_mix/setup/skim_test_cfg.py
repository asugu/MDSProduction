# Test of the muon skim on an existing FEVTSIM file: AODSIM + muon SimHits, crossing frames,
# unpacked muon digis and muon local reco. No sim digis, no digi-SimHit links, no RAW.
# keepTracker=True adds the generalTracks hits + tracker clusters that global muon reco refits (DY).
# cmsRun skim_test_cfg.py inputFiles=file:fevtsim.root outputFile=skim.root [keepTracker=True]
import FWCore.ParameterSet.Config as cms
from FWCore.ParameterSet.VarParsing import VarParsing
from Configuration.Eras.Era_Run3_2023_cff import Run3_2023
from Configuration.EventContent.EventContent_cff import AODSIMEventContent

opt = VarParsing('analysis')
opt.register('keepTracker', False, VarParsing.multiplicity.singleton, VarParsing.varType.bool, "keep tracker hits for global muons")
opt.parseArguments()

process = cms.Process('SKIM', Run3_2023)
process.load('Configuration.StandardSequences.Services_cff')
process.load('FWCore.MessageService.MessageLogger_cfi')
process.load('Configuration.StandardSequences.GeometryRecoDB_cff')
process.load('Configuration.StandardSequences.MagneticField_cff')
process.load('Configuration.StandardSequences.RawToDigi_cff')
process.load('Configuration.StandardSequences.FrontierConditions_GlobalTag_cff')
from Configuration.AlCa.GlobalTag import GlobalTag
process.GlobalTag = GlobalTag(process.GlobalTag, '133X_mcRun3_2024_realistic_v8', '')
process.MessageLogger.cerr.FwkReport.reportEvery = 10

process.source = cms.Source('PoolSource', fileNames=cms.untracked.vstring(opt.inputFiles))
process.maxEvents = cms.untracked.PSet(input=cms.untracked.int32(opt.maxEvents))

MUON_KEEPS = [
    # signal SimHits and pileup crossing frames
    'keep *_g4SimHits_MuonCSCHits_*', 'keep *_g4SimHits_MuonDTHits_*',
    'keep *_g4SimHits_MuonRPCHits_*', 'keep *_g4SimHits_MuonGEMHits_*',
    'keep *_mix_g4SimHitsMuonCSCHits_*', 'keep *_mix_g4SimHitsMuonDTHits_*',
    'keep *_mix_g4SimHitsMuonRPCHits_*', 'keep *_mix_g4SimHitsMuonGEMHits_*',
    # digis unpacked from RAW (what data has)
    'keep *_muonCSCDigis_*_*', 'keep *_muonDTDigis_*_*', 'keep *_muonRPCDigis_*_*', 'keep *_muonGEMDigis_*_*',
    # muon local reco
    'keep *_csc2DRecHits_*_*', 'keep *_cscSegments_*_*', 'keep *_dt1DRecHits_*_*', 'keep *_dt4DSegments_*_*',
    'keep *_rpcRecHits_*_*', 'keep *_gemRecHits_*_*', 'keep *_gemSegments_*_*',
]
TRACKER_KEEPS = [
    'keep recoTrackExtras_generalTracks_*_*', 'keep TrackingRecHitsOwned_generalTracks_*_*',
    'keep *_siPixelClusters_*_*', 'keep *_siStripClusters_*_*',
]
process.out = cms.OutputModule('PoolOutputModule',
    fileName=cms.untracked.string(opt.outputFile),
    outputCommands=cms.untracked.vstring(AODSIMEventContent.outputCommands + MUON_KEEPS
                                         + (TRACKER_KEEPS if opt.keepTracker else [])),
    compressionAlgorithm=cms.untracked.string('LZMA'),
    compressionLevel=cms.untracked.int32(4),
)
process.p = cms.Path(process.muonCSCDigis + process.muonDTDigis + process.muonRPCDigis + process.muonGEMDigis)
process.e = cms.EndPath(process.out)
