"""The uniform rule against the decided treatment (backend issue 48, pre-registered 2026-10-07).

Rules: ``docs/research/uniform-rule-2026-10-07.md`` (committed before any run).

Three ways the 2026 campaign can treat Alexander's Suspended Campaign (Oct 6):

* ``production``: today's rule; a reading enters only when it names Chow, Bradford and
  Alexander, so a Post-Suspension Reading that omits him is dropped.
* ``decided``: the map's decided treatment; Post-Suspension Readings (fieldwork ending
  on or after the suspension, i.e. overlapping or following it) enter as Chow-Bradford
  compositions with any Alexander share set aside; S2 is applied to the election-day
  draws afterwards (``apply_s2``).
* ``uniform``: Chow and Bradford are the named candidates in every reading; Alexander's
  share goes to the residual, before and after the exit; no S2.

Every rule admits the same samples: those naming all three (production's set) plus
Post-Suspension samples naming Chow and Bradford. The 2026 rows are the archive's one
reading per sample (``polls.csv``), as in every research fit, so each arm uses the same
reading for each sample.

``fold_held_out_suspensions`` is the held-out analogue of the uniform rule: a held-out
campaign's candidates whose Suspended Campaign was announced on or before the cutoff are
folded into the pool in all that campaign's readings and in its target.
"""

from __future__ import annotations

from datetime import date

import numpy as np

from .readings import (
    CURRENT_FIELD,
    CURRENT_KEY,
    CampaignPolls,
    Paths,
    Poll,
    _campaign_polls,
    _first_number,
    _normalize,
    _read_csv,
    without_candidates,
)
from .suspensions import known_suspensions, suspend

RULES = ("production", "decided", "uniform")
SUSPENDED = "alexander"  # polls.csv column of the 2026 Suspended Campaign
SUSPENSION_DATE = date(2026, 10, 6)


def admitted(row: dict, suspension_date: date = SUSPENSION_DATE) -> bool:
    """Production's three-name samples, plus Post-Suspension samples naming Chow and Bradford."""
    present = {column for column, _ in CURRENT_FIELD if row.get(column, "") not in ("", None)}
    if present == {column for column, _ in CURRENT_FIELD}:
        return True
    post = date.fromisoformat(row["date_conducted"]) >= suspension_date
    return post and {"chow", "bradford"} <= present


def current_campaign_under(
    rule: str,
    paths: Paths | None = None,
    *,
    election_date: date,
    drop_polls: tuple[str, ...] = (),
    suspension_date: date = SUSPENSION_DATE,
) -> CampaignPolls:
    """The 2026 campaign under one of ``RULES`` (see the module docstring)."""
    if rule not in RULES:
        raise ValueError(f"unknown rule {rule!r}")
    import json

    paths = paths or Paths()
    display = {}
    if paths.current_candidates.exists():
        feed = json.loads(paths.current_candidates.read_text(encoding="utf-8"))
        display = {
            _normalize(c["display_name"]): (c.get("person_id") or c["candidacy_id"])
            for c in feed["candidates"]
        }
    field = (
        CURRENT_FIELD
        if rule != "uniform"
        else tuple((column, name) for column, name in CURRENT_FIELD if column != SUSPENDED)
    )
    columns = [column for column, _ in field]
    names = tuple(name for _, name in field)
    ids = tuple(display.get(_normalize(name), column) for column, name in field)

    polls = []
    for row in _read_csv(paths.current_polls):
        if row["poll_id"] in drop_polls:
            continue
        full = all(row.get(c, "") not in ("", None) for c, _ in CURRENT_FIELD)
        if rule == "production":
            if not full:
                continue
        elif not admitted(row, suspension_date):
            continue
        post = date.fromisoformat(row["date_conducted"]) >= suspension_date
        present = [i for i, column in enumerate(columns) if row.get(column, "") not in ("", None)]
        if rule == "decided" and post:
            present = [i for i in present if columns[i] != SUSPENDED]  # set aside
        base = _first_number(row["sample_size"])
        if base is None or len(present) < 2:
            continue
        raw = [float(row[columns[i]]) for i in present]
        total = sum(raw)
        polls.append(
            Poll(
                reading_id=row["poll_id"],
                group=row["poll_id"],
                firm=row["firm"],
                days_before_election=(
                    election_date - date.fromisoformat(row["date_conducted"])
                ).days,
                n_eff=base * total,
                offered=tuple(present),
                shares=tuple(s / total for s in raw),
            )
        )
    return _campaign_polls(CURRENT_KEY, ids, names, election_date, polls, None, None)


def fold_held_out_suspensions(
    campaign: CampaignPolls, rows: list[dict], cutoff: date
) -> tuple[CampaignPolls, tuple[str, ...]]:
    """Fold candidates suspended on or before ``cutoff`` into the pool (polls and target)."""
    found = known_suspensions(campaign, rows, cutoff)
    names = tuple(campaign.names[i] for i in found)
    if not names:
        return campaign, ()
    return without_candidates(campaign, names), names


def apply_s2(named, tail, suspended: int, mu: float, sigma: float, seed: int):
    """S2 on flattened 2026 draws: one kept fraction per draw (capped at 1), freed share to
    the other named candidates in proportion; the pool (``tail``) is untouched."""
    named = np.asarray(named, dtype=float)
    keep = np.exp(np.random.default_rng(seed).normal(mu, sigma, size=(named.shape[0], 1)))
    out = np.asarray(suspend(named, (suspended,), np.minimum(keep, 1.0)))
    full = out * (1.0 - np.asarray(tail, dtype=float).reshape(-1, 1))
    return out, full
