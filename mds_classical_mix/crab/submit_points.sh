#!/bin/bash
# Makes configs and submits one CRAB task per line of points.txt. Run inside cmssw-el8, cmsenv + crab.sh, with proxy.
# Settings pass through to crab_config.py, e.g.:  NJOBS=1 SUFFIX=smoke ./submit_points.sh
set -e
cd "$(dirname "$0")"
# points are read on fd 3 so crab keeps the terminal (it may ask for the grid pass phrase)
while read -r -u 3 mh ms ctau; do
    tag=$(./make_cfgs.sh "$mh" "$ms" "$ctau" | tail -1)
    echo ">> submitting $tag"
    POINT=$tag crab submit -c crab_config.py
done 3< <(grep -vE "^\s*(#|$)" points.txt)
