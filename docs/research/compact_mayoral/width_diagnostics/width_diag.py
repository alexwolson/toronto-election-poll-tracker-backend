"""Diagnostics from saved draws: 2026 width decomposition, per-campaign residuals that inform phi."""
import json, sys, numpy as np
from pathlib import Path
run = Path(sys.argv[1]); z = np.load(run / "draws.npz"); s = json.load(open(run / "summary.json"))
phi = np.asarray(z["phi_election"]).reshape(-1)
print(f"{run.name}: phi_election q10/q50/q90 = {np.quantile(phi,[.1,.5,.9]).round(1)}  draws {phi.size}")
# --- 2026 decomposition (leader minus runner-up, full-ballot points)
def flat(k):
    a = np.asarray(z[k]); return a.reshape(-1, a.shape[-1]) if a.ndim == 3 else a.reshape(-1)
p = "toronto-2026/"; cur, sup, res, tail = (flat(p+k) for k in ("current","election_support","named_result","tail"))
names = s["campaigns"]["toronto-2026"]["candidates"]; L, R = 0, 1
def margin(x): return 100 * (x[:, L] - x[:, R]) * (1 - tail)
now, at, fin = margin(cur), margin(sup), margin(res)
parts = {"polls_today": now - np.median(now), "campaign_movement": at - now, "election_day": fin - at}
v = {k: float(np.var(x)) for k, x in parts.items()}; tot = float(np.var(fin))
print("2026 margin: election sd %.1f, 80%% band %.1f..%.1f (w %.0f)" % (fin.std(), *np.quantile(fin,[.1,.9]), np.diff(np.quantile(fin,[.1,.9]))[0]))
for k, x in parts.items(): print(f"   {k:18s} sd {x.std():5.1f}  share {v[k]/sum(v.values()):.3f}")
mix26 = np.asarray(z[p+"election_mixing"]).reshape(-1); print(f"   2026 mixing q10/q50/q90 {np.quantile(mix26,[.1,.5,.9]).round(2)}  (prior Gamma(2.5,2.5))")
# analytic mapping: Var(margin) ≈ (muC+muB-(muC-muB)^2)/(phi*m+1) at the median support
mu = np.median(sup, axis=0); base = (mu[L] + mu[R] - (mu[L]-mu[R])**2) * (1 - np.median(tail))**2
for ph in (20, 42, 53, 80, 120, 200): print(f"   analytic election-day margin sd at phi={ph:3d}, mixing=1: {100*np.sqrt(base/(ph+1)):.1f}")
# --- historical campaigns: which residuals carry phi?
print("\nper-campaign: mixing posterior, residual z-scores of the observed result vs posterior election_support (at phi median), implied phi_c")
camps = [k for k in s["campaigns"] if k != "toronto-2026"]
for c in camps:
    q = c + "/"; sup_c = flat(q+"election_support"); mix = flat(q+"election_mixing")
    obs = np.asarray(s["campaigns"][c].get("holdout", {}).get("actual_named_shares") or [])
    if obs.size == 0:
        # observed result is not in summary for in-sample campaigns: read from readings
        sys.path.insert(0, str(Path.cwd())); from docs.research.compact_mayoral import readings
        obs = np.asarray(readings.historical_campaigns()[c].outcome_shares)
    m = sup_c.mean(axis=0); sd_c = np.sqrt(m*(1-m)/(np.median(phi)*np.median(mix)+1))
    zsc = (obs - m) / sd_c
    # method-of-moments phi from this campaign's own residual (mixing=1)
    phi_c = float(np.sum(m*(1-m)) / np.sum((obs-m)**2) - 1)
    nm = s["campaigns"][c]["candidates"]
    top = sorted(range(len(nm)), key=lambda i: -obs[i])[:3]
    print(f"  {c:13s} K={len(nm):2d} mixing q50 {np.median(mix):.2f} (q10 {np.quantile(mix,.1):.2f})  implied phi_c {phi_c:6.0f}  |z| mean {np.abs(zsc).mean():.2f} max {np.abs(zsc).max():.2f}  "
          + "; ".join(f"{nm[i].split()[-1]} {100*m[i]:.0f}->{100*obs[i]:.0f} (z{zsc[i]:+.1f})" for i in top)
          + (f"; minors |z| mean {np.abs(zsc[[i for i in range(len(nm)) if i not in top]]).mean():.2f}" if len(nm) > 3 else ""))
