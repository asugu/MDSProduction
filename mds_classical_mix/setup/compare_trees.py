"""Exact entry-by-entry comparison of every TTree in two ROOT files (same input events, same order).
Usage: python compare_trees.py a.root b.root"""
import sys
import numpy as np
import uproot

fa, fb = uproot.open(sys.argv[1]), uproot.open(sys.argv[2])
trees = lambda f: {k.split(";")[0] for k, c in f.classnames().items() if c == "TTree"}
ta, tb = trees(fa), trees(fb)
if ta ^ tb:
    print("trees only in one file:", sorted(ta ^ tb))
for name in sorted(ta & tb):
    a, b = fa[name], fb[name]
    print(f"== {name}: entries {a.num_entries} vs {b.num_entries}, branches {len(a.keys())} vs {len(b.keys())}")
    if set(a.keys()) ^ set(b.keys()):
        print("   branches only in one:", sorted(set(a.keys()) ^ set(b.keys())))
    if a.num_entries != b.num_entries:
        continue
    bad, empty = [], []
    for br in sorted(set(a.keys()) & set(b.keys())):
        x, y = a[br].array(library="np"), b[br].array(library="np")
        nbad = sum(not np.array_equal(np.asarray(u), np.asarray(v), equal_nan=np.asarray(u).dtype.kind == "f")
                   or np.shape(u) != np.shape(v) for u, v in zip(x, y))
        if nbad:
            bad.append((br, nbad))
        elif not any(np.any(np.asarray(u) != 0) for u in x):
            empty.append(br)
    ok = len(a.keys()) - len(bad) - len(empty)
    print(f"   identical and filled {ok}, zero/empty in both {len(empty)}, DIFFERENT {len(bad)}")
    for br, n in bad:
        print(f"   DIFF {br}: {n} entries")
    if empty:
        print(f"   empty: {', '.join(empty)}")
