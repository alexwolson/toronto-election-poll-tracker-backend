"""Score the repeat-firm anchor test (docs/research/repeat-firm-anchor-2026-10-13.md).

Written before any queue result was read. Applies the note's binding criteria, with the
maintainer's 3-seed decision (a fold is covered when 2 of 3 seeds cover it):

    uv run python -m docs.research.compact_mayoral.score_anchor DIR [DIR ...]

Reads every ``{P,V}-<horizon>-<campaign>-<seed>.json`` written by ``anchor_holdouts.py`` and
refuses to score unless all 84 fits (2 arms x 2 horizons x 7 folds x 3 seeds) are present.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ARMS = ("P", "V")
HORIZONS = (14, 7)
CAMPAIGNS = tuple(f"toronto_{y}" for y in (2003, 2006, 2010, 2014, 2018, 2022, 2023))
SEEDS = (20260921, 20260922, 20260923)
CRPS_TOLERANCE = 0.10  # points
COVERED_SEEDS = 2  # of 3


def load(dirs: list[Path]) -> dict:
    records = {}
    for d in dirs:
        for path in d.glob("*-*-toronto_*-*.json"):
            r = json.loads(path.read_text(encoding="utf-8"))
            key = (r["arm"], r["horizon"], r["holdout"], r["seed"])
            if key in records:
                raise SystemExit(f"duplicate fit {key}: {path}")
            records[key] = r
    missing = [
        (a, h, c, s)
        for a in ARMS
        for h in HORIZONS
        for c in CAMPAIGNS
        for s in SEEDS
        if (a, h, c, s) not in records
    ]
    if missing:
        raise SystemExit(f"{len(missing)} fits missing, e.g. {missing[:3]}")
    return records


def score(records: dict) -> dict:
    out = {"horizons": {}, "folds": []}
    for h in HORIZONS:
        arm = {}
        for a in ARMS:
            rows = [records[(a, h, c, s)] for c in CAMPAIGNS for s in SEEDS]
            covered = sum(
                sum(records[(a, h, c, s)]["covered_80"] for s in SEEDS) >= COVERED_SEEDS
                for c in CAMPAIGNS
            )
            changed = [
                records[(a, h, c, s)]
                for c in CAMPAIGNS
                for s in SEEDS
                if records[("V", h, c, s)]["rule_changes_fold"]
            ]
            arm[a] = {
                "mean_crps": float(np.mean([r["crps"] for r in rows])),
                "folds_covered": int(covered),
                "sampling_failures": int(sum(r["research_bar_failed"] for r in rows)),
                "retries": int(sum(r["retried"] for r in rows)),
                "anchor_error_changed_folds": float(np.mean([r["anchor_error"] for r in changed])),
                "changed_folds": sorted({r["holdout"] for r in changed}),
            }
        p, v = arm["P"], arm["V"]
        arm["checks"] = {
            "1_crps_within_tolerance": v["mean_crps"] <= p["mean_crps"] + CRPS_TOLERANCE,
            "2_coverage_at_least_P": v["folds_covered"] >= p["folds_covered"],
            "3_failures_at_most_P": v["sampling_failures"] <= p["sampling_failures"],
            "target_anchor_error_lower": v["anchor_error_changed_folds"]
            < p["anchor_error_changed_folds"],
        }
        out["horizons"][h] = arm
    do_no_harm = all(
        out["horizons"][h]["checks"][k]
        for h in HORIZONS
        for k in ("1_crps_within_tolerance", "2_coverage_at_least_P", "3_failures_at_most_P")
    )
    target = out["horizons"][14]["checks"]["target_anchor_error_lower"]
    out["do_no_harm_pass"] = do_no_harm
    out["target_14d_pass"] = target
    out["adopt"] = do_no_harm and target
    for h in HORIZONS:
        for c in CAMPAIGNS:
            row = {"horizon": h, "campaign": c}
            for a in ARMS:
                rs = [records[(a, h, c, s)] for s in SEEDS]
                row[a] = {
                    "crps": round(float(np.mean([r["crps"] for r in rs])), 2),
                    "q50": round(float(np.mean([r["q50"] for r in rs])), 1),
                    "covered": sum(r["covered_80"] for r in rs),
                    "anchor_error": round(float(np.mean([r["anchor_error"] for r in rs])), 2),
                }
            row["actual_margin"] = round(records[("P", h, c, SEEDS[0])]["actual_margin"], 1)
            row["rule_changes_fold"] = records[("V", h, c, SEEDS[0])]["rule_changes_fold"]
            out["folds"].append(row)
    return out


def main() -> None:
    dirs = [Path(a) for a in sys.argv[1:]]
    result = score(load(dirs))
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
