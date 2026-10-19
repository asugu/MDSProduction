# Pilot summary: reweights each point's GEN sample to any ctau and prints/plots the checks
# (CSC + DT acceptance vs ctau, decay positions at near/far, boost vs energy, daughter dR, delay).
# Usage (root_env): python analyze_pilot.py [--out plots]
import argparse
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
C_CM_NS = 29.9792458
# detector volumes [cm]; the acceptance (from HCAL on) is the filter box = LLPDecayInDTorCSCFilter
CSC = dict(zmin=550.0, zmax=1100.0, rmax=695.5)
DT = dict(rmin=380.0, rmax=750.0, zmax=661.0)
CTAU_SCAN = np.logspace(1, 6, 201)     # mm
MH_COLOR = {125: "#0072B2", 400: "#E69F00", 1000: "#009E73"}
DELAY_NS = 12.5                        # upper edge of the in-time cluster window


def load_points():
    pts = []
    for line in open(os.path.join(HERE, "tags.txt")):
        tag, mh, ms, ctau0, near, far, role = line.split()
        f = os.path.join(HERE, "out", tag + ".npz")
        if not os.path.exists(f):
            print(f"missing {f}")
            continue
        d = dict(np.load(f))
        r = np.hypot(d["dec_x"], d["dec_y"])
        z = d["dec_z"]
        L = np.sqrt((d["dec_x"] - d["prod_x"]) ** 2 + (d["dec_y"] - d["prod_y"]) ** 2
                    + (d["dec_z"] - d["prod_z"]) ** 2)                    # cm
        bg = d["p"] / d["m"]
        beta = d["p"] / d["E"]
        d.update(r=r, az=np.abs(z), L=L, bg=bg, t=10.0 * L / bg,          # proper decay length, mm
                 delay=L * (1.0 / beta - 1.0) / C_CM_NS,
                 in_csc=(np.abs(z) > CSC["zmin"]) & (np.abs(z) < CSC["zmax"]) & (r < CSC["rmax"]),
                 in_dt=(r > DT["rmin"]) & (r < DT["rmax"]) & (np.abs(z) < DT["zmax"]),
                 in_box=~((r < 200) & (np.abs(z) < 400)) & (r < 800) & (np.abs(z) < 1200))
        pts.append(dict(tag=tag, mh=int(float(mh)), ms=float(ms), ctau0=float(ctau0),
                        near=float(near), far=float(far), role=role, d=d))
    return pts


def event_weights(d, ctau0, ctau):
    # per-event weight = product over its LLPs of exp-pdf ratio at the proper decay length
    w_llp = (ctau0 / ctau) * np.exp(-d["t"] * (1.0 / ctau - 1.0 / ctau0))
    w = np.ones(int(d["n_events"]))
    np.multiply.at(w, d["event"], w_llp)
    return w


def acceptance(d, ctau0, ctau, mask):
    # P(>=1 LLP in region) at ctau; also Kish effective N of the weights
    w = event_weights(d, ctau0, ctau)
    hit = np.zeros(len(w), bool)
    np.logical_or.at(hit, d["event"], mask)
    return np.sum(w * hit) / np.sum(w), np.sum(w) ** 2 / np.sum(w ** 2)


def llp_weights(d, ctau0, ctau):
    return event_weights(d, ctau0, ctau)[d["event"]]


def label(p):
    mode = p["tag"].split("_")[0].replace("HToSSTo4", "")
    return f"{p['mh']}/{p['ms']:g} {mode}" + (" [HO]" if p["role"] == "holdout" else "")


def grid(n):
    nc = 4
    nr = (n + nc - 1) // nc
    fig, axes = plt.subplots(nr, nc, figsize=(4 * nc, 3 * nr), squeeze=False)
    for ax in axes.flat[n:]:
        ax.set_visible(False)
    return fig, axes.flat


def plot_acceptance(pts, out):
    fig, axes = grid(len(pts))
    for ax, p in zip(axes, pts):
        d = p["d"]
        for key, ls, name in (("in_csc", "-", "CSC"), ("in_dt", "--", "DT"), ("in_box", ":", "filter box")):
            acc = [acceptance(d, p["ctau0"], c, d[key])[0] for c in CTAU_SCAN]
            ax.plot(CTAU_SCAN, acc, ls, color=MH_COLOR[p["mh"]], lw=1.5, label=name)
        for c in (p["near"], p["far"]):
            ax.axvline(c, color="0.5", lw=0.8)
        ax.set_xscale("log")
        ax.set_title(label(p), fontsize=10)
        ax.set_xlabel(r"c$\tau$ [mm]")
        ax.set_ylabel(r"P($\geq$1 LLP in region)")
    axes[0].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(out, "acceptance_vs_ctau.png"), dpi=120)


def plot_positions(pts, out):
    for key, var, edges, xl, fname in (("in_csc", "az", np.linspace(550, 1100, 36), "decay |z| [cm] (CSC volume)", "decay_z_csc.png"),
                                       ("in_dt", "r", np.linspace(380, 750, 38), "decay r [cm] (DT volume)", "decay_r_dt.png")):
        fig, axes = grid(len(pts))
        for ax, p in zip(axes, pts):
            d = p["d"]
            sel = d[key]
            for c, ls, name in ((p["near"], "-", "near"), (p["far"], "--", "far")):
                w = llp_weights(d, p["ctau0"], c)
                ax.hist(d[var][sel], bins=edges, weights=w[sel], density=True, histtype="step",
                        ls=ls, color=MH_COLOR[p["mh"]], lw=1.5, label=f"{name} {c:g} mm")
            ax.set_title(label(p), fontsize=10)
            ax.set_xlabel(xl)
            ax.legend(fontsize=7)
        fig.tight_layout()
        fig.savefig(os.path.join(out, fname), dpi=120)


def plot_boost_energy(pts, out):
    fig, ax = plt.subplots(figsize=(6, 4.5))
    for p in pts:
        d = p["d"]
        sel = d["in_csc"] | d["in_dt"]
        bg, E = d["bg"][sel], d["E"][sel]
        if len(bg) == 0:
            continue
        x, y = np.median(E), np.median(bg)
        xe = [[x - np.percentile(E, 25)], [np.percentile(E, 75) - x]]
        ye = [[y - np.percentile(bg, 25)], [np.percentile(bg, 75) - y]]
        mk = "s" if p["role"] == "holdout" else "o"
        ax.errorbar(x, y, xerr=xe, yerr=ye, fmt=mk, color=MH_COLOR[p["mh"]], ms=8, mfc="white" if mk == "s" else MH_COLOR[p["mh"]])
        ax.annotate(label(p), (x, y), xytext=(4, 4), textcoords="offset points", fontsize=7)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("LLP energy [GeV] (median, IQR)")
    ax.set_ylabel(r"LLP $\beta\gamma$ (median, IQR)")
    ax.set_title("LLPs decaying in CSC or DT volume; squares = held out", fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(out, "boost_vs_energy.png"), dpi=120)


def plot_dR_delay(pts, out):
    for var, xl, fname, logx in (("dau_dR", r"$\Delta$R(S daughters)", "daughter_dR.png", True),
                                 ("delay", "delay vs prompt at decay point [ns]", "delay.png", False)):
        fig, ax = plt.subplots(figsize=(6, 0.35 * len(pts) + 1.2))
        for i, p in enumerate(pts):
            d = p["d"]
            v = d[var][d["in_csc"] | d["in_dt"]]
            if len(v) == 0:
                continue
            q = np.percentile(v, [10, 25, 50, 75, 90])
            c = MH_COLOR[p["mh"]]
            ax.plot([q[0], q[4]], [i, i], color=c, lw=1)
            ax.plot([q[1], q[3]], [i, i], color=c, lw=5, solid_capstyle="butt")
            ax.plot(q[2], i, "o", color="white", mec=c, ms=6)
        if var == "delay":
            ax.axvline(DELAY_NS, color="0.4", lw=0.8, ls="--")
        ax.set_yticks(range(len(pts)))
        ax.set_yticklabels([label(p) for p in pts], fontsize=8)
        ax.invert_yaxis()
        if logx:
            ax.set_xscale("log")
        ax.set_xlabel(xl + "  (10/25/50/75/90%)")
        fig.tight_layout()
        fig.savefig(os.path.join(out, fname), dpi=120)


def table(pts):
    hdr = (f"{'point':22s} {'eff_box near/far':>16s} {'CSC near/far':>13s} {'DT near/far':>13s} "
           f"{'opt ctau CSC':>12s} {'opt ctau DT':>11s} {'opt ctau box':>12s} {'Neff box':>8s} {'<t>/ct0':>7s} "
           f"{'bg med':>6s} {'dR med':>6s} {'f(delay>12.5)':>13s} daughters")
    print(hdr)
    print("-" * len(hdr))
    for p in pts:
        d, c0 = p["d"], p["ctau0"]
        cell = {}
        for key in ("in_box", "in_csc", "in_dt"):
            cell[key] = "/".join(f"{acceptance(d, c0, c, d[key])[0]:.2f}" for c in (p["near"], p["far"]))
        opt = {k: CTAU_SCAN[np.argmax([acceptance(d, c0, c, d[k])[0] for c in CTAU_SCAN])] for k in ("in_csc", "in_dt", "in_box")}
        neff = acceptance(d, c0, opt["in_box"], d["in_box"])[1]
        sel = d["in_csc"] | d["in_dt"]
        f_late = np.mean(d["delay"][sel] > DELAY_NS) if sel.any() else np.nan
        pdgs = ",".join(f"{k}:{v}" for k, v in zip(*np.unique(d["dau_pdg"], return_counts=True)))
        print(f"{label(p):22s} {cell['in_box']:>16s} {cell['in_csc']:>13s} {cell['in_dt']:>13s} "
              f"{opt['in_csc']:12.0f} {opt['in_dt']:11.0f} {opt['in_box']:12.0f} {neff:8.0f} {np.mean(d['t']) / c0:7.2f} "
              f"{np.median(d['bg']):6.1f} {np.median(d['dau_dR']):6.2f} {f_late:13.2f} {pdgs}")
    print("\n<t>/ct0 should be ~1 (generator lifetime sanity). Neff = Kish effective events after reweighting to the box-optimal ctau.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(HERE, "plots"))
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    pts = load_points()
    table(pts)
    plot_acceptance(pts, args.out)
    plot_positions(pts, args.out)
    plot_boost_energy(pts, args.out)
    plot_dR_delay(pts, args.out)
    print(f"plots in {args.out}")
