"""Compact adapter: one canonical ordinary reading per independent sample.

Each poll enters as a *conditional composition* over the campaign's named
reference candidates that it offered (renormalized among them), with an
effective base equal to the respondents behind that composition. Rounding,
multiple published views of one sample, routing stages and alternative offered
fields are deliberately NOT modelled here; see the compact-model note.

Reference candidates follow the heavy model's rule so that comparisons with the
2026-09-16 fit are like for like: individually polled in an ordinary
(``campaign_vote_intention``) reading AND on the final ballot. The 2026 campaign
uses the hydrated Polling release and, by default, only polls of the certified
three-name field.
"""

from __future__ import annotations

import csv
import dataclasses
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESEARCH = HERE.parent
BACKEND = HERE.parents[2]
WORKSPACE = HERE.parents[3]
DATA_REPO = WORKSPACE / "toronto-election-poll-tracker-data"

ORDINARY = "campaign_vote_intention"
# Post-lean expressed choice is the reference signal; prefer views closest to it.
# Same rule as production (ADR 0057, 0060): each reading's own denominator_semantics.
DENOMINATOR_RANK = {
    "decided_plus_leaners": 0,
    "decided_only": 1,
    "all_respondents": 2,
    "other": 9,
}
DENOMINATOR_RANKS = {
    "decided_first": DENOMINATOR_RANK,
    "all_first": {"all_respondents": 0, "decided_plus_leaners": 1, "decided_only": 2},
}
# Three old readings (Compas/Ipsos 2003, Léger 2006) publish shares with no base of any
# kind. Rather than drop the sparsest campaigns' evidence, assume a modest base; the
# precision law's floor (tau_reference) bounds the credit any single poll can earn.
ASSUMED_BASE_WHEN_UNREPORTED = 500.0
CURRENT_KEY = "toronto-2026"
# Certified minor candidates that at least one certified-field poll reported
# individually (Mainstreet, Sept 14-17 2026). Modelled only when requested.
EXTRA_2026 = (("sarah-mcvie", "Sarah McVie"), ("odessa-paloma-parker", "Odessa Paloma Parker"))
CURRENT_FIELD = (
    ("chow", "Olivia Chow"),
    ("bradford", "Brad Bradford"),
    ("alexander", "Chris Alexander"),
)
LATEST_POLLS_FOR_LEADERS = 3


@dataclass(frozen=True)
class Paths:
    register: Path = RESEARCH / "mayoral-measurement-classification-2026-09-12.json"
    historical: Path = DATA_REPO / "data/raw/polls/historical_mayoral"
    # The owner's classification (ADR 0060); the register above is a frozen record.
    classification: Path = DATA_REPO / "data/raw/polls/historical_mayoral/reading_classification.csv"
    outcomes: Path = DATA_REPO / "data/raw/elections/mayoral_outcomes.csv"
    elections: Path = DATA_REPO / "data/raw/elections/mayoral_elections.csv"
    current_polls: Path = BACKEND / "data/upstream/polling/polls.csv"
    current_candidates: Path = BACKEND / "data/upstream/results/mayoral_candidates.json"


@dataclass(frozen=True)
class Poll:
    reading_id: str
    group: str  # same-sample dependence group (one poll per group)
    firm: str
    days_before_election: int  # fieldwork midpoint to election day
    n_eff: float  # respondents behind the modelled composition
    offered: tuple[int, ...]  # indices into CampaignPolls.candidates
    shares: tuple[float, ...]  # renormalized over ``offered``


@dataclass(frozen=True)
class CampaignPolls:
    key: str
    candidates: tuple[str, ...]
    names: tuple[str, ...]
    election_date: date
    polls: tuple[Poll, ...]
    outcome_shares: tuple[float, ...] | None  # renormalized among ``candidates``
    outcome_tail: float | None  # ballot share outside ``candidates``
    leaders: tuple[int, int]  # top two by the latest polls (pre-outcome information)


def _read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _normalize(name: str) -> str:
    return " ".join(name.casefold().replace("-", " ").split())


def _midpoint(start: str, end: str) -> date:
    a, b = date.fromisoformat(start), date.fromisoformat(end or start)
    return a + timedelta(days=(b - a).days // 2)


def _first_number(*values) -> float | None:
    for value in values:
        try:
            number = float(value)
        except TypeError, ValueError:
            continue
        if number > 0:
            return number
    return None


def _leaders(polls: tuple[Poll, ...], count: int) -> tuple[int, int]:
    """Top two by mean renormalized share over the latest polls (never the outcome)."""
    latest = sorted(polls, key=lambda p: p.days_before_election)[:LATEST_POLLS_FOR_LEADERS]
    totals, seen = defaultdict(float), defaultdict(int)
    for poll in latest:
        for index, share in zip(poll.offered, poll.shares):
            totals[index] += share
            seen[index] += 1
    means = {index: totals[index] / seen[index] for index in totals}
    ranked = sorted(range(count), key=lambda i: (-means.get(i, -1.0), i))
    return (ranked[0], ranked[1])


def _campaign_polls(key, candidate_ids, names, election_date, polls, outcome_shares, tail):
    polls = tuple(sorted(polls, key=lambda p: (-p.days_before_election, p.reading_id)))
    if not polls:
        raise ValueError(f"{key}: no usable polls")
    return CampaignPolls(
        key=key,
        candidates=tuple(candidate_ids),
        names=tuple(names),
        election_date=election_date,
        polls=polls,
        outcome_shares=outcome_shares,
        outcome_tail=tail,
        leaders=_leaders(polls, len(candidate_ids)),
    )


def with_horizon(campaign: CampaignPolls, horizon_days: int) -> CampaignPolls:
    """Keep only polls at least ``horizon_days`` before election day; leaders follow.

    The outcome fields are left untouched: nulling a result is the fit's decision.
    """
    polls = tuple(p for p in campaign.polls if p.days_before_election >= horizon_days)
    if not polls:
        raise ValueError(f"{campaign.key}: no polls at or before {horizon_days} days out")
    return CampaignPolls(
        **{
            **campaign.__dict__,
            "polls": polls,
            "leaders": _leaders(polls, len(campaign.candidates)),
        }
    )


def without_candidates(campaign: CampaignPolls, names: tuple[str, ...]) -> CampaignPolls:
    """Drop reference candidates by name (width diagnostics, 2026-09-22: withdrawn
    candidates who stayed on the ballot). Their poll shares are removed and the rest
    renormalized (n_eff scaled by the retained fraction); their count share moves to
    the tail; leaders are recomputed from the remaining polls."""
    drop = {campaign.names.index(n) for n in names}
    keep = [i for i in range(len(campaign.names)) if i not in drop]
    remap = {old: new for new, old in enumerate(keep)}
    polls = []
    for poll in campaign.polls:
        pairs = [(remap[i], s) for i, s in zip(poll.offered, poll.shares) if i in remap]
        if len(pairs) < 2:
            continue
        total = sum(s for _, s in pairs)
        polls.append(
            dataclasses.replace(
                poll,
                offered=tuple(i for i, _ in pairs),
                shares=tuple(s / total for _, s in pairs),
                n_eff=poll.n_eff * total,
            )
        )
    outcome, tail = None, campaign.outcome_tail
    if campaign.outcome_shares is not None:
        dropped = sum(campaign.outcome_shares[i] for i in drop)
        kept = [campaign.outcome_shares[i] for i in keep]
        outcome = tuple(s / sum(kept) for s in kept)
        tail = tail + (1.0 - tail) * dropped
    return _campaign_polls(
        campaign.key,
        [campaign.candidates[i] for i in keep],
        [campaign.names[i] for i in keep],
        campaign.election_date,
        polls,
        outcome,
        tail,
    )


# --------------------------------------------------------------------------- historical


def historical_campaigns(
    paths: Paths | None = None, *, min_offered: int = 2, denominator_rank: str = "decided_first"
) -> dict[str, CampaignPolls]:
    """Seven historical campaigns from the owner's corpus and its classification (ADR 0060)."""
    paths = paths or Paths()
    samples = {r["poll_sample_id"]: r for r in _read_csv(paths.historical / "poll_samples.csv")}
    readings = {r["poll_reading_id"]: r for r in _read_csv(paths.historical / "poll_readings.csv")}
    ordinary = [
        {**readings[r["poll_reading_id"]],
         "election_cycle_id": samples[readings[r["poll_reading_id"]]["poll_sample_id"]]["election_cycle_id"]}
        for r in _read_csv(paths.classification)
        if r["scope"] == "citywide_mayoral" and r["measurement_class"] == ORDINARY
    ]
    responses = defaultdict(list)
    for row in _read_csv(paths.historical / "poll_responses.csv"):
        responses[row["poll_reading_id"]].append(row)
    outcomes = defaultdict(dict)
    for row in _read_csv(paths.outcomes):
        outcomes[row["election_cycle_id"]][row["candidate_id"]] = row
    election_dates = {
        r["election_cycle_id"]: date.fromisoformat(r["election_date"])
        for r in _read_csv(paths.elections)
    }

    by_cycle = defaultdict(list)
    for r in ordinary:
        by_cycle[r["election_cycle_id"]].append(r)

    campaigns = {}
    for cycle, rows in sorted(by_cycle.items()):
        final = outcomes[cycle]
        names_to_id = defaultdict(set)
        for cid, row in final.items():
            names_to_id[_normalize(row["candidate_name"])].add(cid)

        def identity(response, final=final, names_to_id=names_to_id):
            cid = response["candidate_id"]
            if cid in final:
                return cid
            matches = names_to_id.get(_normalize(response["candidate_name"]), set())
            return next(iter(matches)) if len(matches) == 1 else None

        def published(reading_id, identity=identity):
            """Final-ballot candidates with a numeric share in this reading."""
            found = {}
            for response in responses[reading_id]:
                if response["response_kind"] != "candidate" or response["share"] == "":
                    continue
                cid = identity(response)
                if cid is not None:
                    found[cid] = float(response["share"])
            return found

        # Reference: polled in any ordinary reading and on the final ballot.
        reference = sorted(
            {cid for r in rows for cid in published(r["poll_reading_id"])},
            key=lambda cid: (-float(final[cid]["share"]), cid),
        )
        if len(reference) < 2:
            raise ValueError(f"{cycle}: fewer than two polled final-ballot candidates")
        index = {cid: i for i, cid in enumerate(reference)}
        votes = [float(final[cid]["votes"]) for cid in reference]
        outcome_shares = tuple(v / sum(votes) for v in votes)
        tail = 1.0 - sum(float(final[cid]["share"]) for cid in reference)

        groups = defaultdict(list)
        for r in rows:
            groups[r["poll_sample_id"]].append(r)
        polls = []
        for group, members in groups.items():
            candidates = []
            for r in members:
                shares = published(r["poll_reading_id"])
                if len(shares) < min_offered:
                    continue
                rank = DENOMINATOR_RANKS[denominator_rank].get(r["denominator_semantics"], 9)
                candidates.append((rank, -len(shares), r["poll_reading_id"], r, shares))
            if not candidates:
                continue
            _, _, reading_id, r, shares = min(candidates)
            source, sample = readings[reading_id], samples[r["poll_sample_id"]]
            base = _first_number(
                source["weighted_base"],
                source["reported_base"],
                source["unweighted_base"],
                sample["recruited_sample_size"],
            )
            if base is None:
                base = ASSUMED_BASE_WHEN_UNREPORTED
            offered = tuple(sorted(index[cid] for cid in shares))
            raw = [shares[reference[i]] for i in offered]
            total = sum(raw)
            polls.append(
                Poll(
                    reading_id=reading_id,
                    group=group,
                    firm=sample["pollster"],
                    days_before_election=(
                        election_dates[cycle]
                        - _midpoint(sample["fieldwork_start"], sample["fieldwork_end"])
                    ).days,
                    n_eff=base * total,
                    offered=offered,
                    shares=tuple(s / total for s in raw),
                )
            )
        campaigns[cycle] = _campaign_polls(
            cycle,
            reference,
            [final[cid]["candidate_name"] for cid in reference],
            election_dates[cycle],
            polls,
            outcome_shares,
            tail,
        )
    return campaigns


# --------------------------------------------------------------------------- current


def current_campaign(
    paths: Paths | None = None,
    *,
    election_date: date,
    require_full_field: bool = True,
    extra_named: tuple[tuple[str, str], ...] = (),
) -> CampaignPolls:
    """The 2026 campaign from the hydrated Polling release (certified field only by default).

    ``extra_named`` adds (polls.csv column, display name) pairs as further named
    candidates; a poll offers them only when it reported them, otherwise its
    composition is conditional on the names it did report. The certified-field
    rule applies to the base three only.
    """
    paths = paths or Paths()
    display = {}
    if paths.current_candidates.exists():
        feed = json.loads(paths.current_candidates.read_text(encoding="utf-8"))
        display = {
            _normalize(c["display_name"]): (c.get("person_id") or c["candidacy_id"])
            for c in feed["candidates"]
        }
    field = (*CURRENT_FIELD, *extra_named)
    columns = [column for column, _ in field]
    names = tuple(name for _, name in field)
    ids = tuple(display.get(_normalize(name), column) for column, name in field)
    base_count = len(CURRENT_FIELD)

    polls = []
    for row in _read_csv(paths.current_polls):
        present = [i for i, column in enumerate(columns) if row.get(column, "") not in ("", None)]
        base_present = [i for i in present if i < base_count]
        if len(base_present) < (base_count if require_full_field else 2):
            continue
        base = _first_number(row["sample_size"])
        if base is None:
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
