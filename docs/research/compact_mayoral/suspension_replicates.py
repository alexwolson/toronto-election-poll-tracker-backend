"""Seed-replicate test of the Suspended Campaign signal (backend issue 45).

Usage (from the backend root)::

    uv run python -m docs.research.compact_mayoral.suspension_replicates <runs_dir>

``<runs_dir>/seed<N>/`` holds one seed's folds, named as ``run_holdouts.sh`` names them:
``holdout<H>-<race>-dirichlet`` (baseline) and ``...-dirichlet_joint`` (S1). S2 is
computed from each baseline fold's draws by ``suspension_compare.s2_fold``, with its
NumPy seed equal to the fit's seed. The rule was fixed in issue 45 before any run:

1. CRPS: each arm's mean leader-margin CRPS, averaged over the five seeds, is no more
   than 0.10 points above the baseline's at 20 and at 14 days.
2. Coverage: a fold is covered when its 80% band holds the actual margin in at least 3 of
   the 5 seeds; a variant needs every fold but one (5 of 6 at 20 days, 6 of 7 at 14), or
   the baseline's count where the baseline falls short of that.
3. Sampling: every fit in every seed has at most 4 divergences and worst R-hat < 1.02.

Order: S1, then S2, then neither. Never reads the 2026 forecast.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

from . import evaluate as ev
from .readings import historical_campaigns
from .suspension_compare import s2_fold
from .suspensions import load_suspensions

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
TOLERANCE = 0.0010  # 0.10 points of leader margin
MAJORITY = 3  # seeds out of five
RECORD_SETTINGS = {
    "variant": "dirichlet",
    "hyperpriors": "population",
    "corpus": "all",
    "innovations": "gaussian",
    "target_accept": 0.95,
    "chains": 4,
    "warmup": 1000,
    "draws": 1000,
}
ARMS = ("dirichlet", "dirichlet_joint", "dirichlet_s2")


def check_run_config(run_dir: Path, *, seed: int, joint: bool) -> None:
    """Fail loudly unless a run carries its seed, its arm and the run of record's settings."""
    config = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))["config"]
    for key, value in RECORD_SETTINGS.items():
        assert config[key] == value, (run_dir.name, key, config[key])
    assert config["seed"] == seed, (run_dir.name, "seed", config["seed"])
    signal = "joint" if joint else "none"
    assert config["suspension_signal"] == signal, (run_dir.name, config["suspension_signal"])
    horizon, race = run_dir.name.split("-")[0].removeprefix("holdout"), run_dir.name.split("-")[1]
    assert config["horizon_days"] == int(horizon) and config["holdout"] == race, run_dir.name


def _folds(arm: dict, h: int):
    return [arm[s][h][r] for s in SEEDS for r in HORIZONS[h]]


def mean_crps(arm: dict, h: int) -> float:
    return float(np.mean([np.mean([arm[s][h][r]["crps"] for r in HORIZONS[h]]) for s in SEEDS]))


def covered_folds(arm: dict, h: int) -> int:
    return sum(
        sum(bool(arm[s][h][r]["covered_80"]) for s in SEEDS) >= MAJORITY for r in HORIZONS[h]
    )


def failing_fits(arm: dict) -> int:
    """Fits breaking the sampling rule: more than 4 divergences or worst R-hat >= 1.02."""
    return sum(
        not (f["divergences"] <= 4 and f["worst_r_hat"] < 1.02)
        for h in HORIZONS
        for f in _folds(arm, h)
    )


def rules(variant: dict, base: dict, *, baseline_sampling_bar: bool = False) -> dict:
    """The pre-registered rule; ``baseline_sampling_bar`` is the 2026-10-07 correction.

    As written, any failing fit fails the arm. With the correction (maintainer decision
    after the sweep, because the baseline itself failed the as-written bar at 65 fits),
    a variant passes sampling with no more failing fits than the baseline, as coverage
    already allowed.
    """
    crps = {h: mean_crps(variant, h) for h in HORIZONS}
    base_crps = {h: mean_crps(base, h) for h in HORIZONS}
    cover = {h: covered_folds(variant, h) for h in HORIZONS}
    base_cover = {h: covered_folds(base, h) for h in HORIZONS}
    bar = {h: min(len(HORIZONS[h]) - 1, base_cover[h]) for h in HORIZONS}
    ok_crps = all(crps[h] <= base_crps[h] + TOLERANCE for h in HORIZONS)
    ok_cover = all(cover[h] >= bar[h] for h in HORIZONS)
    failing, base_failing = failing_fits(variant), failing_fits(base)
    ok_sampler = failing <= (base_failing if baseline_sampling_bar else 0)
    return {
        "crps": crps,
        "baseline_crps": base_crps,
        "coverage": cover,
        "baseline_coverage": base_cover,
        "coverage_bar": bar,
        "failing_fits": failing,
        "baseline_failing_fits": base_failing,
        "1_crps": ok_crps,
        "2_coverage": ok_cover,
        "3_sampler": ok_sampler,
        "pass": ok_crps and ok_cover and ok_sampler,
    }


def adopted(s1: dict, s2: dict) -> str:
    return "S1" if s1["pass"] else ("S2" if s2["pass"] else "neither")


def seed_spread(variant: dict, base: dict, h: int) -> float:
    """Standard deviation over seeds of the variant-minus-baseline mean CRPS (n-1)."""
    diffs = [
        np.mean([variant[s][h][r]["crps"] for r in HORIZONS[h]])
        - np.mean([base[s][h][r]["crps"] for r in HORIZONS[h]])
        for s in SEEDS
    ]
    return float(np.std(diffs, ddof=1))


def load(runs: Path) -> dict:
    """{arm: {seed: {horizon: {race: fold}}}} for the three arms; every fold must exist."""
    rows = load_suspensions()
    dates = {k: c.election_date for k, c in historical_campaigns().items()}
    out = {a: {s: {h: {} for h in HORIZONS} for s in SEEDS} for a in ARMS}
    for s in SEEDS:
        for h, races in HORIZONS.items():
            for r in races:
                base_dir = runs / f"seed{s}" / f"holdout{h}-{r}-dirichlet"
                joint_dir = runs / f"seed{s}" / f"holdout{h}-{r}-dirichlet_joint"
                check_run_config(base_dir, seed=s, joint=False)
                check_run_config(joint_dir, seed=s, joint=True)
                base = ev.fold_metrics(base_dir)
                joint = ev.fold_metrics(joint_dir)
                summary = json.loads((joint_dir / "summary.json").read_text(encoding="utf-8"))
                joint["keep_fraction"] = summary["shared_scales"]["keep_fraction"]
                out["dirichlet"][s][h][r] = base
                out["dirichlet_joint"][s][h][r] = joint
                out["dirichlet_s2"][s][h][r] = s2_fold(base_dir, base, rows, dates, seed=s)
    return out


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    runs = Path(argv[0])
    arms = load(runs)
    base = arms["dirichlet"]
    for name in ARMS:
        print(f"=== {name}")
        for h, races in HORIZONS.items():
            for r in races:
                for s in SEEDS:
                    f = arms[name][s][h][r]
                    keep = f.get("keep_fraction")
                    extra = f" keep {keep['mean']:.3f}" if keep else ""
                    extra += f" S2 on {f['s2_applied']}" if f.get("s2_applied") else ""
                    print(
                        f"  {h:>2d} {r:13s} {s} band {100 * f['q10']:+6.1f}..{100 * f['q90']:+6.1f}"
                        f"  actual {100 * f['actual_margin']:+6.1f}  crps {100 * f['crps']:5.2f}"
                        f"  cov {f['covered_80']!s:5s}  div {f['divergences']}"
                        f"  R-hat {f['worst_r_hat']:.4f}  {f['scales']}{extra}"
                    )
            per_seed = [np.mean([arms[name][s][h][r]["crps"] for r in races]) for s in SEEDS]
            print(
                f"  -> {h} d: mean CRPS over seeds {100 * mean_crps(arms[name], h):.2f}"
                f" (per seed {', '.join(f'{100 * c:.2f}' for c in per_seed)})"
                f" | covered folds {covered_folds(arms[name], h)}/{len(races)}"
            )
    spread = {
        name: {h: seed_spread(arms[name], base, h) for h in HORIZONS}
        for name in ("dirichlet_joint", "dirichlet_s2")
    }
    print(
        "seed spread of the variant-minus-baseline mean CRPS (points):",
        {n: {h: round(100 * v, 3) for h, v in d.items()} for n, d in spread.items()},
    )
    verdicts = {}
    for label, corrected in (("as_written", False), ("baseline_sampling_bar", True)):
        s1 = rules(arms["dirichlet_joint"], base, baseline_sampling_bar=corrected)
        s2 = rules(arms["dirichlet_s2"], base, baseline_sampling_bar=corrected)
        verdicts[label] = {"s1": s1, "s2": s2, "adopted": adopted(s1, s2)}
        print(f"[{label}] S1 rules:", s1)
        print(f"[{label}] S2 rules:", s2, "(consulted only if S1 fails)")
        print(f"[{label}] ADOPTED:", verdicts[label]["adopted"])
    print(
        "DECISION OF RECORD (sampling bar corrected, 2026-10-07):",
        verdicts["baseline_sampling_bar"]["adopted"],
    )

    def keyed(d: dict) -> dict:
        return {
            k: ({str(h): x for h, x in v.items()} if isinstance(v, dict) else v)
            for k, v in d.items()
        }

    out = {
        "folds": {
            n: {str(s): {str(h): d for h, d in hs.items()} for s, hs in a.items()}
            for n, a in arms.items()
        },
        "verdicts": {
            label: {"s1": keyed(v["s1"]), "s2": keyed(v["s2"]), "adopted": v["adopted"]}
            for label, v in verdicts.items()
        },
        "seed_spread": {n: {str(h): v for h, v in d.items()} for n, d in spread.items()},
        "adopted": verdicts["baseline_sampling_bar"]["adopted"],
    }
    (runs / "suspension_replicates_evaluation.json").write_text(json.dumps(out, indent=1) + "\n")
    return out


if __name__ == "__main__":
    main()
