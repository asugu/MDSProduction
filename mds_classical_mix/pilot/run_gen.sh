#!/bin/bash
# Condor job: GEN for one pilot point (el8 container), then gen_summary.py -> out/<tag>.npz.
# Usage: run_gen.sh <tag>
set -e
set -x
tag=$1
here=/data/dust/user/guvenlia/production/mds_classical_mix/pilot
[ -n "$tag" ] || { echo "usage: $0 <tag>"; exit 1; }

workdir=/data/dust/user/guvenlia/scratch/mds_pilot/${tag}_$$
mkdir -p "$workdir" $here/out
cleanup() { [ "${KEEP_SCRATCH:-0}" = "1" ] || rm -rf "$workdir"; }
trap cleanup EXIT
export HOME="$workdir" XDG_CACHE_HOME="$workdir/.cache"

cat > $workdir/inner.sh <<INNER
set -e
source /cvmfs/cms.cern.ch/cmsset_default.sh
cd /data/dust/user/guvenlia/cmssw/CMSSW_13_3_0/src && eval "\$(scramv1 runtime -sh)"
cd $workdir
cmsRun $here/points/$tag/gen_cfg.py > gen.log 2>&1
python3 $here/gen_summary.py gen.root $here/out/$tag.npz > summary.log 2>&1
INNER
/cvmfs/cms.cern.ch/common/cmssw-el8 -B /data/dust --command-to-run bash $workdir/inner.sh

mkdir -p $here/out/logs_$tag
cp $workdir/*.log $here/out/logs_$tag/
[ "${KEEP_ROOT:-0}" = "1" ] && mv $workdir/gen.root $here/out/$tag.root
echo "done: $here/out/$tag.npz"
