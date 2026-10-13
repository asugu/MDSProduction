# Summary of a condor chain round: per-job cost, cluster yield, SimHit origin/BX, detectability by BX.
# Usage: python3 summarize_chain.py /data/dust/user/guvenlia/production/mds_classical_mix/condor/out
import glob, os, re, sys
import numpy as np
import uproot

OUT = sys.argv[1]
STRIP_THR = 13.3     # max(ADC)-min(ADC), same as event_datamaker / MLCSCRecHitProducer
RECHIT_TOL = 3.0     # cm, same-layer SimHit -> rechit
STRIP_TOL = 1.0      # cm, SimHit -> fired-strip line, same layer (about one strip pitch)
CTRL_SHIFT = 10.0    # cm along phi: control point in the same layer, measures the coincidence floor

def grab(path, pattern, cast=float):
    try:
        m = re.findall(pattern, open(path, errors="replace").read())
        return cast(m[-1]) if m else None
    except OSError:
        return None

# ---- 1. per-job cost ----
print("== per job")
print(f"{'job':>12} {'eff':>6} {'nEv':>4} {'DIGI s/ev':>9} {'RECO s/ev':>9} {'FEVT MB/ev':>10} {'ntup kB/ev':>10} {'h5 docs':>7}")
jobs = sorted(glob.glob(f"{OUT}/ntupled_*.root"))
for nt in jobs:
    jid = nt.split("ntupled_")[1][:-5]
    L = f"{OUT}/logs_{jid}"
    eff = grab(f"{L}/gensim.log", r"Filter efficiency \(event-level\)= \((\d+)\) / \((\d+)\)", str)
    n_pass, n_gen = (map(int, re.findall(r"\d+", eff))) if eff else (0, 0)
    t_digi = grab(f"{L}/digi.log", r"event loop Real/event = ([\d.]+)")
    t_reco = grab(f"{L}/reco.log", r"event loop Real/event = ([\d.]+)")
    fevt = f"{OUT}/fevtsim_{jid}.root"
    mb = os.path.getsize(fevt) / 1e6 / max(n_pass, 1) if os.path.exists(fevt) else float("nan")
    kb = os.path.getsize(nt) / 1e3 / max(n_pass, 1)
    docs = grab(f"{L}/event_cluster.log", r"\[event\] (\d+)/\d+ events written", int)
    print(f"{jid:>12} {n_pass/max(n_gen,1):6.2f} {n_pass:4d} {t_digi or float('nan'):9.1f} {t_reco or float('nan'):9.1f} {mb:10.2f} {kb:10.0f} {docs if docs is not None else '-':>7}")

# ---- 2. load all ntuples ----
br = ["nCscRechitClusters", "gLLP_csc", "gLLP_dt",
      "cscSimHitDetID", "cscSimHitX", "cscSimHitY", "cscSimHitZ", "cscSimHitBX", "cscSimHitOrigin",
      "cscRechitsDetId", "cscRechitsX", "cscRechitsY", "cscRechitsZ",
      "cscStripDigiDetID", "cscStripDigiADC", "cscStripStartX", "cscStripStartY", "cscStripStartZ",
      "cscStripEndX", "cscStripEndY", "cscStripEndZ",
      "dtSimHitDetID", "dtSimHitBX", "dtSimHitOrigin", "dtDigiDetID", "dtDigiWire"]
ev = {k: [] for k in br}
for nt in jobs:
    a = uproot.open(nt)["ntuples/llp"].arrays(br, library="np")
    for k in br:
        ev[k].extend(a[k])
n_ev = len(ev["nCscRechitClusters"])

# ---- 3. cluster yield ----
ncl = np.array(ev["nCscRechitClusters"])
llp_csc = np.array([np.any(x) for x in ev["gLLP_csc"]])
llp_dt = np.array([np.any(x) for x in ev["gLLP_dt"]])
print(f"\n== cluster yield ({n_ev} filtered events)")
print(f"CSC rechit clusters / event: {ncl.mean():.3f}   events with >=1 cluster: {np.mean(ncl > 0):.3f}")
for lab, m in [("LLP in CSC", llp_csc), ("LLP in DT (not CSC)", llp_dt & ~llp_csc), ("neither", ~llp_csc & ~llp_dt)]:
    if m.any():
        print(f"  {lab:22s} n={m.sum():4d}  clusters/event={ncl[m].mean():.3f}  frac>=1={np.mean(ncl[m] > 0):.3f}")

# ---- 4. SimHit origin / BX ----
for det in ["csc", "dt"]:
    o = np.concatenate(ev[f"{det}SimHitOrigin"]) if n_ev else np.array([])
    print(f"\n== {det.upper()} SimHits: origin (0 sig, 1 in-time PU, 2 OOT PU):",
          {int(k): int(v) for k, v in zip(*np.unique(o, return_counts=True))})

# ---- 5. CSC detectability by BX: rechit nearby / fired strip nearby, same layer ----
def seg_dist(P, S, E):
    D = E - S
    u = np.clip(((P - S) * D).sum(1) / np.maximum((D * D).sum(1), 1e-9), 0, 1)
    return np.linalg.norm(S + u[:, None] * D - P, axis=1)

rows = []
for i in range(n_ev):
    sd = ev["cscSimHitDetID"][i]
    if len(sd) == 0:
        continue
    SP = np.stack([ev[f"cscSimHit{c}"][i] for c in "XYZ"], 1)
    rd = ev["cscRechitsDetId"][i]; RP = np.stack([ev[f"cscRechits{c}"][i] for c in "XYZ"], 1)
    adc = np.asarray(ev["cscStripDigiADC"][i]).reshape(-1, 8).astype(float)
    fired = (adc.max(1) - adc.min(1)) > STRIP_THR
    std = ev["cscStripDigiDetID"][i][fired]
    SS = np.stack([ev[f"cscStripStart{c}"][i][fired] for c in "XYZ"], 1)
    SE = np.stack([ev[f"cscStripEnd{c}"][i][fired] for c in "XYZ"], 1)
    # control: same hit rotated by CTRL_SHIFT in phi (stays in its layer plane)
    dphi = CTRL_SHIFT / np.maximum(np.hypot(SP[:, 0], SP[:, 1]), 1.0)
    CP = np.stack([SP[:, 0] * np.cos(dphi) - SP[:, 1] * np.sin(dphi),
                   SP[:, 0] * np.sin(dphi) + SP[:, 1] * np.cos(dphi), SP[:, 2]], 1)
    for j in range(len(sd)):
        m = rd == sd[j]
        ms = std == sd[j]
        res = []
        for P in (SP[j], CP[j]):
            res.append(m.any() and np.min(np.linalg.norm(RP[m] - P, axis=1)) < RECHIT_TOL)
            res.append(ms.any() and np.min(seg_dist(P, SS[ms], SE[ms])) < STRIP_TOL)
        rows.append((ev["cscSimHitBX"][i][j], *res))
r = np.array(rows, dtype=float)
print(f"\n== CSC SimHit detectability by BX (same layer; rechit < {RECHIT_TOL} cm, fired strip < {STRIP_TOL} cm)")
print(f"   ctrl = same test at a point {CTRL_SHIFT:.0f} cm away in phi (coincidence floor)")
print(f"{'BX':>4} {'nSim':>7} {'rechit':>7} {'ctrl':>6} {'strip':>7} {'ctrl':>6} {'strip-ctrl':>11}")
for b in range(-12, 4):
    s = r[r[:, 0] == b]
    if len(s):
        rec, strip, rec_c, strip_c = s[:, 1].mean(), s[:, 2].mean(), s[:, 3].mean(), s[:, 4].mean()
        print(f"{b:>4} {len(s):>7} {rec:>7.2f} {rec_c:>6.2f} {strip:>7.2f} {strip_c:>6.2f} {strip - strip_c:>+11.2f}")

# ---- 6. DT detectability by BX: SimHit's own wire fired ----
WMASK = 0xFF << 3   # DTWireId wire field; layerId = raw with it cleared
dt_rows = []
for i in range(n_ev):
    fired = set(zip(ev["dtDigiDetID"][i].tolist(), ev["dtDigiWire"][i].tolist()))
    for raw, bx in zip(ev["dtSimHitDetID"][i].astype(np.int64) & 0xFFFFFFFF, ev["dtSimHitBX"][i]):
        dt_rows.append((bx, ((raw & ~WMASK) & 0xFFFFFFFF, (raw >> 3) & 0xFF) in fired))
d = np.array(dt_rows, dtype=float)
print("\n== DT SimHit: own wire fired, by BX")
for b in range(-12, 4):
    s = d[d[:, 0] == b] if len(d) else d
    if len(s):
        print(f"{b:>4} {len(s):>7} {s[:, 1].mean():>7.2f}")
