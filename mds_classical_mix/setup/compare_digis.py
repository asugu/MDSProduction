"""Sim vs unpacked (from RAW) muon digis from MuonDigiDump output. Usage: python compare_digis.py digi_compare.root"""
import sys
import numpy as np
import uproot

f = uproot.open(sys.argv[1])["dump"]


def load(name, extra=()):
    t = f[name]
    d = t.arrays(["ev", "src", "id", "ch", *extra], library="np")
    key = np.column_stack([d["ev"], d["id"], d["ch"]])
    return d, key


def match(key, src):
    """bool arrays: sim row has an identical channel in raw, and vice versa"""
    s, r = key[src == 0], key[src == 1]
    sv = np.ascontiguousarray(s).view([("", s.dtype)] * s.shape[1]).ravel()
    rv = np.ascontiguousarray(r).view([("", r.dtype)] * r.shape[1]).ravel()
    return np.isin(sv, rv), np.isin(rv, sv)


def pct(a, b):
    return f"{100 * a / max(b, 1):5.1f}%"


# CSC strips
d, key = load("strip", ["adc", "nAdc"])
adc = d["adc"]
fired = (adc.max(1) - np.where(adc < 0, 9999, adc).min(1)) > 13.3
src = d["src"]
in_raw, in_sim = match(key, src)
fs, fr = fired[src == 0], fired[src == 1]
print("== CSC strips")
print(f"sim {len(fs)}  raw {len(fr)}   fired: sim {fs.sum()}  raw {fr.sum()}")
print(f"sim fired found in raw     {pct((fs & in_raw).sum(), fs.sum())}")
print(f"sim not-fired found in raw {pct((~fs & in_raw).sum(), (~fs).sum())}")
print(f"raw not in sim             {pct((~in_sim).sum(), len(in_sim))}")
print(f"nAdc sim {np.unique(d['nAdc'][src == 0])}  raw {np.unique(d['nAdc'][src == 1])}")
# ADC equality for matched channels
ks, kr = key[src == 0], key[src == 1]
o_s = np.lexsort(ks.T[::-1]); o_r = np.lexsort(kr.T[::-1])
ms = o_s[in_raw[o_s]]; mr = o_r[in_sim[o_r]]
a_s, a_r = adc[src == 0][ms], adc[src == 1][mr]
print(f"matched strips with identical ADCs {pct((a_s == a_r).all(1).sum(), len(ms))}")
print("per station/ring (sim fired kept in raw | sim fired count)")
ids = d["id"][src == 0]
for st in range(1, 5):
    for rg in range(1, 5):
        m = (ids[:, 1] == st) & (ids[:, 2] == rg) & fs
        if m.sum():
            print(f"  ME{st}/{rg}: {pct((m & in_raw).sum(), m.sum())} | {m.sum()}")

for name, extra, cols in [("wire", ["tbin", "nTbOn"], ["tbin"]), ("comp", ["tbin", "val"], ["tbin", "val"]),
                          ("dt", ["tdc", "number"], ["tdc"]), ("rpc", ["bx"], ["bx"]), ("gem", ["bx"], ["bx"])]:
    d, key = load(name, extra)
    src = d["src"]
    in_raw, in_sim = match(key, src)
    full = np.column_stack([key] + [d[c] for c in cols])
    fr_, fs_ = match(full, src)
    print(f"== {name}: sim {(src == 0).sum()} raw {(src == 1).sum()} | sim channel in raw {pct(in_raw.sum(), len(in_raw))}"
          f"  raw channel in sim {pct(in_sim.sum(), len(in_sim))} | identical incl. {'+'.join(cols)}: {pct(fr_.sum(), len(fr_))}")
