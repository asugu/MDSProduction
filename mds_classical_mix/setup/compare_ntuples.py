"""Branch-by-branch, event-by-event comparison of two llp ntuples (e.g. FEVTSIM vs skim).
Usage: python compare_ntuples.py a.root b.root
Events are matched by (runNum, lumiNum, eventNum); every branch is compared exactly (NaN == NaN)."""
import sys
import numpy as np
import uproot

ta = uproot.open(sys.argv[1])["ntuples/llp"]
tb = uproot.open(sys.argv[2])["ntuples/llp"]
ka, kb = set(ta.keys()), set(tb.keys())
print(f"A {sys.argv[1]}: {ta.num_entries} events, {len(ka)} branches")
print(f"B {sys.argv[2]}: {tb.num_entries} events, {len(kb)} branches")
for name, s in [("only in A", ka - kb), ("only in B", kb - ka)]:
    if s:
        print(f"{name}: {sorted(s)}")

ida = ta.arrays(["runNum", "lumiNum", "eventNum"], library="np")
idb = tb.arrays(["runNum", "lumiNum", "eventNum"], library="np")
key = lambda d: list(zip(d["runNum"], d["lumiNum"], d["eventNum"]))
pos_b = {k: i for i, k in enumerate(key(idb))}
order = [pos_b.get(k, -1) for k in key(ida)]
print(f"events matched: {sum(o >= 0 for o in order)} / {ta.num_entries}")
ia = np.array([i for i, o in enumerate(order) if o >= 0])
ib = np.array([o for o in order if o >= 0])

same, diff, empty_both = [], [], []
for br in sorted(ka & kb):
    a = ta[br].array(library="np")[ia]
    b = tb[br].array(library="np")[ib]
    nbad, nonzero = 0, False
    for x, y in zip(a, b):
        x, y = np.asarray(x), np.asarray(y)
        if x.size or y.size:
            nonzero = nonzero or bool(np.any(x != 0)) or bool(np.any(y != 0))
        if x.shape != y.shape or not np.array_equal(x, y, equal_nan=x.dtype.kind == "f"):
            nbad += 1
    if nbad:
        sa = sum(np.asarray(x).size for x in a)
        sb = sum(np.asarray(y).size for y in b)
        diff.append((br, nbad, sa, sb))
    elif not nonzero:
        empty_both.append(br)
    else:
        same.append(br)

print(f"\nidentical (and filled): {len(same)}")
print(f"identical but zero/empty in both: {len(empty_both)}")
print(f"DIFFERENT: {len(diff)}")
print(f"{'branch':40s} {'events differing':>16s} {'entries A':>10s} {'entries B':>10s}")
for br, n, sa, sb in diff:
    print(f"{br:40s} {n:16d} {sa:10d} {sb:10d}")
with open("compare_ntuples_empty.txt", "w") as f:
    f.write("\n".join(empty_both) + "\n")
