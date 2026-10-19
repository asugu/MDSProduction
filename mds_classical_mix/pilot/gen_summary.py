# Per-LLP GEN quantities from genParticles -> npz. Runs in CMSSW (FWLite).
# Usage: python3 gen_summary.py gen.root out.npz
import sys
import numpy as np
from DataFormats.FWLite import Events, Handle

LLP_IDS = (6000113, 9000006)
fin, fout = sys.argv[1], sys.argv[2]

handle = Handle("std::vector<reco::GenParticle>")
cols = {k: [] for k in ("event", "E", "p", "pt", "eta", "phi", "m",
                        "prod_x", "prod_y", "prod_z", "dec_x", "dec_y", "dec_z",
                        "dau_pdg", "dau_dR", "higgs_pt")}
n_events = 0
for iev, ev in enumerate(Events(fin)):
    n_events += 1
    ev.getByLabel("genParticles", handle)
    parts = handle.product()
    higgs_pt = max((g.pt() for g in parts if g.pdgId() in (25, 35) and g.isLastCopy()), default=-1.0)
    for g in parts:
        if abs(g.pdgId()) not in LLP_IDS or not g.isLastCopy() or g.numberOfDaughters() < 2:
            continue
        d0, d1 = g.daughter(0), g.daughter(1)
        dphi = (d0.phi() - d1.phi() + np.pi) % (2 * np.pi) - np.pi
        vals = dict(event=iev, E=g.energy(), p=g.p(), pt=g.pt(), eta=g.eta(), phi=g.phi(), m=g.mass(),
                    prod_x=g.vx(), prod_y=g.vy(), prod_z=g.vz(),   # cm
                    dec_x=d0.vx(), dec_y=d0.vy(), dec_z=d0.vz(),
                    dau_pdg=abs(d0.pdgId()), dau_dR=np.hypot(d0.eta() - d1.eta(), dphi),
                    higgs_pt=higgs_pt)
        for k, v in vals.items():
            cols[k].append(v)

out = {k: np.asarray(v) for k, v in cols.items()}
out["n_events"] = np.int64(n_events)
np.savez(fout, **out)
print(f"{n_events} events, {len(out['E'])} LLPs -> {fout}")
