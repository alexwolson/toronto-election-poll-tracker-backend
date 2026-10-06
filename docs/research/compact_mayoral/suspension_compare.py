"""Pre-registered held-out comparison for the Suspended Campaign signal (backend issue 43).

Usage (from the backend root)::

    uv run python -m docs.research.compact_mayoral.suspension_compare <runs_dir>

Baseline folds are ``holdout<H>-<race>-dirichlet``; S1 folds ``...-dirichlet_joint``.
S2 is computed here from the baseline folds' draws: for a held-out campaign with a
suspension known at its cutoff (election day minus the horizon), each election-day
named draw is passed through ``suspend`` with a kept fraction drawn from the table's
log-normal (Toronto 2010's rows excluded when 2010 is held out); every other fold is
the baseline fold unchanged. Rules (the 2026-09-22 rule, unchanged): mean leader-margin
CRPS no worse than +0.10 points at each horizon; 80% coverage >= 3/4 at 39 days and
>= 6/7 at 14; at most 4 divergences per fold and worst R-hat < 1.02. Order: S1, then S2.
Never reads the 2026 forecast.
"""

from __future__ import annotations

import json
import math
import sys
from datetime import timedelta
from pathlib import Path

import numpy as np

from . import evaluate as ev
from .readings import historical_campaigns
from .suspensions import keep_distribution, load_suspensions, suspend

SHARED = {
    39: ["toronto_2010", "toronto_2014", "toronto_2018", "toronto_2023"],
    14: [
        "toronto_2003",
        "toronto_2006",
        "toronto_2010",
        "toronto_2014",
        "toronto_2018",
        "toronto_2022",
        "toronto_2023",
    ],
}
SEED = 20260921


def s2_fold(run_dir: Path, base: dict, rows: list[dict], election_dates: dict) -> dict:
    """The baseline fold with S2 applied to the held-out campaign's election-day draws."""
    campaign, horizon = base["campaign"], base["horizon"]
    cutoff = election_dates[campaign] - timedelta(days=horizon)
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    record = summary["campaigns"][campaign]
    names = record["candidates"]
    found = tuple(
        sorted(
            names.index(r["candidate_name"])
            for r in rows
            if r["election_cycle_id"] == campaign
            and r["announcement_date"] <= cutoff
            and r["candidate_name"] in names
        )
    )
    if not found:
        return {**base, "variant": "dirichlet_s2", "s2_applied": []}
    exclude = ("toronto_2010",) if campaign == "toronto_2010" else ()
    mu, sigma = keep_distribution(rows, exclude_cycles=exclude)
    with np.load(run_dir / "draws.npz") as draws:
        named = np.asarray(draws[f"{campaign}/named_result"])
    named = named.reshape(-1, named.shape[-1])
    keep = np.exp(np.random.default_rng(SEED).normal(mu, sigma, size=(named.shape[0], 1)))
    named = suspend(named, found, np.minimum(keep, 1.0))
    held = record["holdout"]
    truth = np.asarray(held["actual_named_shares"], dtype=float)
    lead, second = (names.index(n) for n in record["leaders"])
    margin = named[:, lead] - named[:, second]
    actual = float(truth[lead] - truth[second])
    q10, q50, q90 = (float(np.quantile(margin, q)) for q in (0.1, 0.5, 0.9))
    winners = named.argmax(axis=1)
    p_winner = max(float((winners == int(truth.argmax())).mean()), 1.0 / named.shape[0])
    return {
        **base,
        "variant": "dirichlet_s2",
        "s2_applied": [names[i] for i in found],
        "s2_keep_log_normal": [mu, sigma],
        "q10": q10,
        "q50": q50,
        "q90": q90,
        "median_error": q50 - actual,
        "pit": float((margin <= actual).mean()),
        "covered_80": bool(q10 <= actual <= q90),
        "crps": ev.crps(margin, actual),
        "log_score": -math.log(p_winner),
        "candidate_pits": [float((named[:, i] <= truth[i]).mean()) for i in range(len(truth))],
    }


def aggregate(folds: list[dict]) -> dict:
    return {
        "n": len(folds),
        "crps": float(np.mean([f["crps"] for f in folds])),
        "cover": sum(bool(f["covered_80"]) for f in folds),
        "maxdiv": max(f["divergences"] for f in folds),
        "rhat": max(f["worst_r_hat"] for f in folds),
        "rmse": float(np.sqrt(np.mean([f["median_error"] ** 2 for f in folds]))),
        "logp": float(np.mean([f["log_score"] for f in folds])),
        "ks": ev.ks_to_uniform([p for f in folds for p in f["candidate_pits"]]),
    }


def rules(variant: dict, base: dict) -> dict:
    crps = all(variant[h]["crps"] <= base[h]["crps"] + 0.0010 for h in (39, 14))
    cover = variant[39]["cover"] >= 3 and variant[14]["cover"] >= 6
    sampler = all(variant[h]["maxdiv"] <= 4 and variant[h]["rhat"] < 1.02 for h in (39, 14))
    return {
        "1_crps": crps,
        "2_coverage": cover,
        "3_sampler": sampler,
        "pass": crps and cover and sampler,
    }


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    runs = Path(argv[0])
    folds = [m for p in sorted(runs.iterdir()) if p.is_dir() for m in [ev.fold_metrics(p)] if m]
    rows = load_suspensions()
    dates = {k: c.election_date for k, c in historical_campaigns().items()}
    by = {"dirichlet": {}, "dirichlet_joint": {}, "dirichlet_s2": {}}
    per_fold = {"dirichlet": [], "dirichlet_joint": [], "dirichlet_s2": []}
    for h, races in SHARED.items():
        base = {
            f["campaign"]: f for f in folds if f["variant"] == "dirichlet" and f["horizon"] == h
        }
        joint = {
            f["campaign"]: f
            for f in folds
            if f["variant"] == "dirichlet_joint" and f["horizon"] == h
        }
        assert set(races) <= set(base), ("baseline", h, sorted(base))
        assert set(races) <= set(joint), ("joint", h, sorted(joint))
        s2 = {r: s2_fold(runs / base[r]["run"], base[r], rows, dates) for r in races}
        for name, sub in (("dirichlet", base), ("dirichlet_joint", joint), ("dirichlet_s2", s2)):
            chosen = [sub[r] for r in races]
            by[name][h] = aggregate(chosen)
            per_fold[name].extend(chosen)
    for name in by:
        print(f"=== {name}")
        for f in sorted(per_fold[name], key=lambda r: (-r["horizon"], r["campaign"])):
            extra = f" S2 on {f['s2_applied']}" if f.get("s2_applied") else ""
            print(
                f"  {f['horizon']:>2d} {f['campaign']:13s} band {100 * f['q10']:+6.1f}..{100 * f['q90']:+6.1f}"
                f"  med {100 * f['q50']:+6.1f}  actual {100 * f['actual_margin']:+6.1f}  crps {100 * f['crps']:5.2f}"
                f"  cov {f['covered_80']!s:5s}  div {f['divergences']}  R-hat {f['worst_r_hat']:.4f}"
                f"  {f['scales']}{extra}"
            )
        for h in (39, 14):
            a = by[name][h]
            print(
                f"  -> {h} d: mean CRPS {100 * a['crps']:.2f} | coverage {a['cover']}/{a['n']} | "
                f"max div {a['maxdiv']} | worst R-hat {a['rhat']:.4f} | RMSE {100 * a['rmse']:.1f} | "
                f"-logP {a['logp']:.3f} | cand KS {a['ks']:.3f}"
            )
    verdict_s1 = rules(by["dirichlet_joint"], by["dirichlet"])
    verdict_s2 = rules(by["dirichlet_s2"], by["dirichlet"])
    adopted = "S1" if verdict_s1["pass"] else ("S2" if verdict_s2["pass"] else "neither")
    print("S1 rules:", verdict_s1)
    print("S2 rules:", verdict_s2, "(consulted only if S1 fails)")
    print("ADOPTED:", adopted)
    out = {
        "aggregates": {n: {str(h): a for h, a in d.items()} for n, d in by.items()},
        "folds": per_fold,
        "s1": verdict_s1,
        "s2": verdict_s2,
        "adopted": adopted,
    }
    (runs / "suspension_evaluation.json").write_text(json.dumps(out, indent=1) + "\n")
    return out


if __name__ == "__main__":
    main()
