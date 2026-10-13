# One CRAB task per mass/ctau point; settings come from env vars (see submit_points.sh).
#   POINT=MH125_MS12_ctau900mm  NJOBS=50  EVENTS_PER_JOB=100  TRANSFER=0|1  AT_DESY=0|1  SUFFIX=test1
import os
from CRABClient.UserUtilities import config
config = config()

point = os.environ["POINT"]
njobs = int(os.environ.get("NJOBS", 50))
per_job = int(os.environ.get("EVENTS_PER_JOB", 100))
transfer = os.environ.get("TRANSFER", "0") == "1"
suffix = os.environ.get("SUFFIX", "test1")
cfg_dir = os.path.join("points", point)

config.General.requestName = f"MDSProd_{point}_{suffix}"
config.General.workArea = "crab_projects"
config.General.transferOutputs = transfer   # 0: nothing written to pnfs (read logs with crab getlog --short)
config.General.transferLogs = transfer

config.JobType.pluginName = "PrivateMC"
config.JobType.psetName = os.path.join(cfg_dir, "gensim_cfg.py")
config.JobType.scriptExe = "crab_chain.sh"
config.JobType.inputFiles = [os.path.join(cfg_dir, "digi_cfg.py"), os.path.join(cfg_dir, "reco_cfg.py")]
config.JobType.outputFiles = ["fevtsim.root"]
config.JobType.numCores = 4
config.JobType.maxMemoryMB = 8000        # condor test peaked at 5.4 GB with 4 threads

config.Data.outputPrimaryDataset = f"HToSSTo4b_{point}_classicalMix"
config.Data.splitting = "EventBased"
config.Data.unitsPerJob = per_job
config.Data.totalUnits = njobs * per_job
config.Data.publication = False
config.Data.outLFNDirBase = "/store/user/aguvenli/MDSProduction_test/"

config.Site.storageSite = "T2_DE_DESY"
if os.environ.get("AT_DESY", "0") == "1":   # once the pileup replica is at DESY
    config.Site.whitelist = ["T2_DE_DESY"]
