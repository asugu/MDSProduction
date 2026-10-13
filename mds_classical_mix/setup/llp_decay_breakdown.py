# Breakdown of LLP decay positions from the MCLongLivedParticles verbose log.
# Usage: python3 llp_decay_breakdown.py gen500.log
# Region edges in cm are approximate CMS volumes, for a rough census only.
import re, sys
from collections import Counter

LLP_RE = re.compile(r"LLP (\d+) decay at r = ([-\d.e+]+) cm, z = ([-\d.e+]+) cm, eta = ([-\d.e+]+) -> (\w+)")
EVT_RE = re.compile(r"event (passes|fails)")

def region(r, z):
    az = abs(z)
    if r >= 800 or az >= 1200:
        return "outside CMS (r>=800 or |z|>=1200) [rejected]"
    if r < 200 and az < 400:
        return "tracker+ECAL (r<200, |z|<400) [rejected]"
    if az < 400:
        return "barrel HCAL/solenoid (200<=r<400)" if r < 400 else "barrel DT region (r>=400)"
    return "endcap HCAL (400<=|z|<570)" if az < 570 else "endcap CSC region (|z|>=570)"

llps, events = [], Counter()
for line in open(sys.argv[1], errors="replace"):
    m = LLP_RE.search(line)
    if m:
        llps.append((float(m.group(2)), float(m.group(3)), m.group(5)))
        continue
    e = EVT_RE.search(line)
    if e:
        events[e.group(1)] += 1

n_ev = sum(events.values())
print(f"events: {n_ev}  passed: {events['passes']}  efficiency: {events['passes']/max(n_ev,1):.3f}")
print(f"LLP decays: {len(llps)}  accepted by box: {sum(a == 'accepted' for *_, a in llps)}")
for k, v in sorted(Counter(region(r, z) for r, z, _ in llps).items(), key=lambda x: -x[1]):
    print(f"  {k:42s} {v:5d}  ({v/max(len(llps),1):.1%})")
