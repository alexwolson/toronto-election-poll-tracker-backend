"""Issue 51 results: binding do-no-harm (C2, C3 against P), the 2010 target check, the 7-day
report and the current-input fits. Rules fixed in ``reactive-allocation-2026-10-07.md`` (9a1ddef).

Usage (from the backend root)::

    uv run python -m docs.research.compact_mayoral.reactive_compare
"""

from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path

import numpy as np

from . import evaluate as ev
from .readings import historical_campaigns
from .suspensions import keep_distribution, load_suspensions, suspend
from .uniform_rule_diagnose import decompose

WORKSPACE = Path(__file__).resolve().parents[4]
RR = WORKSPACE / "research-runs" / "reactive-allocation-2026-10-07"
P_RUNS = WORKSPACE / "research-runs" / "suspension-replicates-2026-10-06" / "runs"
U_RUNS = WORKSPACE / "research-runs" / "uniform-rule-2026-10-07" / "runs" / "uniform"
SEEDS = (20260921, 20260922, 20260923, 20260924, 20260925)
ALL = [
    "toronto_2003",
    "toronto_2006",
    "toronto_2010",
    "toronto_2014",
    "toronto_2018",
    "toronto_2022",
    "toronto_2023",
]
BINDING = {20: [r for r in ALL if r != "toronto_2022"], 14: ALL}
TOLERANCE = 0.0010
MAJORITY = 3


def run_dir(arm: str, seed: int, h: int, race: str, retry: bool = False) -> Path:
    name = f"holdout{h}-{race}-dirichlet"
    if retry:
        return RR / "retries" / arm / f"seed{seed + 1}" / name
    if arm == "P" and h in (20, 14):
        return P_RUNS / f"seed{seed}" / name
    if arm == "U" and h in (20, 14):
        return U_RUNS / f"seed{seed}" / name
    return RR / "runs" / arm / f"seed{seed}" / name


def fails(f: dict) -> bool:
    return not (f["divergences"] <= 4 and f["worst_r_hat"] < 1.02)


def load_arm(arm: str, horizons: dict) -> dict:
    out = {s: {h: {} for h in horizons} for s in SEEDS}
    for s in SEEDS:
        for h, races in horizons.items():
            for r in races:
                f = ev.fold_metrics(run_dir(arm, s, h, r))
                f["retry"] = None
                if fails(f):
                    rd = run_dir(arm, s, h, r, retry=True)
                    if (rd / "summary.json").exists():
                        f["retry"] = ev.fold_metrics(rd)
                out[s][h][r] = f
    return out


def pick(f: dict, use_retry: bool) -> dict:
    return f["retry"] if use_retry and f.get("retry") else f


def mean_crps(arm, horizons, h, use_retry=False):
    return float(
        np.mean(
            [np.mean([pick(arm[s][h][r], use_retry)["crps"] for r in horizons[h]]) for s in SEEDS]
        )
    )


def covered(arm, horizons, h, use_retry=False):
    return sum(
        sum(bool(pick(arm[s][h][r], use_retry)["covered_80"]) for s in SEEDS) >= MAJORITY
        for r in horizons[h]
    )


def failing(arm, horizons, after_retry: bool) -> list:
    out = []
    for s in SEEDS:
        for h, races in horizons.items():
            for r in races:
                f = arm[s][h][r]
                if fails(f):
                    retried = f.get("retry")
                    still = retried is None or fails(retried)
                    if not after_retry or still:
                        out.append(
                            (
                                s,
                                h,
                                r,
                                f["divergences"],
                                round(f["worst_r_hat"], 4),
                                None
                                if retried is None
                                else (retried["divergences"], round(retried["worst_r_hat"], 4)),
                            )
                        )
    return out


def rules(v, p, horizons, use_retry):
    crps = {h: mean_crps(v, horizons, h, use_retry) for h in horizons}
    pc = {h: mean_crps(p, horizons, h, use_retry) for h in horizons}
    cov = {h: covered(v, horizons, h, use_retry) for h in horizons}
    pcov = {h: covered(p, horizons, h, use_retry) for h in horizons}
    fv, fp = failing(v, horizons, True), failing(p, horizons, True)
    r = {
        "crps": crps,
        "p_crps": pc,
        "difference": {h: crps[h] - pc[h] for h in horizons},
        "coverage": cov,
        "p_coverage": pcov,
        "failing_after_retry": len(fv),
        "p_failing_after_retry": len(fp),
        "1_crps": all(crps[h] <= pc[h] + TOLERANCE for h in horizons),
        "2_coverage": all(cov[h] >= pcov[h] for h in horizons),
        "3_sampler": len(fv) <= len(fp),
    }
    r["pass"] = r["1_crps"] and r["2_coverage"] and r["3_sampler"]
    return r


# --------------------------------------------------------------------------- 2010 / A


def margin_draws(run: Path, race: str):
    summary = json.loads((run / "summary.json").read_text(encoding="utf-8"))
    rec = summary["campaigns"][race]
    names = rec["candidates"]
    with np.load(run / "draws.npz") as d:
        named = np.asarray(d[f"{race}/named_result"]).reshape(-1, len(names))
    lead, second = (names.index(n) for n in rec["leaders"])
    return named, names, (lead, second), rec["holdout"]["leader_margin_actual"]


def s2_margin(run: Path, race: str, h: int, seed: int):
    """A = P plus S2 on P's draws (suspension_compare.s2_fold's construction)."""
    named, names, (lead, second), truth = margin_draws(run, race)
    rows = load_suspensions()
    camp = historical_campaigns()[race]
    cutoff = camp.election_date - timedelta(days=h)
    found = tuple(
        sorted(
            names.index(r["candidate_name"])
            for r in rows
            if r["election_cycle_id"] == race
            and r["announcement_date"] <= cutoff
            and r["candidate_name"] in names
        )
    )
    if found:
        mu, sigma = keep_distribution(rows, exclude_cycles=(race,))
        keep = np.exp(np.random.default_rng(seed).normal(mu, sigma, size=(named.shape[0], 1)))
        named = np.asarray(suspend(named, found, np.minimum(keep, 1.0)))
    return named[:, lead] - named[:, second], truth, [names[i] for i in found]


def target_check(horizons=(14, 7)) -> dict:
    out = {}
    for h in horizons:
        rows = {}
        for s in SEEDS:
            pm = margin_draws(run_dir("P", s, h, "toronto_2010"), "toronto_2010")
            p_margin = pm[0][:, pm[2][0]] - pm[0][:, pm[2][1]]
            truth = pm[3]
            a_margin, _, found = s2_margin(run_dir("P", s, h, "toronto_2010"), "toronto_2010", h, s)
            arms = {"P": (p_margin, truth), "A": (a_margin, truth)}
            for arm in ("U", "C2", "C3"):
                named, _, (lead, second), t = margin_draws(
                    run_dir(arm, s, h, "toronto_2010"), "toronto_2010"
                )
                arms[arm] = (named[:, lead] - named[:, second], t)
            for arm, (m, t) in arms.items():
                d = decompose(p_margin, m, t) if arm != "P" else None
                rows.setdefault(arm, []).append(
                    {
                        "median": float(np.median(m)),
                        "q10": float(np.quantile(m, 0.1)),
                        "q90": float(np.quantile(m, 0.9)),
                        "actual": t,
                        "crps": ev.crps(m, t),
                        **({"centre": d["centre"], "width": d["width"]} if d else {}),
                        **({"s2_on": found} if arm == "A" else {}),
                    }
                )
        out[h] = {
            arm: {k: float(np.mean([r[k] for r in v])) for k in v[0] if isinstance(v[0][k], float)}
            for arm, v in rows.items()
        }
    return out


# --------------------------------------------------------------------------- 7 days


def seven_day() -> dict:
    hz = {7: ALL}
    arms = {a: load_arm(a, hz) for a in ("P", "C2", "C3", "U")}
    out = {"folds": {}, "mean": {}, "covered": {}, "failing": {}}
    a_folds = {}
    for s in SEEDS:
        for r in ALL:
            f = arms["P"][s][7][r]
            m, t, found = s2_margin(run_dir("P", s, 7, r), r, 7, s)
            a_folds[(s, r)] = (
                {
                    "crps": ev.crps(m, t),
                    "covered_80": bool(np.quantile(m, 0.1) <= t <= np.quantile(m, 0.9)),
                    "s2_on": found,
                }
                if found
                else f
            )
    for name in ("P", "A", "C2", "C3", "U"):

        def get(s, r, name=name):
            return a_folds[(s, r)] if name == "A" else arms[name][s][7][r]

        out["folds"][name] = {r: float(np.mean([get(s, r)["crps"] for s in SEEDS])) for r in ALL}
        out["mean"][name] = float(
            np.mean([np.mean([get(s, r)["crps"] for r in ALL]) for s in SEEDS])
        )
        out["covered"][name] = sum(
            sum(bool(get(s, r)["covered_80"]) for s in SEEDS) >= MAJORITY for r in ALL
        )
        out["failing"][name] = (
            len(failing(arms[name], hz, False))
            if name != "A"
            else len(failing(arms["P"], hz, False))
        )
    return out


def main():
    p = load_arm("P", BINDING)
    result = {"binding": {}}
    for v in ("C2", "C3"):
        arm = load_arm(v, BINDING)
        per_seed = {
            h: [
                100
                * (
                    np.mean([arm[s][h][r]["crps"] for r in BINDING[h]])
                    - np.mean([p[s][h][r]["crps"] for r in BINDING[h]])
                )
                for s in SEEDS
            ]
            for h in BINDING
        }
        result["binding"][v] = {
            "as_written_original_fits": rules(arm, p, BINDING, use_retry=False),
            "with_retried_fits_substituted": rules(arm, p, BINDING, use_retry=True),
            "per_seed_difference_points": per_seed,
            "failing_before_retry": failing(arm, BINDING, False),
            "failing_after_retry": failing(arm, BINDING, True),
            "per_fold": {
                h: {
                    r: [
                        100 * np.mean([arm[s][h][r]["crps"] for s in SEEDS]),
                        100 * np.mean([p[s][h][r]["crps"] for s in SEEDS]),
                    ]
                    for r in BINDING[h]
                }
                for h in BINDING
            },
        }
    result["p_failing_before_retry"] = failing(p, BINDING, False)
    result["p_failing_after_retry"] = failing(p, BINDING, True)
    result["target_check_2010"] = target_check()
    result["seven_day"] = seven_day()
    (RR / "reactive_evaluation.json").write_text(json.dumps(result, indent=1, default=str) + "\n")
    print(json.dumps(result, indent=1, default=str))
    return result


if __name__ == "__main__":
    main()
