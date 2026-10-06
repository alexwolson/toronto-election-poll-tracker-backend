"""Shared-fold comparison for the era-rule pre-registration (2026-09-22 note).
Current corpus = runs named holdout<H>-<race>-dirichlet; era corpus = ...-dirichlet_era."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from docs.research.compact_mayoral import evaluate as ev

runs = Path("docs/research/compact-mayoral-runs-2026-09-22")
folds = [m for p in sorted(runs.iterdir()) if p.is_dir() for m in [ev.fold_metrics(p)] if m]
shared = {39: ["toronto_2010", "toronto_2014", "toronto_2018", "toronto_2023"],
          14: ["toronto_2010", "toronto_2014", "toronto_2018", "toronto_2022", "toronto_2023"]}

def ks(pits):
    pits = sorted(pits); n = len(pits)
    return max(max(abs((i + 1) / n - p), abs(i / n - p)) for i, p in enumerate(pits))

def agg(sub):
    cand = [p for f in sub for p in f["candidate_pits"]]
    return dict(n=len(sub), crps=sum(f["crps"] for f in sub) / len(sub),
                cover=sum(bool(f["covered_80"]) for f in sub), logp=sum(f["log_score"] for f in sub) / len(sub),
                ks=ks(cand), maxdiv=max(f["divergences"] for f in sub), rhat=max(f["worst_r_hat"] for f in sub),
                rmse=(sum(f["median_error"] ** 2 for f in sub) / len(sub)) ** 0.5)

out = {}
for variant in ("dirichlet", "dirichlet_era"):
    out[variant] = {}
    for h, races in shared.items():
        sub = [f for f in folds if f["variant"] == variant and f["horizon"] == h and f["campaign"] in races]
        assert len(sub) == len(races), (variant, h, [f["campaign"] for f in sub])
        out[variant][h] = agg(sub)
        print(f"=== {variant:14s} @ {h:2d} d  (shared folds) ===")
        for f in sorted(sub, key=lambda r: r["campaign"]):
            print(f"  {f['campaign']:13s} band {100*f['q10']:+6.1f}..{100*f['q90']:+6.1f} (w {100*(f['q90']-f['q10']):3.0f})  med {100*f['q50']:+6.1f}  actual {100*f['actual_margin']:+6.1f}  miss {100*f['median_error']:+6.1f}  crps {100*f['crps']:5.2f}  cov {str(f['covered_80']):5s} pit {f['pit']:.2f}  logP {f['log_score']:.3f}  div {f['divergences']}")
        a = out[variant][h]
        print(f"  -> mean CRPS {100*a['crps']:.2f} pts | coverage {a['cover']}/{a['n']} | RMSE of median {100*a['rmse']:.1f} | mean -logP(winner) {-a['logp']:.3f} | candidate KS {a['ks']:.3f} | max div {a['maxdiv']} | worst R-hat {a['rhat']:.4f}\n")

c, e = out["dirichlet"], out["dirichlet_era"]
rule1 = all(e[h]["crps"] < c[h]["crps"] for h in (39, 14))
rule2 = e[39]["cover"] >= 3 and e[14]["cover"] >= 4
rule3 = all(e[h]["maxdiv"] <= 4 and e[h]["rhat"] < 1.02 for h in (39, 14))
print("DECISION RULE  1 CRPS lower at both horizons:", rule1, f"(39 d {100*e[39]['crps']:.2f} vs {100*c[39]['crps']:.2f}; 14 d {100*e[14]['crps']:.2f} vs {100*c[14]['crps']:.2f})")
print("               2 coverage >=3/4 and >=4/5:", rule2, f"({e[39]['cover']}/4, {e[14]['cover']}/5)")
print("               3 <=4 div/fold, R-hat<1.02:", rule3)
print("VERDICT:", "ADOPT" if rule1 and rule2 and rule3 else "NOT ADOPTED (sensitivity only)")
json.dump({"shared_folds": shared, "aggregates": {v: {str(h): a for h, a in d.items()} for v, d in out.items()},
           "rules": {"crps_both": rule1, "coverage": rule2, "sampler": rule3}, "adopt": rule1 and rule2 and rule3},
          open(runs / "era_evaluation.json", "w"), indent=1)
