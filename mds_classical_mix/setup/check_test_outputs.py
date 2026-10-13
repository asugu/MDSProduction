# Prints LLP (6000113) decay positions from genParticles in a GEN-SIM file.
import sys, math, ROOT
from DataFormats.FWLite import Events, Handle
h = Handle("std::vector<reco::GenParticle>")
for i, ev in enumerate(Events(sys.argv[1])):
    ev.getByLabel("genParticles", h)
    for p in h.product():
        if abs(p.pdgId()) != 6000113 or p.numberOfDaughters() == 0 or abs(p.daughter(0).pdgId()) == 6000113:
            continue
        d = p.daughter(0)
        r = math.hypot(d.vx(), d.vy())
        inbox = (abs(d.vz()) < 1200 and r < 800) and not (abs(d.vz()) < 400 and r < 200)
        print(f"ev{i} LLP decay r={r:7.1f} cm z={d.vz():8.1f} cm  daughters={[p.daughter(k).pdgId() for k in range(p.numberOfDaughters())]}  in_filter_box={inbox}")
