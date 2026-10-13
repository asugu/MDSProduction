# MDS classical-mixing sample production

Private Run 3 MC for MDS ML studies, made with **classical pileup mixing** so that the
pileup SimHits are kept (premixing throws them away). Output is FEVTSIM (GEN-SIM-RECO).
Ntupling is not part of this repo.

Samples:
- signal: ggH → SS → 4b with a long-lived S, mass and cτ configurable, LLP filter
- background: DY → 2μ, Powheg 2024 gridpacks in MLL bins (no filter yet)

## Recipe

TSG Run3Winter24 chain, all steps in **CMSSW_13_3_0 (el8, run inside `cmssw-el8`)**, era `Run3_2023`.

| step | conditions | notes |
|---|---|---|
| GEN-SIM | `133X_mcRun3_2024_realistic_v7` | LLP filter in `ProductionFilterSequence` |
| DIGI,L1,DIGI2RAW,HLT:2023v12 | `133X_mcRun3_2024_realistic_v8` | pileup `2023_LHC_Simulation_12p5h_9h_hybrid2p23` |
| RAW2DIGI,L1Reco,RECO,RECOSIM | `133X_mcRun3_2024_realistic_v8` | **FEVTSIM** instead of AODSIM |

Pileup input: `/MinBias_TuneCP5_13p6TeV-pythia8/Run3Winter24GS-133X_mcRun3_2024_realistic_v7-v1/GEN-SIM`

Changes with respect to the official recipe:
- FEVTSIM output, so the SimHits survive
- PU SimHit crossing frames kept for CSC and DT (`mix_g4SimHitsMuonCSCHits`, `mix_g4SimHitsMuonDTHits`)
- `simMuonDTDigis` kept
- LLP filter: at least one LLP decaying outside r<200 cm & |z|<400 cm and inside r<800 cm, |z|<1200 cm

## Layout

```
fragments/   original fragment + the LLP-filter version used as template
cmssw_src/   files installed into CMSSW_13_3_0 (LLP filter plugin, seed customise)
setup/       setup_cmssw.sh, make_fragment.py, check/summary scripts
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
NJOBS=50 TRANSFER=1 SUFFIX=test1 ./submit_points.sh     # 50 jobs, output to T2_DE_DESY
```
One CRAB task is made per line of `crab/points.txt`: `HToSSTo4b M_H M_S ctau[mm]` or `DYto2Mu <MLL bin>`,
optionally ending in `njobs=N` to give that sample its own number of jobs.

| env var | default | meaning |
|---|---|---|
| `NJOBS` | 50 | jobs per point |
| `EVENTS_PER_JOB` | 100 | generated events per job (signal: about 58% pass the filter) |
| `TRANSFER` | 0 | 1 = stage out to `/store/user/aguvenli/MDSProduction_test/` at T2_DE_DESY |
| `AT_DESY` | 0 | 1 = run only at T2_DE_DESY (once the pileup replica is there) |
| `SUFFIX` | test1 | appended to the CRAB request name |

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
| FEVTSIM size | 6.2 MB per event |
| pileup read | ~190 MB per event (over xrootd) |
| CSC rechit clusters | 0.32 per filtered event |
