"""Pre-registered held-out evaluation of the discrepancy-scaling variants (2026-09-22).

Usage (from the backend root)::

    uv run --no-project python -m docs.research.compact_mayoral.evaluate <runs_dir> [control]

Reads every ``<runs_dir>/holdout<H>-<campaign>-<variant>/`` (``summary.json`` plus
``draws.npz``), computes the metrics named in
``docs/research/compact-mayoral-discrepancy-scaling-2026-09-22.md`` for the held-out
campaign only, aggregates them per (variant, horizon), and applies that note's
decision rule against the control variant (default ``isotropic``). Writes
``<runs_dir>/evaluation.json``.

Pre-registration hygiene: this module never reads or prints the 2026 forecast that
every fit also carries.
"""

from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

import numpy as np

RUN_NAME = re.compile(r"^holdout(\d+)-(toronto_\d{4})-([a-z_]+)$")
CRPS_TOLERANCE = 0.02  # criterion 3: within 2% of the control at the secondary horizon
MAX_DIVERGENCES_PER_FOLD = 4  # criterion 1, round 2: at most 4 divergent transitions per 4,000


def crps(sample, truth: float) -> float:
    """Empirical CRPS: E|X - y| - E|X - X'| / 2, in the sample's units."""
    x = np.sort(np.asarray(sample, dtype=float))
    n = x.size
    term1 = float(np.abs(x - truth).mean())
    i = np.arange(1, n + 1)
    pairwise = (2.0 / n**2) * float(np.sum((2 * i - n - 1) * x))  # E|X - X'|
    return term1 - 0.5 * pairwise


def ks_to_uniform(pits) -> float:
    """Kolmogorov–Smirnov distance between the PITs' empirical CDF and Uniform(0, 1)."""
    u = np.sort(np.asarray(pits, dtype=float))
    n = u.size
    if n == 0:
        return math.nan
    i = np.arange(1, n + 1)
    return float(max(np.max(i / n - u), np.max(u - (i - 1) / n)))


def fold_metrics(run_dir: Path) -> dict | None:
    match = RUN_NAME.match(run_dir.name)
    if not match or not (run_dir / "summary.json").exists():
        return None
    horizon, campaign, variant = int(match[1]), match[2], match[3]
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    record = summary["campaigns"][campaign]
    held = record["holdout"]
    names = record["candidates"]
    lead, second = (names.index(n) for n in record["leaders"])
    with np.load(run_dir / "draws.npz") as draws:
        named = np.asarray(draws[f"{campaign}/named_result"])
    named = named.reshape(-1, named.shape[-1])
    margin = named[:, lead] - named[:, second]
    truth = np.asarray(held["actual_named_shares"], dtype=float)
    actual_margin = float(truth[lead] - truth[second])
    p_winner = max(float(held["p_actual_winner"]), 1.0 / named.shape[0])
    scales = summary["shared_scales"]
    return {
        "run": run_dir.name,
        "horizon": horizon,
        "campaign": campaign,
        "variant": variant,
        "polls": held["polls_used"],
        "leaders": record["leaders"],
        "actual_margin": actual_margin,
        "q10": float(np.quantile(margin, 0.10)),
        "q50": float(np.quantile(margin, 0.50)),
        "q90": float(np.quantile(margin, 0.90)),
        "median_error": float(np.quantile(margin, 0.50)) - actual_margin,
        "pit": float(held["leader_margin_pit"]),
        "covered_80": bool(held["leader_margin_covered_80"]),
        "crps": crps(margin, actual_margin),
        "log_score": -math.log(p_winner),
        "candidate_pits": [float(p) for p in held["pit"]],
        "divergences": int(summary["diagnostics"]["divergences"]),
        "worst_r_hat": float(summary["diagnostics"]["worst_r_hat"]),
        "scales": {
            k: round(float(v["mean"]), 3)
            for k, v in scales.items()
            if k in ("tau_election", "tau_lead", "tau_rest", "gamma_election", "phi_election")
        },
    }


def aggregate(folds: list[dict]) -> dict:
    return {
        "n": len(folds),
        "mean_crps": float(np.mean([f["crps"] for f in folds])),
        "rmse_median": float(np.sqrt(np.mean([f["median_error"] ** 2 for f in folds]))),
        "coverage_80": sum(f["covered_80"] for f in folds),
        "pits": sorted(round(f["pit"], 2) for f in folds),
        "mean_log_score": float(np.mean([f["log_score"] for f in folds])),
        "candidate_ks": ks_to_uniform([p for f in folds for p in f["candidate_pits"]]),
        "divergences": sum(f["divergences"] for f in folds),
        "worst_r_hat": max(f["worst_r_hat"] for f in folds),
    }


def decide(by_variant: dict[str, dict], control: str) -> dict[str, dict]:
    """Apply the pre-registered rule; every criterion is reported, not just the verdict."""
    ctrl = by_variant[control]
    verdicts = {}
    for variant, agg in by_variant.items():
        if variant == control:
            continue
        both = {h: agg.get(h) for h in ("39", "14")}
        if any(v is None for v in both.values()) or any(ctrl.get(h) is None for h in ("39", "14")):
            verdicts[variant] = {"adopt": False, "reason": "missing a horizon"}
            continue
        # Criterion 1 (round 2 wording, pre-registered 2026-09-22): at most
        # MAX_DIVERGENCES_PER_FOLD divergent transitions in every fold and R-hat < 1.01.
        clean = all(
            f["divergences"] <= MAX_DIVERGENCES_PER_FOLD and f["worst_r_hat"] < 1.01
            for h in ("39", "14")
            for f in agg[f"folds_{h}"]
        )
        better_39 = both["39"]["mean_crps"] < ctrl["39"]["mean_crps"]
        held_14 = both["14"]["mean_crps"] <= ctrl["14"]["mean_crps"] * (1 + CRPS_TOLERANCE)
        pooled = ks_to_uniform(
            [p for h in ("39", "14") for f in agg[f"folds_{h}"] for p in f["candidate_pits"]]
        )
        pooled_ctrl = ks_to_uniform(
            [p for h in ("39", "14") for f in ctrl[f"folds_{h}"] for p in f["candidate_pits"]]
        )
        calibrated = pooled <= pooled_ctrl
        verdicts[variant] = {
            "1_samples_cleanly": clean,
            "2_better_crps_39d": better_39,
            "3_crps_14d_within_tolerance": held_14,
            "4_candidate_calibration_not_worse": calibrated,
            "candidate_ks_pooled": round(pooled, 3),
            "control_candidate_ks_pooled": round(pooled_ctrl, 3),
            "adopt": clean and better_39 and held_14 and calibrated,
        }
    return verdicts


def render_folds(folds: list[dict]) -> str:
    head = (
        f"{'H':>3s} {'campaign':13s} {'variant':15s} {'n':>2s} {'leaders':22s} {'actual':>7s} "
        f"{'p10':>6s} {'p50':>6s} {'p90':>6s} {'PIT':>5s} {'80%':>4s} {'CRPS':>5s} {'-logP':>6s} "
        f"{'div':>4s} {'scales'}"
    )
    lines = [head, "-" * len(head)]
    for f in sorted(folds, key=lambda r: (-r["horizon"], r["campaign"], r["variant"])):
        leaders = " / ".join(n.split()[-1] for n in f["leaders"])
        scales = " ".join(f"{k.replace('_election', '')}={v}" for k, v in f["scales"].items())
        lines.append(
            f"{f['horizon']:>3d} {f['campaign']:13s} {f['variant']:15s} {f['polls']:>2d} "
            f"{leaders:22s} {100 * f['actual_margin']:>+7.1f} {100 * f['q10']:>+6.1f} "
            f"{100 * f['q50']:>+6.1f} {100 * f['q90']:>+6.1f} {f['pit']:>5.2f} "
            f"{'yes' if f['covered_80'] else 'NO':>4s} {100 * f['crps']:>5.1f} "
            f"{f['log_score']:>6.2f} {f['divergences']:>4d} {scales}"
        )
    return "\n".join(lines)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        sys.exit("usage: evaluate.py <runs_dir> [control_variant]")
    runs_dir = Path(argv[0])
    control = argv[1] if len(argv) > 1 else "isotropic"
    folds = [m for p in sorted(runs_dir.iterdir()) if p.is_dir() for m in [fold_metrics(p)] if m]
    if not folds:
        sys.exit(f"no held-out runs under {runs_dir}")
    print(render_folds(folds))
    by_variant: dict[str, dict] = {}
    for variant in sorted({f["variant"] for f in folds}):
        by_variant[variant] = {}
        for horizon in sorted({f["horizon"] for f in folds}, reverse=True):
            sub = [f for f in folds if f["variant"] == variant and f["horizon"] == horizon]
            if sub:
                by_variant[variant][str(horizon)] = aggregate(sub)
                by_variant[variant][f"folds_{horizon}"] = sub
    print()
    print(
        f"{'variant':15s} {'H':>3s} {'n':>2s} {'mean CRPS':>9s} {'RMSE med':>8s} {'80% cov':>7s} "
        f"{'-logP':>6s} {'cand KS':>7s} {'div':>4s} {'R-hat':>6s}  PITs"
    )
    for variant, per in by_variant.items():
        for horizon in ("39", "14"):
            a = per.get(horizon)
            if not a:
                continue
            print(
                f"{variant:15s} {horizon:>3s} {a['n']:>2d} {100 * a['mean_crps']:>9.2f} "
                f"{100 * a['rmse_median']:>8.1f} {a['coverage_80']:>4d}/{a['n']:<2d} "
                f"{a['mean_log_score']:>6.2f} {a['candidate_ks']:>7.2f} {a['divergences']:>4d} "
                f"{a['worst_r_hat']:>6.3f}  {a['pits']}"
            )
    verdicts = decide(by_variant, control) if control in by_variant else {}
    print()
    for variant, verdict in verdicts.items():
        print(f"{variant}: {json.dumps(verdict)}")
    output = {
        "control": control,
        "folds": folds,
        "aggregates": {
            v: {h: a for h, a in per.items() if not h.startswith("folds_")}
            for v, per in by_variant.items()
        },
        "verdicts": verdicts,
    }
    (runs_dir / "evaluation.json").write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    return output


if __name__ == "__main__":
    main()
