"""Held-out runner for the repeat-firm anchor test (docs/research/repeat-firm-anchor-2026-10-13.md).

One fit per call, using the production package so arm P is exactly the published model:

    uv run python -m docs.research.compact_mayoral.anchor_holdouts \
        --arm {P,V} --holdout toronto_2023 --horizon 14 --seed 20260921 --out DIR

Inputs are the hydrated ``data/upstream`` of the checkout it runs in. The held-out campaign
keeps polls at least ``--horizon`` days out (``with_horizon``) and has its result nulled;
the other historical campaigns and 2026 are fitted jointly, in production order. Production
settings, with production's one retry (target acceptance 0.99, seed + 1) when a fit has more
than 4 divergences or worst R-hat at or above 1.02. Writes ``DIR/<arm>-<horizon>-<campaign>-<seed>.json``.
Arm P is the published frame of 2026-10-13 morning (``house_anchor="prior"``); V and O are the
two variants tested that day (repeat-firm and non-online anchors).
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import time
from datetime import date
from pathlib import Path

import numpy as np

import backend.model.compact_mayoral  # noqa: F401  (host device count)
from backend.model.compact_mayoral.hyperpriors import population_hyperpriors
from backend.model.compact_mayoral.model import prepare
from backend.model.compact_mayoral.readings import (
    current_campaign,
    historical_campaigns,
    with_horizon,
)
from backend.model.compact_mayoral.sampling import PRODUCTION, fit_joint
from docs.research.compact_mayoral.evaluate import crps

ROOT = Path.cwd()
ELECTION_2026 = date(2026, 10, 26)
ANALYSIS_CUTOFF = date(2026, 10, 13)
RESEARCH_DIVERGENCES = 4
RESEARCH_R_HAT = 1.02


def two_way(a: float, b: float) -> float:
    return 100.0 * (a - b) / (a + b)


def campaigns_for(holdout: str, horizon: int):
    polling = ROOT / "data/upstream/polling"
    history = historical_campaigns(polling)
    if holdout not in history:
        raise SystemExit(f"--holdout {holdout!r} is not among {sorted(history)}")
    held = with_horizon(history[holdout], horizon)
    truth = held.outcome_shares
    history[holdout] = dataclasses.replace(held, outcome_shares=None, outcome_tail=None)
    current = current_campaign(
        polling,
        ROOT / "data/upstream/results/mayoral_candidates.json",
        election_date=ELECTION_2026,
        cutoff=ANALYSIS_CUTOFF,
    )
    return (*history.values(), current), history[holdout], truth


def fit(campaigns, arm: str, seed: int):
    # P is the pre-ADR-0064 production frame; pass it explicitly now that the default changed.
    kwargs = {
        "P": {"house_anchor": "prior"},
        "V": {"house_anchor": "repeat_firms"},
        "O": {"house_anchor": "non_online"},
    }[arm]
    settings = dataclasses.replace(PRODUCTION, seed=seed)
    result = fit_joint(campaigns, population_hyperpriors(), settings=settings, **kwargs)
    d = result.diagnostics
    if d.divergences > RESEARCH_DIVERGENCES or d.worst_r_hat >= RESEARCH_R_HAT:
        retry = dataclasses.replace(settings, seed=seed + 1, target_accept=0.99)
        return fit_joint(campaigns, population_hyperpriors(), settings=retry, **kwargs), True
    return result, False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--arm", choices=("P", "V", "O"), required=True)
    parser.add_argument("--holdout", required=True)
    parser.add_argument("--horizon", type=int, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    started = time.monotonic()
    campaigns, held, truth = campaigns_for(args.holdout, args.horizon)
    result, retried = fit(campaigns, args.arm, args.seed)
    d = result.diagnostics
    key = held.key + "/"
    lead, second = held.leaders
    named = np.asarray(result.draws[key + "named_result"])
    margin = 100.0 * (named[:, lead] - named[:, second])
    actual = 100.0 * (truth[lead] - truth[second])
    q10, q50, q90 = (float(np.quantile(margin, q)) for q in (0.1, 0.5, 0.9))
    current = np.asarray(result.draws[key + "current"])
    latent_two_way = float(np.median(two_way(current[:, lead], current[:, second])))
    actual_two_way = two_way(truth[lead], truth[second])
    firms = sorted({p.firm for p in held.polls})
    counts = {f: sum(p.firm == f for p in held.polls) for f in firms}
    repeat = [f for f in firms if counts[f] >= 2]
    online = prepare(held).online_firms
    record = {
        "arm": args.arm,
        "holdout": held.key,
        "horizon": args.horizon,
        "seed": args.seed,
        "retried": retried,
        "polls_used": len(held.polls),
        "leaders": [held.names[lead], held.names[second]],
        "repeat_firms": repeat,
        "single_poll_firms": [f for f in firms if counts[f] == 1],
        "rule_changes_fold": (
            bool(online.any() and not online.all())
            if args.arm == "O"
            else len(repeat) >= 2 and len(repeat) < len(firms)
        ),
        "online_firms": [f for f, o in zip(firms, online) if o],
        "actual_margin": actual,
        "q10": q10,
        "q50": q50,
        "q90": q90,
        "covered_80": bool(q10 <= actual <= q90),
        "crps": 100.0 * crps(margin / 100.0, actual / 100.0),
        "latent_two_way_median": latent_two_way,
        "actual_two_way": actual_two_way,
        "anchor_error": abs(latent_two_way - actual_two_way),
        "diagnostics": dataclasses.asdict(d) if dataclasses.is_dataclass(d) else d.__dict__,
        "research_bar_failed": d.divergences > RESEARCH_DIVERGENCES
        or d.worst_r_hat >= RESEARCH_R_HAT,
        "seconds": round(time.monotonic() - started, 1),
    }
    args.out.mkdir(parents=True, exist_ok=True)
    path = args.out / f"{args.arm}-{args.horizon}-{held.key}-{args.seed}.json"
    path.write_text(json.dumps(record, indent=1), encoding="utf-8")
    print(
        json.dumps(
            {
                k: record[k]
                for k in (
                    "arm",
                    "holdout",
                    "horizon",
                    "seed",
                    "crps",
                    "covered_80",
                    "anchor_error",
                    "retried",
                    "seconds",
                )
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
