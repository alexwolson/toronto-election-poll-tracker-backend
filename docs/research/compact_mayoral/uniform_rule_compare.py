"""Issue 48 report: current-input arms (report only) and the binding held-out rule.

Usage (from the backend root)::

    uv run python -m docs.research.compact_mayoral.uniform_rule_compare <runs_root>

``<runs_root>/current/{P,A0,A1,U0,U1}`` are full fits on current inputs (production
settings); ``<runs_root>/runs/{baseline,uniform}/seed<N>/holdout<H>-<race>-dirichlet`` are
the held-out folds. The held-out rule (fixed in issue 48 before any run):

1. CRPS: at each horizon, the uniform arm's mean leader-margin CRPS over the five seeds is
   no worse than the baseline's by more than 0.10 points.
2. Coverage: a fold is covered when 3 of 5 seeds cover it; the uniform arm covers at least
   as many folds as the baseline at each horizon.
3. Sampling: no more fits fail (more than 4 divergences, or worst R-hat >= 1.02) than in
   the baseline.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

from . import evaluate as ev
from .suspensions import keep_distribution, load_suspensions
from .uniform_rule import apply_s2

SEEDS = (20260921, 20260922, 20260923, 20260924, 20260925)
HORIZONS = {
    20: [
        "toronto_2003",
        "toronto_2006",
        "toronto_2010",
        "toronto_2014",
        "toronto_2018",
        "toronto_2023",
    ],
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
TOLERANCE = 0.0010
MAJORITY = 3
ARMS = {"baseline": ("production", False), "uniform": ("uniform", True)}
CURRENT = ("P", "A0", "A1", "U0", "U1")
KEY = "toronto-2026"


def q(x, probs=(0.1, 0.5, 0.9)):
    return [float(v) for v in np.quantile(np.asarray(x, dtype=float), probs)]


# --------------------------------------------------------------------------- current inputs


def current_arm(run: Path, s2: tuple[float, float] | None) -> dict:
    summary = json.loads((run / "summary.json").read_text(encoding="utf-8"))
    record = summary["campaigns"][KEY]
    names = record["candidates"]
    with np.load(run / "draws.npz") as d:
        named = np.asarray(d[f"{KEY}/named_result"]).reshape(-1, len(names))
        tail = np.asarray(d[f"{KEY}/tail"]).reshape(-1)
    if s2 is not None:
        seed = summary["config"]["seed"]
        named, full = apply_s2(named, tail, names.index("Chris Alexander"), *s2, seed=seed)
    else:
        full = named * (1.0 - tail[:, None])
    chow, brad = names.index("Olivia Chow"), names.index("Brad Bradford")
    winners = named.argmax(axis=1)
    scales = summary["shared_scales"]
    return {
        "polls": record["polls"],
        "win": {n: float((winners == i).mean()) for i, n in enumerate(names)},
        "chow_two_way": q(named[:, chow] / (named[:, chow] + named[:, brad])),
        "full_ballot": {n: q(full[:, i]) for i, n in enumerate(names)},
        "pool": q(tail),
        "margin_points": q(full[:, chow] - full[:, brad]),
        "weekly_movement_2026": [record["weekly_movement"][k] for k in ("q10", "q50", "q90")],
        "m_move": [scales["m_move"][k] for k in ("q10", "q50", "q90")],
        "omega_move": [scales["omega_move"][k] for k in ("q10", "q50", "q90")],
        "diagnostics": {
            k: summary["diagnostics"][k] for k in ("divergences", "worst_r_hat", "min_ess")
        },
        "s2": s2 is not None,
    }


# --------------------------------------------------------------------------- held out


def check_config(run: Path, arm: str, seed: int, h: int, race: str) -> dict:
    summary = json.loads((run / "summary.json").read_text(encoding="utf-8"))
    c = summary["config"]
    rule, fold = ARMS[arm]
    expected = {
        "variant": "dirichlet",
        "hyperpriors": "population",
        "corpus": "all",
        "innovations": "gaussian",
        "target_accept": 0.95,
        "chains": 4,
        "warmup": 1000,
        "draws": 1000,
        "seed": seed,
        "holdout": race,
        "horizon_days": h,
        "current_rule": rule,
        "fold_held_out_suspensions": fold,
        "suspension_signal": "none",
    }
    for k, v in expected.items():
        assert c[k] == v, (run, k, c[k], v)
    return summary


def load_holdouts(root: Path) -> dict:
    out = {a: {s: {h: {} for h in HORIZONS} for s in SEEDS} for a in ARMS}
    for arm in ARMS:
        for s in SEEDS:
            for h, races in HORIZONS.items():
                for race in races:
                    run = root / "runs" / arm / f"seed{s}" / f"holdout{h}-{race}-dirichlet"
                    summary = check_config(run, arm, s, h, race)
                    f = ev.fold_metrics(run)
                    held = summary["campaigns"][race]["holdout"]
                    f["folded"] = held.get("folded_suspensions", [])
                    if "baseline_target_margin" in held:
                        with np.load(run / "draws.npz") as d:
                            named = np.asarray(d[f"{race}/named_result"])
                        named = named.reshape(-1, named.shape[-1])
                        names = summary["campaigns"][race]["candidates"]
                        lead, second = (names.index(n) for n in f["leaders"])
                        margin = named[:, lead] - named[:, second]
                        target = held["baseline_target_margin"]
                        f["baseline_target"] = {
                            "actual_margin": target,
                            "crps": ev.crps(margin, target),
                            "covered_80": bool(
                                np.quantile(margin, 0.1) <= target <= np.quantile(margin, 0.9)
                            ),
                        }
                    pool = summary["campaigns"][race]["residual_pool"]
                    f["pool_band"] = [pool["q10"], pool["q50"], pool["q90"]]
                    f["actual_pool"] = held["actual_tail"]
                    out[arm][s][h][race] = f
    return out


def mean_crps(arm: dict, h: int, field=None) -> float:
    def c(f):
        return f[field]["crps"] if field and field in f else f["crps"]

    return float(np.mean([np.mean([c(arm[s][h][r]) for r in HORIZONS[h]]) for s in SEEDS]))


def covered_folds(arm: dict, h: int) -> int:
    return sum(
        sum(bool(arm[s][h][r]["covered_80"]) for s in SEEDS) >= MAJORITY for r in HORIZONS[h]
    )


def failing_fits(arm: dict) -> int:
    return sum(
        not (arm[s][h][r]["divergences"] <= 4 and arm[s][h][r]["worst_r_hat"] < 1.02)
        for s in SEEDS
        for h in HORIZONS
        for r in HORIZONS[h]
    )


def rules(variant: dict, base: dict) -> dict:
    crps = {h: mean_crps(variant, h) for h in HORIZONS}
    base_crps = {h: mean_crps(base, h) for h in HORIZONS}
    cover = {h: covered_folds(variant, h) for h in HORIZONS}
    base_cover = {h: covered_folds(base, h) for h in HORIZONS}
    failing, base_failing = failing_fits(variant), failing_fits(base)
    ok1 = all(crps[h] <= base_crps[h] + TOLERANCE for h in HORIZONS)
    ok2 = all(cover[h] >= base_cover[h] for h in HORIZONS)
    ok3 = failing <= base_failing
    return {
        "crps": crps,
        "baseline_crps": base_crps,
        "difference": {h: crps[h] - base_crps[h] for h in HORIZONS},
        "coverage": cover,
        "baseline_coverage": base_cover,
        "failing_fits": failing,
        "baseline_failing_fits": base_failing,
        "1_crps": ok1,
        "2_coverage": ok2,
        "3_sampler": ok3,
        "pass": ok1 and ok2 and ok3,
    }


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    root = Path(argv[0])
    report: dict = {}

    s2 = keep_distribution(load_suspensions())  # all seven usable cases
    report["s2_keep_log_normal"] = list(s2)
    report["current"] = {}
    for name in CURRENT:
        run = root / "current" / name
        if (run / "summary.json").exists():
            report["current"][name] = current_arm(run, s2 if name.startswith("A") else None)
    for name, r in report["current"].items():
        win = ", ".join(f"{k.split()[-1]} {100 * v:.1f}" for k, v in r["win"].items())
        tw = r["chow_two_way"]
        print(
            f"[{name}] polls {r['polls']} | win {win} | Chow two-way {100 * tw[1]:.1f} "
            f"({100 * tw[0]:.1f}-{100 * tw[2]:.1f}) | diag {r['diagnostics']}"
        )
        for n, v in r["full_ballot"].items():
            print(f"      {n:16s} {100 * v[1]:5.1f} ({100 * v[0]:.1f}-{100 * v[2]:.1f})")
        p = r["pool"]
        print(
            f"      {'pool':16s} {100 * p[1]:5.1f} ({100 * p[0]:.1f}-{100 * p[2]:.1f}) | "
            f"weekly movement 2026 {[round(100 * x, 2) for x in r['weekly_movement_2026']]} | "
            f"m_move {[round(x, 3) for x in r['m_move']]}"
        )

    if not (root / "runs").exists():
        (root / "uniform_rule_evaluation.json").write_text(json.dumps(report, indent=1) + "\n")
        return report
    arms = load_holdouts(root)
    base, uni = arms["baseline"], arms["uniform"]
    for h, races in HORIZONS.items():
        for race in races:
            for arm in ARMS:
                cov = sum(bool(arms[arm][s][h][race]["covered_80"]) for s in SEEDS)
                crps = [100 * arms[arm][s][h][race]["crps"] for s in SEEDS]
                print(
                    f"  {h:>2d} {race:13s} {arm:8s} crps {np.mean(crps):6.2f} "
                    f"(per seed {', '.join(f'{c:.2f}' for c in crps)}) covered {cov}/5"
                )
        per_seed = [
            100
            * (
                np.mean([uni[s][h][r]["crps"] for r in races])
                - np.mean([base[s][h][r]["crps"] for r in races])
            )
            for s in SEEDS
        ]
        print(
            f"  -> {h} d uniform minus baseline per seed: "
            f"{', '.join(f'{d:+.3f}' for d in per_seed)}"
        )
    verdict = rules(uni, base)
    print("RULES (as written):", verdict)
    alt = {h: mean_crps(uni, h, "baseline_target") for h in HORIZONS}
    print(
        "uniform CRPS with 2010 scored against the baseline's own target:",
        {h: round(100 * v, 3) for h, v in alt.items()},
    )
    for h in HORIZONS:
        for s in SEEDS:
            f = uni[s][h]["toronto_2010"]
            print(
                f"  target check {h} d {s}: 2010 pool band {100 * f['pool_band'][0]:.2f}-"
                f"{100 * f['pool_band'][2]:.2f} (median {100 * f['pool_band'][1]:.2f}) | actual "
                f"pool {100 * f['actual_pool']:.2f} | covered "
                f"{f['pool_band'][0] <= f['actual_pool'] <= f['pool_band'][2]} | folded {f['folded']}"
                f" | baseline-target crps {100 * f['baseline_target']['crps']:.2f}"
            )
    report["holdout"] = {
        "verdict": {
            k: ({str(h): x for h, x in v.items()} if isinstance(v, dict) else v)
            for k, v in verdict.items()
        },
        "baseline_target_crps": {str(h): v for h, v in alt.items()},
        "folds": {
            a: {str(s): {str(h): d for h, d in hs.items()} for s, hs in arm.items()}
            for a, arm in arms.items()
        },
    }
    (root / "uniform_rule_evaluation.json").write_text(json.dumps(report, indent=1) + "\n")
    return report


if __name__ == "__main__":
    main()
