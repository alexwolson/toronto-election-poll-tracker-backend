"""Suspended Campaign signal (backend issue 43, pre-registered 2026-10-06).

From the public start of a Suspended Campaign the candidate's support is multiplied
by a kept fraction; the freed share goes to the other named candidates in proportion
to their support. Only suspensions known at the forecast cutoff apply. The kept
fraction's evidence is ``data/raw/elections/mayoral_suspended_campaigns.csv``: one row
per recorded Canadian case, kept fraction = final share / last pre-suspension poll
share, and no ratio when that share is 0 or there was no poll.
"""

from __future__ import annotations

import csv
import math
from datetime import date
from pathlib import Path

import numpy as np

from .readings import BACKEND, CampaignPolls, _normalize

TABLE = BACKEND / "data" / "raw" / "elections" / "mayoral_suspended_campaigns.csv"


def load_suspensions(path: Path = TABLE) -> list[dict]:
    with Path(path).open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        row["announcement_date"] = date.fromisoformat(row["announcement_date"])
        row["election_date"] = date.fromisoformat(row["election_date"])
    return rows


def kept_fraction(row: dict) -> float | None:
    """Final share over the last pre-suspension poll share; None without a positive share."""
    last = row["last_poll_share_pct"]
    if last in ("", None) or float(last) <= 0:
        return None
    return float(row["final_share_pct"]) / float(last)


def keep_distribution(
    rows: list[dict], *, exclude_cities: tuple[str, ...] = (), exclude_cycles: tuple[str, ...] = ()
) -> tuple[float, float]:
    """Mean and sample standard deviation of log kept fractions over the usable cases."""
    logs = [
        math.log(k)
        for row in rows
        if row["city"] not in exclude_cities and row["election_cycle_id"] not in exclude_cycles
        for k in [kept_fraction(row)]
        if k is not None
    ]
    if len(logs) < 2:
        raise ValueError(f"need at least two usable cases, got {len(logs)}")
    return float(np.mean(logs)), float(np.std(logs, ddof=1))


def suspend(shares, indices: tuple[int, ...], keep):
    """Multiply the ``indices`` shares by ``keep``; scale the rest so the total stays 1.

    Works on NumPy or JAX arrays; ``keep`` is a scalar or broadcasts against
    ``shares[..., :1]`` (one kept fraction per draw).
    """
    if not indices:
        return shares
    mask = np.zeros(shares.shape[-1])
    mask[list(indices)] = 1.0
    suspended = (shares * mask).sum(axis=-1, keepdims=True)
    others = (1.0 - keep * suspended) / (1.0 - suspended)
    return shares * mask * keep + shares * (1.0 - mask) * others


def known_suspensions(campaign: CampaignPolls, rows: list[dict], cutoff: date) -> tuple[int, ...]:
    """Indices of the campaign's named candidates whose suspension was announced by ``cutoff``."""
    index = {_normalize(name): i for i, name in enumerate(campaign.names)}
    found = []
    for row in rows:
        if row["election_cycle_id"] != campaign.key or row["announcement_date"] > cutoff:
            continue
        i = index.get(_normalize(row["candidate_name"]))
        if i is not None:
            found.append(i)
    return tuple(sorted(found))


def check_no_post_suspension_offer(campaign: CampaignPolls, rows: list[dict]) -> None:
    """Raise if a modelled poll dated on or after a suspension offers that candidate.

    The joint signal acts on election-day support only, which is exact while no
    modelled Post-Suspension Reading names the suspended candidate (poll dates are
    fieldwork midpoints, so this is a pattern check, not a fieldwork-overlap test).
    """
    for row in rows:
        if row["election_cycle_id"] != campaign.key:
            continue
        found = known_suspensions(campaign, [row], campaign.election_date)
        if not found:
            continue
        days = (campaign.election_date - row["announcement_date"]).days
        for poll in campaign.polls:
            if poll.days_before_election <= days and found[0] in poll.offered:
                raise ValueError(
                    f"{campaign.key}: {poll.reading_id} offers {row['candidate_name']} "
                    f"after the suspension on {row['announcement_date']}"
                )
