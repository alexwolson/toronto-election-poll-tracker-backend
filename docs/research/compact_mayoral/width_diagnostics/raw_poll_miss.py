"""Per-race record: last-three-poll leader margin at a horizon vs the count, plus the
dirichlet model's held-out band at the same horizon (from the 09-22 run's evaluation.json)."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from docs.research.compact_mayoral import readings

ev = json.loads(Path("docs/research/compact-mayoral-runs-2026-09-22/evaluation.json").read_text())
folds = ev["folds"]
if isinstance(folds, dict):
    k0 = next(iter(folds)); print("fold keys sample:", k0, "->", list(folds[k0].keys())[:12] if isinstance(folds[k0], dict) else type(folds[k0]).__name__)
else:
    print("fold keys sample:", list(folds[0].keys()))
camps = readings.historical_campaigns()
print(f"{len(camps)} campaigns\n")

def table(horizon):
    rows = []
    for key, c in sorted(camps.items()):
        try:
            h = readings.with_horizon(c, horizon)
        except ValueError:
            continue
        L, R = h.leaders
        usable = [p for p in sorted(h.polls, key=lambda p: p.days_before_election) if L in p.offered and R in p.offered]
        last3 = usable[:3]
        pm = sum(100*(p.shares[p.offered.index(L)] - p.shares[p.offered.index(R)]) for p in last3)/len(last3)
        o = c.outcome_shares; am = 100*(o[L]-o[R])
        # actual top two by the count, for the runner-up-collapse check
        top = sorted(range(len(o)), key=lambda i: -o[i])[:2]
        rows.append(dict(key=key, n=len(h.polls), last=min(p.days_before_election for p in last3),
                         L=c.names[L].split()[-1], R=c.names[R].split()[-1], polled=pm, actual=am, miss=am-pm,
                         real_top2=[c.names[i].split()[-1] for i in top]))
    return rows

for horizon in (39, 14):
    rows = table(horizon)
    print(f"=== horizon {horizon} d: leaders as known then, last-3-poll margin vs count ===")
    print(f"{'race':13s} {'polls':>5s} {'last@':>5s} {'leader vs runner-up':24s} {'polled':>7s} {'actual':>7s} {'miss':>6s}  count's top two")
    for r in rows:
        print(f"{r['key']:13s} {r['n']:5d} {r['last']:5d} {r['L']+' vs '+r['R']:24s} {r['polled']:+7.1f} {r['actual']:+7.1f} {r['miss']:+6.1f}  {', '.join(r['real_top2'])}")
    m = [r['miss'] for r in rows]; rmse = (sum(x*x for x in m)/len(m))**0.5
    print(f"n={len(m)}  RMSE {rmse:.1f}  mean abs {sum(abs(x) for x in m)/len(m):.1f}  median abs {sorted(abs(x) for x in m)[len(m)//2]:.1f}\n")
