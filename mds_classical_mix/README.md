# MDS classical-mixing sample production

Private Run 3 MC for MDS ML studies, made with **classical pileup mixing** so that the
pileup SimHits are kept (premixing throws them away). Output is a "muon skim" (see [Output](#output-the-muon-skim)).
Ntupling is not part of this repo.

Samples:
- signal: ggH → SS → 4b / 4d / 4τ with a long-lived S, mass and cτ configurable, LLP filter
- background: DY → 2μ, Powheg 2024 gridpacks in MLL bins (no filter yet)

## Recipe

TSG Run3Winter24 chain, all steps in **CMSSW_13_3_0 (el8, run inside `cmssw-el8`)**, era `Run3_2023`.

| step | conditions | notes |
|---|---|---|
| GEN-SIM | `133X_mcRun3_2024_realistic_v7` | LLP filter in `ProductionFilterSequence` |
| DIGI,L1,DIGI2RAW,HLT:2023v12 | `133X_mcRun3_2024_realistic_v8` | pileup `2023_LHC_Simulation_12p5h_9h_hybrid2p23` |
| RAW2DIGI,L1Reco,RECO,RECOSIM | `133X_mcRun3_2024_realistic_v8` | AODSIM + muon keeps (`skim.root`) |

Pileup input: `/MinBias_TuneCP5_13p6TeV-pythia8/Run3Winter24GS-133X_mcRun3_2024_realistic_v7-v1/GEN-SIM`

Changes with respect to the official recipe:
- PU SimHit crossing frames kept for CSC, DT, RPC and GEM (`mix_g4SimHitsMuon{CSC,DT,RPC,GEM}Hits`), so every
  muon SimHit can be labelled signal / in-time PU / out-of-time PU with its BX
- RECO step writes the muon skim instead of AODSIM
- LLP filter: at least one LLP decaying outside r<200 cm & |z|<400 cm and inside r<800 cm, |z|<1200 cm

## Output: the muon skim

The RECO step's output (`skim.root`) is **standard AODSIM plus the muon system**. It is a reco-level file:
no RAW, so the full reconstruction cannot be rerun, but everything an analysis or the ntupler reads is there,
and the muon local reconstruction (and the ML hit producer) can be rerun from the digis.

| part | collections |
|---|---|
| AODSIM | jets, MET, PF candidates, tracks (no hits), vertices, e/γ, reduced ECAL/HCAL rechits, genParticles, pileup info, trigger |
| muon SimHits, signal | `g4SimHits:Muon{CSC,DT,RPC,GEM}Hits` |
| muon SimHits, pileup | crossing frames `mix:g4SimHitsMuon{CSC,DT,RPC,GEM}Hits` |
| muon digis | **unpacked from RAW**, as in data: `muonCSCDigis` (strips, wires, comparators), `muonDTDigis`, `muonRPCDigis`, `muonGEMDigis` |
| muon local reco | `csc2DRecHits`, `cscSegments`, `dt1DRecHits`, `dt4DSegments`, `rpcRecHits`, `gemRecHits`, `gemSegments` |
| only with `tracker` | `generalTracks` extras + hits, `siPixelClusters`, `siStripClusters` (needed to rerun global muon reco) |

Not kept: RAW, tracker/calo digis and clusters, sim muon digis (`simMuon*Digis`), digi→SimHit links, SimTracks,
TrackingParticles. Size: ~0.7 MB/event slim, ~2.8 MB/event with `tracker` (FEVTSIM was 6.2 MB/event).

Readers: ntupler `muonDigiSource=unpacked`; `runMuonRecoML_cfg.py digiSource=file`.

## Layout

```
fragments/   original fragment + the LLP-filter version used as template
cmssw_src/   files installed into CMSSW_13_3_0 (LLP filter plugin, seed customise, MuonDigiDump sim-vs-unpacked check)
setup/       setup_cmssw.sh, make_fragment.py, skim_test_cfg.py, check/compare scripts
pilot/       GEN-only signal grid pilot (filter acceptance vs cτ)
crab/        CRAB production: points.txt, make_cfgs.sh, submit_points.sh, crab_config.py
condor/      NAF condor chain used for the first validation (also ran ntupler + event maker)
```

## Setup (once)

```bash
cmssw-el8 -B /data/dust       # make dust visible inside the container
./setup/setup_cmssw.sh        # creates/updates CMSSW_13_3_0, installs fragments + filter, compiles
```

## Running on CRAB

The CRAB credential must be delegated **on the el9 host**; it fails inside the el8 container.
Do it once every ~30 days:
```bash
source /data/dust/user/guvenlia/cmssw/grid.sh     # VOMS proxy
cd <any el9 CMSSW area>/src && cmsenv
source /cvmfs/cms.cern.ch/crab3/crab.sh
crab createmyproxy --days 30
```

Submit, inside `cmssw-el8`:
```bash
source /cvmfs/cms.cern.ch/cmsset_default.sh
cd /data/dust/user/guvenlia/cmssw/CMSSW_13_3_0/src && cmsenv
source /cvmfs/cms.cern.ch/crab3/crab.sh
cd /data/dust/user/guvenlia/production/mds_classical_mix/crab

NJOBS=1 SUFFIX=smoke ./submit_points.sh                 # 1 job, nothing transferred
# production (njobs/events per line in points.txt), published in DBS phys03
TRANSFER=1 PUBLISH=1 SUFFIX=v1 OUTDIR=/store/user/aguvenli/MDSProduction/ ./submit_points.sh
```
One CRAB task is made per line of `crab/points.txt`: `HToSSTo4b M_H M_S ctau[mm]` or `DYto2Mu <MLL bin>`,
optionally ending in `njobs=N`, `events=N` (generated events per job) and `tracker` (keep tracker hits/clusters, tag gets `_trk`).
The signal is submitted in batches of ~2 lines (1500 jobs) to limit the pileup reads from DESY.

| env var | default | meaning |
|---|---|---|
| `NJOBS` | 50 | jobs per point |
| `EVENTS_PER_JOB` | 100 | generated events per job (signal: about 58% pass the filter) |
| `TRANSFER` | 0 | 1 = stage out to `OUTDIR` at T2_DE_DESY |
| `AT_DESY` | 0 | 1 = run only at T2_DE_DESY (not needed: reading pileup from DESY elsewhere is only ~20% slower) |
| `SUFFIX` | test1 | appended to the CRAB request name |
| `PUBLISH` | 0 | 1 = publish in DBS phys03 as `/<sample>_classicalMix/aguvenli-MDSProd_<SUFFIX>-<hash>/USER` (DAS: `instance=prod/phys03`) |
| `OUTDIR` | `/store/user/aguvenli/MDSProduction_test/` | output LFN base |

Checking:
```bash
crab status -d crab_projects/crab_MDSProd_<point>_<suffix>
crab getlog --short -d crab_projects/crab_MDSProd_<point>_<suffix> --jobids 1
```
Before resubmitting a failed submission, remove its `crab_projects/` folder.

## Expected numbers

From 10 condor jobs (578 filtered events), point MH125_MS12_ctau900mm:

| | |
|---|---|
| filter efficiency | 0.58 |
| DIGI / RECO time | ~16 s / ~2 s per event, 4 threads |
| peak memory | 5.4 GB |
| FEVTSIM size (before the skim) | 6.2 MB per event |
| skim size | 0.70 MB/event signal, 2.8 MB/event DY (with tracker) |
| pileup read | ~190 MB per event (over xrootd) |
| CSC rechit clusters | 0.32 per filtered event |

CRAB jobs with 1000 generated events, 4 threads, ~6.7 GB memory (request 8 GB):

| | GEN-SIM | DIGI | RECO | total |
|---|---|---|---|---|
| signal | 16–27 min | 2–2.4 h (12–15 s/event) | 20–30 min | ~3 h |
| DY 800–1500 | 42 min (incl. LHE) | 3.4 h | 52 min | ~5 h |

Pileup comes from the full MinBias dataset replicated at T2_DE_DESY (`condor/pu_disk_lfns.txt`, 1922 files); each job
reads files sequentially from a random start (CMSSW default), so every MinBias event is reused ~90x but evenly.
