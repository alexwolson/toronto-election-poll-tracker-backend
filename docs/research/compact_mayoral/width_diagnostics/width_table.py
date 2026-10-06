"""One row per run: phi posterior, 2026 election-day decomposition (sd in points), band width."""
import json, sys, numpy as np
from pathlib import Path
R = Path("docs/research/compact-mayoral-runs-2026-09-22")
def flat(z, k):
    a = np.asarray(z[k]); return a.reshape(-1, a.shape[-1]) if a.ndim == 3 else a.reshape(-1)
def row(name):
    run = R / name
    if not (run / "draws.npz").exists(): return None
    z = np.load(run / "draws.npz"); s = json.load(open(run / "summary.json"))
    phi = flat(z, "phi_election") if "phi_election" in z else np.full(1, np.nan)
    p = "toronto-2026/"; cur, sup, res, tail = (flat(z, p+k) for k in ("current","election_support","named_result","tail"))
    m = lambda x: 100 * (x[:, 0] - x[:, 1]) * (1 - tail)
    now, at, fin = m(cur), m(sup), m(res)
    parts = [now - np.median(now), at - now, fin - at]; v = [float(np.var(x)) for x in parts]
    w = s["campaigns"]["toronto-2026"]["win_probability"]
    q = np.quantile(fin, [.1, .9])
    return dict(name=name, phi=np.quantile(phi, [.1, .5, .9]), sd=[x.std() for x in parts], total=fin.std(), share_ed=v[2]/sum(v), band=q[1]-q[0], chow=100*w["Olivia Chow"], div=s["diagnostics"]["divergences"])
names = ["v2-all-population-dirichlet", "all-2026-dirichlet_era"] + sorted(p.name for p in R.iterdir() if p.is_dir() and p.name.startswith("wd-"))
print(f"{'run':28s} {'phi q10/q50/q90':>18s}  {'sd now':>6s} {'sd move':>7s} {'sd eday':>7s} {'sd total':>8s} {'eday share':>10s} {'band':>5s} {'Chow':>5s} div")
base = None
for n in names:
    r = row(n)
    if not r: print(f"{n:28s} (no draws yet)"); continue
    if base is None: base = r
    print(f"{r['name']:28s} {r['phi'][0]:5.0f}/{r['phi'][1]:4.0f}/{r['phi'][2]:4.0f}   {r['sd'][0]:6.1f} {r['sd'][1]:7.1f} {r['sd'][2]:7.1f} {r['total']:8.1f} {r['share_ed']:10.2f} {r['band']:5.0f} {r['chow']:5.1f} {r['div']:3d}"
          + (f"   eday var vs baseline {100*(r['sd'][2]**2/base['sd'][2]**2 - 1):+5.0f}%" if r is not base else ""))
