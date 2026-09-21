"""Inputs for the compact model: one canonical ordinary reading per independent sample.

Historical campaigns come from the backend-tracked audited corpus
(``data/raw/polls/historical_mayoral``), the canonical outcomes table and the
election-dates manifest, filtered by the tracked reading-classification table
(derived from the 2026-09-12 research register). The current campaign comes from
the hydrated Polling release's ``polls.csv`` and the hydrated Results candidate
feed.

Each poll enters as a *conditional composition* over the campaign's named
reference candidates that it offered (renormalized among them), with an
effective base equal to the respondents behind that composition. Rounding,
multiple published views of one sample, routing stages and alternative offered
fields are deliberately not modelled (ADR 0054).

Reference candidates follow the research integrated model's rule: individually
polled in an ordinary (``campaign_vote_intention``) reading AND on the final
ballot. The 2026 reference is the certified three-name field; certified minor
candidates that a poll reports individually stay in the residual pool unless
``extra_named`` asks for them.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from backend.model.mayoral_candidate_ids import mayoral_candidate_id

ROOT = Path(__file__).resolve().parents[3]
HISTORICAL = ROOT / "data" / "raw" / "polls" / "historical_mayoral"
OUTCOMES = ROOT / "data" / "raw" / "elections" / "mayoral_outcomes.csv"
ELECTIONS = ROOT / "data" / "raw" / "elections" / "mayoral_elections.csv"
CLASSIFICATION = ROOT / "data" / "raw" / "polls" / "mayoral_reading_classification.csv"

ORDINARY = "campaign_vote_intention"
# Post-lean expressed choice is the reference signal; prefer views closest to it.
DENOMINATOR_RANK = {
    "decided_plus_leaners": 0,
    "decided_only": 1,
    "all_respondents": 2,
    "not_reported": 3,
    "other_source_defined": 4,
}
# Three old readings (Compas/Ipsos 2003, Léger 2006) publish shares with no base of
# any kind. Rather than drop the sparsest campaigns' evidence, assume a modest base;
# the precision law's floor (tau_reference) bounds the credit any single poll earns.
ASSUMED_BASE_WHEN_UNREPORTED = 500.0
CURRENT_KEY = "toronto-2026"
CURRENT_FIELD = (
    ("chow", "Olivia Chow"),
    ("bradford", "Brad Bradford"),
    ("alexander", "Chris Alexander"),
)
# Certified minor candidates that at least one certified-field poll reported
# individually (Mainstreet, Sept 14-17 2026). Modelled only when requested.
EXTRA_2026 = (("sarah-mcvie", "Sarah McVie"), ("odessa-paloma-parker", "Odessa Paloma Parker"))
LATEST_POLLS_FOR_LEADERS = 3
POLL_META_COLUMNS = {
    "poll_id",
    "firm",
    "date_conducted",
    "date_published",
    "sample_size",
    "methodology",
    "field_tested",
    "other",
    "notes",
}


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
    with Path(path).open(encoding="utf-8", newline="") as handle:
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


# --------------------------------------------------------------------------- historical


def historical_campaigns(
    *,
    historical_dir: Path = HISTORICAL,
    outcomes_csv: Path = OUTCOMES,
    elections_csv: Path = ELECTIONS,
    classification_csv: Path = CLASSIFICATION,
    min_offered: int = 2,
) -> dict[str, CampaignPolls]:
    """Seven historical campaigns from the audited corpus and the classification table."""
    ordinary = [
        r
        for r in _read_csv(classification_csv)
        if r["scope"] == "citywide_mayoral"
        and r["measurement_class"] == ORDINARY
        and r["corpus"] == "historical"
    ]
    samples = {r["poll_sample_id"]: r for r in _read_csv(historical_dir / "poll_samples.csv")}
    readings = {r["poll_reading_id"]: r for r in _read_csv(historical_dir / "poll_readings.csv")}
    responses = defaultdict(list)
    for row in _read_csv(historical_dir / "poll_responses.csv"):
        responses[row["poll_reading_id"]].append(row)
    outcomes = defaultdict(dict)
    for row in _read_csv(outcomes_csv):
        outcomes[row["election_cycle_id"]][row["candidate_id"]] = row
    election_dates = {
        r["election_cycle_id"]: date.fromisoformat(r["election_date"])
        for r in _read_csv(elections_csv)
    }

    by_cycle = defaultdict(list)
    for r in ordinary:
        # The register also classifies readings the research model recovered from
        # source documents (e.g. Mainstreet 2023 report stages); they have no rows
        # in the audited corpus and are not modelled here.
        if r["poll_reading_id"] not in readings:
            continue
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
            groups[r["same_sample_dependence_group"]].append(r)
        polls = []
        for group, members in groups.items():
            candidates = []
            for r in members:
                shares = published(r["poll_reading_id"])
                if len(shares) < min_offered:
                    continue
                rank = DENOMINATOR_RANK.get(r["denominator_semantics"], 9)
                candidates.append((rank, -len(shares), r["poll_reading_id"], shares))
            if not candidates:
                continue
            _, _, reading_id, shares = min(candidates)
            source = readings[reading_id]
            sample = samples[source["poll_sample_id"]]
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


def certified_candidates(candidates_json: Path) -> list[tuple[str, str, str]]:
    """(canonical id, display name, poll column slug) for every certified candidate."""
    feed = json.loads(Path(candidates_json).read_text(encoding="utf-8"))
    out = []
    for c in feed["candidates"]:
        name = c["display_name"]
        parts = name.split()
        slug = mayoral_candidate_id(parts[0], " ".join(parts[1:])) if len(parts) > 1 else parts[0]
        out.append((c.get("person_id") or c["candidacy_id"], name, slug))
    return out


def _certified_field_rows(polls_csv: Path, columns: list[str], require_full_field: bool):
    base_count = len(CURRENT_FIELD)
    for row in _read_csv(polls_csv):
        present = [i for i, column in enumerate(columns) if row.get(column, "") not in ("", None)]
        base_present = [i for i in present if i < base_count]
        if len(base_present) < (base_count if require_full_field else 2):
            continue
        base = _first_number(row["sample_size"])
        if base is None:
            continue
        yield row, present, base


def current_campaign(
    polls_csv: Path,
    candidates_json: Path,
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
    display = {_normalize(name): cid for cid, name, _ in certified_candidates(candidates_json)}
    field = (*CURRENT_FIELD, *extra_named)
    columns = [column for column, _ in field]
    names = tuple(name for _, name in field)
    ids = tuple(display.get(_normalize(name), column) for column, name in field)

    polls = []
    for row, present, base in _certified_field_rows(polls_csv, columns, require_full_field):
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


def minor_candidates_reported(polls_csv: Path, candidates_json: Path) -> list[dict]:
    """Certified candidates outside the modelled three that a certified-field poll reported.

    Returns the latest reported share per candidate, newest poll first.
    """
    base_slugs = {slug for slug, _ in CURRENT_FIELD}
    minors = {
        slug: (cid, name)
        for cid, name, slug in certified_candidates(candidates_json)
        if slug not in base_slugs
    }
    columns = [slug for slug, _ in CURRENT_FIELD]
    latest: dict[str, dict] = {}
    for row, _, _ in _certified_field_rows(polls_csv, columns, True):
        for slug, (cid, name) in minors.items():
            value = row.get(slug, "")
            if value in ("", None):
                continue
            record = {
                "candidate_id": cid,
                "display_name": name,
                "latest_polled_share": float(value),
                "poll_id": row["poll_id"],
                "date_conducted": row["date_conducted"],
            }
            if cid not in latest or record["date_conducted"] > latest[cid]["date_conducted"]:
                latest[cid] = record
    return sorted(
        latest.values(), key=lambda r: (r["date_conducted"], r["latest_polled_share"]), reverse=True
    )
