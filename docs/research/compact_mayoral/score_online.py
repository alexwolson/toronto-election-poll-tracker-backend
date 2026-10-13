"""Score the non-online anchor do-no-harm test (docs/research/online-free-anchor-2026-10-13.md).

Written before any arm O fit ran:

    uv run python -m docs.research.compact_mayoral.score_online --p DIR [DIR ...] --o DIR [DIR ...]

Changed folds are scored at seeds 20260921-20260923, unchanged folds at 20260921 only; P and O
are compared on the identical (fold, seed) set. Refuses to score when any required fit is missing.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

CAMPAIGNS = tuple(f"toronto_{y}" for y in (2003, 2006, 2010, 2014, 2018, 2022, 2023))
CHANGED = {
    14: {"toronto_2006", "toronto_2010", "toronto_2014", "toronto_2023"},
    7: {"toronto_2006", "toronto_2010", "toronto_2014"},
}
ALL_SEEDS = (20260921, 20260922, 20260923)
CHECK_SEED = (20260921,)
CRPS_TOLERANCE = 0.10


def load(dirs: list[Path], arm: str) -> dict:
    out = {}
    for d in dirs:
        for path in d.glob(f"{arm}-*-toronto_*-*.json"):
            r = json.loads(path.read_text(encoding="utf-8"))
            key = (r["horizon"], r["holdout"], r["seed"])
            if key in out:
                raise SystemExit(f"duplicate {arm} fit {key}: {path}")
            out[key] = r
    return out


def plan() -> list[tuple[int, str, int]]:
    return [
        (h, c, s)
        for h in (14, 7)
        for c in CAMPAIGNS
        for s in (ALL_SEEDS if c in CHANGED[h] else CHECK_SEED)
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--p", type=Path, nargs="+", required=True)
    parser.add_argument("--o", type=Path, nargs="+", required=True)
    args = parser.parse_args()
    p, o = load(args.p, "P"), load(args.o, "O")
    keys = plan()
    missing = [("P", k) for k in keys if k not in p] + [("O", k) for k in keys if k not in o]
    if missing:
        raise SystemExit(f"{len(missing)} fits missing, e.g. {missing[:3]}")
    for k in keys:
        if (k[1] in CHANGED[k[0]]) != o[k]["rule_changes_fold"]:
            raise SystemExit(f"fold {k} disagrees with the pre-registered changed list")
    result = {"horizons": {}, "folds": []}
    for h in (14, 7):
        hk = [k for k in keys if k[0] == h]
        arms = {}
        for name, recs in (("P", p), ("O", o)):
            covered = 0
            for c in CAMPAIGNS:
                seeds = [k for k in hk if k[1] == c]
                need = 2 if len(seeds) == 3 else 1
                covered += sum(recs[k]["covered_80"] for k in seeds) >= need
            arms[name] = {
                "mean_crps": float(np.mean([recs[k]["crps"] for k in hk])),
                "folds_covered": int(covered),
                "sampling_failures": int(sum(recs[k]["research_bar_failed"] for k in hk)),
                "retries": int(sum(recs[k]["retried"] for k in hk)),
            }
        arms["checks"] = {
            "1_crps_within_tolerance": arms["O"]["mean_crps"]
            <= arms["P"]["mean_crps"] + CRPS_TOLERANCE,
            "2_coverage_at_least_P": arms["O"]["folds_covered"] >= arms["P"]["folds_covered"],
            "3_failures_at_most_P": arms["O"]["sampling_failures"]
            <= arms["P"]["sampling_failures"],
        }
        result["horizons"][h] = arms
        for c in CAMPAIGNS:
            seeds = [k for k in hk if k[1] == c]
            result["folds"].append(
                {
                    "horizon": h,
                    "campaign": c,
                    "changed": c in CHANGED[h],
                    "seeds": len(seeds),
                    "P_crps": round(float(np.mean([p[k]["crps"] for k in seeds])), 2),
                    "O_crps": round(float(np.mean([o[k]["crps"] for k in seeds])), 2),
                    "P_q50": round(float(np.mean([p[k]["q50"] for k in seeds])), 1),
                    "O_q50": round(float(np.mean([o[k]["q50"] for k in seeds])), 1),
                    "actual": round(p[seeds[0]]["actual_margin"], 1),
                }
            )
    result["pass"] = all(all(result["horizons"][h]["checks"].values()) for h in (14, 7))
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
