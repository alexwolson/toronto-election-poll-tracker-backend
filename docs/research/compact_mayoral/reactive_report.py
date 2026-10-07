"""Issue 51 current-input report for a reactive fit (C2/C3): odds, two-way share, allocation,
keep fraction, C3 shift, house effects, movement and diagnostics.

Usage (from the backend root)::

    uv run python -m docs.research.compact_mayoral.reactive_report <run_dir> [...]
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import numpy as np

from .model import helmert_basis
from .readings import CURRENT_KEY
from .uniform_rule import current_campaign_under

KEY = CURRENT_KEY


def q(x, probs=(0.1, 0.5, 0.9)):
    return [float(v) for v in np.quantile(np.asarray(x, dtype=float), probs)]


def report(run: Path) -> dict:
    summary = json.loads((run / "summary.json").read_text(encoding="utf-8"))
    rec = summary["campaigns"][KEY]
    names = rec["candidates"]
    drops = tuple(summary["config"].get("drop_current_poll") or ())
    campaign = current_campaign_under("decided", election_date=date(2026, 10, 26), drop_polls=drops)
    firms = sorted({p.firm for p in campaign.polls})
    with np.load(run / "draws.npz") as d:
        named = np.asarray(d[f"{KEY}/named_result"]).reshape(-1, len(names))
        tail = np.asarray(d[f"{KEY}/tail"]).reshape(-1)
        firm = np.asarray(d[f"{KEY}/firm"])
    firm = firm.reshape(-1, *firm.shape[2:])  # (draws, F, K-1)
    lean = firm @ helmert_basis(len(names)).T  # (draws, F, K) log-ratio offsets
    c, b = names.index("Olivia Chow"), names.index("Brad Bradford")
    two_way = named[:, c] / (named[:, c] + named[:, b])
    p = float(np.median(two_way))
    # house lean on the Chow-Bradford two-way share, in points at the median two-way share
    house = {f: q(100 * p * (1 - p) * (lean[:, i, c] - lean[:, i, b])) for i, f in enumerate(firms)}
    winners = named.argmax(axis=1)
    full = named * (1 - tail[:, None])
    out = {
        "polls": rec["polls"],
        "win": {n: float((winners == i).mean()) for i, n in enumerate(names)},
        "chow_two_way": q(two_way),
        "full_ballot": {n: q(full[:, i]) for i, n in enumerate(names)},
        "pool": q(tail),
        "reactive": summary["reactive"][KEY],
        "house_lean_chow_minus_bradford_points": house,
        "weekly_movement_2026": [rec["weekly_movement"][k] for k in ("q10", "q50", "q90")],
        "diagnostics": {
            k: summary["diagnostics"][k] for k in ("divergences", "worst_r_hat", "min_ess")
        },
    }
    return out


def main(argv=None):
    for run in map(Path, sys.argv[1:] if argv is None else argv):
        r = report(run)
        print(f"=== {run.name} | polls {r['polls']} | diag {r['diagnostics']}")
        print("  win", {k.split()[-1]: round(100 * v, 1) for k, v in r["win"].items()})
        tw = r["chow_two_way"]
        print(f"  Chow two-way {100 * tw[1]:.1f} ({100 * tw[0]:.1f}-{100 * tw[2]:.1f})")
        for n, v in r["full_ballot"].items():
            print(f"  {n:16s} {100 * v[1]:5.1f} ({100 * v[0]:.1f}-{100 * v[2]:.1f})")
        for e in r["reactive"]:
            k = e["keep_fraction"]
            print(
                f"  exit {e['name']} day {e['day']}: keep {k['q50']:.3f} ({k['q10']:.3f}-{k['q90']:.3f})"
            )
            for n, a in e["allocation"].items():
                print(f"    allocation {n:16s} {a['q50']:.3f} ({a['q10']:.3f}-{a['q90']:.3f})")
            if "shift" in e:
                s = e["shift_sigma"]
                print(f"    shift sigma {s['q50']:.3f} ({s['q10']:.3f}-{s['q90']:.3f})")
                for n, a in e["shift"].items():
                    print(f"    shift {n:16s} {a['q50']:+.3f} ({a['q10']:+.3f}..{a['q90']:+.3f})")
        print(
            "  house lean on Chow two-way (points):",
            {
                f: f"{v[1]:+.1f} ({v[0]:+.1f}..{v[2]:+.1f})"
                for f, v in r["house_lean_chow_minus_bradford_points"].items()
            },
        )
        print(
            "  2026 weekly movement x100:", [round(100 * x, 2) for x in r["weekly_movement_2026"]]
        )
        (run / "reactive_report.json").write_text(json.dumps(r, indent=1) + "\n")


if __name__ == "__main__":
    main()
