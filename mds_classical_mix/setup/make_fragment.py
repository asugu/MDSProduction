# Writes the fragment for one sample and prints "<fragment file> <tag>".
# Usage: python3 make_fragment.py HToSSTo4b MH MS CTAU_MM OUTDIR    (also HToSSTo4d, HToSSTo4tau)
#        python3 make_fragment.py DYto2Mu   MLL_BIN OUTDIR          (e.g. 120to200, 6000)
import os, re, sys

HBARC_GEV_MM = 1.973269804e-13   # hbar*c, so width [GeV] = hbar*c / ctau [mm]
FRAG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fragments")


DECAY_PDG = {"b": 5, "d": 1, "tau": 15}


def htossto4f(f, mh, ms, ctau):
    text = open(os.path.join(FRAG_DIR, "ggH_HToSSTo4b_LLPfilter.py")).read()
    values = {"MASS_HIGGS": mh, "MASS_X": ms, "CTAU_X": ctau, "WIDTH_X": HBARC_GEV_MM / ctau,
              "DECAY_PDG": DECAY_PDG[f]}
    for name, val in values.items():
        text, n = re.subn(rf"^{name}\s*=.*$", f"{name} = {val!r}", text, flags=re.M)
        if n == 0:
            sys.exit(f"{name} not found in template")
    tag = f"HToSSTo4{f}_MH{mh:g}_MS{ms:g}_ctau{ctau:g}mm"
    return text, f"ggH_{tag}.py", tag


def dyto2mu(mll_bin):
    # 2024 gridpacks; the fragments differ only in the bin name in the gridpack path
    text = open(os.path.join(FRAG_DIR, "DYto2Mu_Bin-MLL-120to200_TuneCP5_13p6TeV_powheg-pythia8.py")).read()
    text = text.replace("Bin-MLL-120to200", f"Bin-MLL-{mll_bin}")
    gridpack = re.search(r"'(/cvmfs/\S+\.tgz)'", text).group(1)
    if not os.path.exists(gridpack):
        sys.exit(f"no gridpack {gridpack}")
    tag = f"DYto2Mu_MLL-{mll_bin}"
    return text, f"{tag}.py", tag


kind, args, outdir = sys.argv[1], sys.argv[2:-1], sys.argv[-1]
if kind.startswith("HToSSTo4") and kind[8:] in DECAY_PDG:
    text, name, tag = htossto4f(kind[8:], *map(float, args))
elif kind == "DYto2Mu":
    text, name, tag = dyto2mu(*args)
else:
    sys.exit(f"unknown sample type {kind}")
open(os.path.join(outdir, name), "w").write(text)
print(name, tag)
