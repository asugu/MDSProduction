#!/bin/bash
# Makes configs and submits one CRAB task per line of points.txt. Run inside cmssw-el8, cmsenv + crab.sh, with proxy.
# Settings pass through to crab_config.py, e.g.:  NJOBS=1 SUFFIX=smoke ./submit_points.sh
set -e
cd "$(dirname "$0")"
# points are read on fd 3 so crab keeps the terminal (it may ask for the grid pass phrase)
while read -r -u 3 line; do
    # optional tokens: njobs=N, events=N (override NJOBS / EVENTS_PER_JOB), tracker (keep tracker hits)
    njobs=${NJOBS:-50}; events=${EVENTS_PER_JOB:-100}; tracker=0; args=()
    for tok in ${line%%#*}; do    # drop trailing "# ..." comments
        case $tok in
            njobs=*) njobs=${tok#njobs=} ;;
            events=*) events=${tok#events=} ;;
            tracker) tracker=1 ;;
            *) args+=("$tok") ;;
        esac
    done
    tag=$(EVENTS_PER_JOB=$events TRACKER=$tracker ./make_cfgs.sh "${args[@]}" | tail -1)
    echo ">> submitting $tag: $njobs jobs x $events events"
    POINT=$tag NJOBS=$njobs EVENTS_PER_JOB=$events crab submit -c crab_config.py
done 3< <(grep -vE "^\s*(#|$)" points.txt)
