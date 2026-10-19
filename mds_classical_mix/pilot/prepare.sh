#!/bin/bash
# Writes one GEN-only cfg (LLP filter removed) per line of points.txt into points/<tag>/; lists tags in tags.txt.
# Run once inside cmssw-el8 with CMSSW_13_3_0 cmsenv. NEV events per point (default 2000).
set -e
cd "$(dirname "$0")"
here=$PWD
NEV=${NEV:-2000}
frag_dir=$CMSSW_BASE/src/Configuration/GenProduction/python
tmp=$(mktemp -d -p $here)
: > tags.txt
grep -v '^#' points.txt | while read -r kind mh ms ctau0 near far role; do
  [ -n "$kind" ] || continue
  read -r frag tag < <(python3 ../setup/make_fragment.py $kind $mh $ms $ctau0 $tmp)
  # no filter: the pilot measures the acceptance itself
  pilot_frag=${frag%.py}_pilot.py
  sed 's/cms.Sequence(generator + LLPDecayInDTorCSCFilter)/cms.Sequence(generator)/' $tmp/$frag > $frag_dir/$pilot_frag
  grep -q "^ProductionFilterSequence = cms.Sequence(generator)$" $frag_dir/$pilot_frag || { echo "filter not removed in $pilot_frag"; exit 1; }
  mkdir -p points/$tag && cd points/$tag
  cmsDriver.py Configuration/GenProduction/python/$pilot_frag \
    --fileout file:gen.root --mc --eventcontent RAWSIM --datatier GEN \
    --conditions 133X_mcRun3_2024_realistic_v7 --beamspot Realistic25ns13p6TeVEarly2023Collision \
    --step GEN --geometry DB:Extended --era Run3_2023 -n $NEV \
    --python_filename gen_cfg.py --no_exec \
    --customise Configuration/GenProduction/setRandomSeed.py
  cd $here
  echo "$tag $mh $ms $ctau0 $near $far $role" >> tags.txt
done
rm -rf $tmp
echo "wrote $(wc -l < tags.txt) points to tags.txt"
