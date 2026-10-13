#!/bin/bash
# One job: GEN-SIM (LLP filter) -> DIGI (classical mixing) -> RECO -> ntuple -> event_cluster h5.
# Usage: run_chain.sh <job_id> <n_gen_events> <proc_id>   (based on produce_minbias_2023.sh)
set -e
set -x

job_id=$1
ngen=$2
proc_id=$3
[ -n "$proc_id" ] || { echo "usage: $0 <job_id> <n_gen_events> <proc_id>"; exit 1; }
lumi=$((proc_id + 1))   # lumi 0 is invalid, so ProcId 0 -> lumi 1

here=/data/dust/user/guvenlia/production/mds_classical_mix/condor
out_dir=$here/out
ntupler_dir=/data/dust/user/guvenlia/cmssw/ntuple/CMSSW_14_0_22
ntupler_cfg=$ntupler_dir/src/cms_lpc_llp/llp_ntupler/python/config_asu.py
flex_dir=/data/dust/user/guvenlia/mds-ml/flex_atten
py=/data/dust/user/guvenlia/conda/envs/root_env/bin/python3

# DIGI reads pileup over xrootd, needs a CMS proxy
[ -f /cvmfs/grid.cern.ch/etc/profile.d/setup-cvmfs-ui.sh ] && source /cvmfs/grid.cern.ch/etc/profile.d/setup-cvmfs-ui.sh
voms-proxy-info -all | grep -q "cms" || { echo "No CMS VOMS in proxy"; exit 2; }

# scratch on dust, not /tmp or AFS; removed on exit unless KEEP_SCRATCH=1
workdir=/data/dust/user/guvenlia/scratch/mds_classical_mix/job_${job_id}_$$
mkdir -p "$workdir" "$out_dir"
cleanup() { [ "${KEEP_SCRATCH:-0}" = "1" ] || rm -rf "$workdir"; }
trap cleanup EXIT
cd "$workdir"
export HOME="$workdir" XDG_CACHE_HOME="$workdir/.cache"   # writable DAS/scram caches

# steps 1-3 run in el8 (CMSSW_13_3_0); bind the proxy dir for DIGI
export JOB_ID=$job_id NGEN=$ngen WORKDIR=$workdir LUMI=$lumi
export FRAGMENT=ggH_HToSSTo4b_LLPfilter.py PU_LIST=$here/pu_disk_lfns.txt
/cvmfs/cms.cern.ch/common/cmssw-el8 -B /data/dust -B "$(dirname "$X509_USER_PROXY")" \
  --command-to-run $here/el8_chain.sh

# step 4: ntupler (el9, CMSSW_14_0_22)
source /cvmfs/cms.cern.ch/cmsset_default.sh
(cd $ntupler_dir/src && eval "$(scramv1 runtime -sh)" && cd "$workdir" && \
  echo "file:$workdir/fevtsim.root" > inputFiles.txt && \
  cmsRun $ntupler_cfg inputFiles=inputFiles.txt \
    globalTag=133X_mcRun3_2024_realistic_v8 saveDTSimDigi=True cscStripFiredOnly=True > ntuple.log 2>&1)

# step 5: event maker
$py $flex_dir/make_event_cluster.py --sample ggH --in ntupled.root --out event_cluster.h5 > event_cluster.log 2>&1

# FEVTSIM kept by default for now (KEEP_FEVTSIM=0 drops it)
mv ntupled.root $out_dir/ntupled_${job_id}.root
mv event_cluster.h5 $out_dir/event_cluster_${job_id}.h5
[ "${KEEP_FEVTSIM:-1}" = "1" ] && mv fevtsim.root $out_dir/fevtsim_${job_id}.root
mkdir -p $out_dir/logs_${job_id}
cp *.log *_fjr.xml *_cfg.py $out_dir/logs_${job_id}/
echo "done: $out_dir/ntupled_${job_id}.root"
