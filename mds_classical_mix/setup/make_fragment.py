# Writes the LLP-filter fragment for one (M_H, M_S, ctau) point.
# Usage: python3 make_fragment.py MH MS CTAU_MM OUTDIR   -> prints the fragment file name
import os, re, sys

HBARC_GEV_MM = 1.973269804e-13   # hbar*c, so width [GeV] = hbar*c / ctau [mm]

mh, ms, ctau, outdir = float(sys.argv[1]), float(sys.argv[2]), float(sys.argv[3]), sys.argv[4]
template = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fragments", "ggH_HToSSTo4b_LLPfilter.py")
text = open(template).read()

values = {"MASS_HIGGS": mh, "MASS_X": ms, "CTAU_X": ctau, "WIDTH_X": HBARC_GEV_MM / ctau}
for name, val in values.items():
    text, n = re.subn(rf"^{name}\s*=.*$", f"{name} = {val!r}", text, flags=re.M)
    if n == 0:
        sys.exit(f"{name} not found in template")

tag = f"MH{mh:g}_MS{ms:g}_ctau{ctau:g}mm"
name = f"ggH_HToSSTo4b_{tag}.py"
open(os.path.join(outdir, name), "w").write(text)
print(name)
