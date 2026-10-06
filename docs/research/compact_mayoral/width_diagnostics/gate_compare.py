"""Gate comparison: candidate variant (run suffix) vs a control, all shared folds, lenient bar.
usage: gate_compare.py <candidate_variant> [control_variant=dirichlet]"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from docs.research.compact_mayoral import evaluate as ev
import re
ev.RUN_NAME = re.compile(r"^holdout(\d+)-(toronto_\d{4})-([a-z_][a-z0-9_]*)$")  # allow digits in variant suffixes (phi160); metrics code untouched
cand, ctrl = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else "dirichlet")
runs = Path("docs/research/compact-mayoral-runs-2026-09-22")
folds = [m for p in sorted(runs.iterdir()) if p.is_dir() for m in [ev.fold_metrics(p)] if m]
def agg(sub):
    return dict(n=len(sub), crps=sum(f["crps"] for f in sub)/len(sub), cover=sum(bool(f["covered_80"]) for f in sub),
                nlogp=-sum(f["log_score"] for f in sub)/len(sub) if False else sum(f["log_score"] for f in sub)/len(sub),
                maxdiv=max(f["divergences"] for f in sub), rhat=max(f["worst_r_hat"] for f in sub),
                rmse=(sum(f["median_error"]**2 for f in sub)/len(sub))**0.5, width=sum(f["q90"]-f["q10"] for f in sub)/len(sub))
out = {}
for h in (39, 14):
    c = {f["campaign"]: f for f in folds if f["variant"] == ctrl and f["horizon"] == h}
    e = {f["campaign"]: f for f in folds if f["variant"] == cand and f["horizon"] == h}
    shared = sorted(set(c) & set(e)); missing = sorted(set(c) - set(e))
    print(f"=== {cand} vs {ctrl} @ {h} d: {len(shared)} shared folds" + (f" (candidate missing: {missing})" if missing else "") + " ===")
    for k in shared:
        a, b = c[k], e[k]
        print(f"  {k:13s} crps {100*a['crps']:5.2f} -> {100*b['crps']:5.2f}  width {100*(a['q90']-a['q10']):3.0f} -> {100*(b['q90']-b['q10']):3.0f}  miss {100*a['median_error']:+5.1f} -> {100*b['median_error']:+5.1f}  cov {str(a['covered_80'])[0]}->{str(b['covered_80'])[0]}  div {b['divergences']}")
    A, B = agg([c[k] for k in shared]), agg([e[k] for k in shared]); out[h] = (A, B)
    print(f"  mean CRPS {100*A['crps']:.2f} -> {100*B['crps']:.2f} | coverage {A['cover']}/{A['n']} -> {B['cover']}/{B['n']} | mean band width {100*A['width']:.0f} -> {100*B['width']:.0f} | RMSE {100*A['rmse']:.1f} -> {100*B['rmse']:.1f} | -logP(winner) {A['nlogp']:.3f} -> {B['nlogp']:.3f} | max div {B['maxdiv']} | R-hat {B['rhat']:.4f}")
A39, B39 = out[39]; A14, B14 = out[14]
r1 = B39["crps"] <= A39["crps"] + 0.0010 and B14["crps"] <= A14["crps"] + 0.0010
r2 = B39["cover"] >= 3 and B14["cover"] >= 6
r3 = max(B39["maxdiv"], B14["maxdiv"]) <= 4 and max(B39["rhat"], B14["rhat"]) < 1.02
print(f"GATE (lenient): CRPS no worse than +0.10 at each horizon: {r1} | coverage >=3/4 & >=6/7: {r2} | sampler: {r3} -> {'PASSES' if r1 and r2 and r3 else 'FAILS'}")
json.dump({"candidate": cand, "control": ctrl, "39": {"ctrl": A39, "cand": B39}, "14": {"ctrl": A14, "cand": B14}, "passes": bool(r1 and r2 and r3)}, open(runs / f"gate_{cand}_vs_{ctrl}.json", "w"), indent=1)
