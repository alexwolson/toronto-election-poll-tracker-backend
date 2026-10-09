"""Inputs for the compact model: one canonical ordinary reading per independent sample.

Historical campaigns come from the audited corpus that every Polling release
carries (``historical_mayoral_*.csv`` beside the 2026 tables; ADR 0060), filtered
by the release's reading-classification table, with the canonical outcomes table
and the election-dates manifest. The current campaign comes from the same
release's poll tables and the hydrated Results candidate feed. One selection rule
serves both: each sample's ordinary reading is chosen by its own
``denominator_semantics`` (ADR 0057).

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

Once a Suspended Campaign has started (its date from the Results candidates feed,
schema 6), a 2026 reading whose fieldwork overlaps or follows that date is a
Post-Suspension Reading: a composition over the remaining named candidates, with
any share it reports for the suspended candidate set aside, and in its sample the
full field beats a head-to-head (Polling's ``reading_classification.csv``; backend
issue 31). Earlier readings still need all three named candidates.

A sample listed in Polling's ``model_exclusions.csv`` is never modelled: the
maintainer kept it out of the fit, and it stays in the record (ADR 0062).
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from backend.model.compact_mayoral.exits import Exit, kept_fraction_prior, load_cases
from backend.model.mayoral_candidate_ids import load_campaign_suspensions, mayoral_candidate_id

ROOT = Path(__file__).resolve().parents[3]
OUTCOMES = ROOT / "data" / "raw" / "elections" / "mayoral_outcomes.csv"
ELECTIONS = ROOT / "data" / "raw" / "elections" / "mayoral_elections.csv"
# Historical corpus tables in a Polling release directory (flat release assets).
HISTORICAL_PREFIX = "historical_mayoral_"

ORDINARY = "campaign_vote_intention"
# One reading per sample, every campaign alike: what the pollster did about
# undecided respondents, best first (post-lean expressed choice is the reference
# signal). ``other`` (turnout screens, leaner tables that keep undecideds,
# unreported denominators) is used only when a sample publishes nothing else;
# ties go to the reading naming more candidates, then to id. Entered per reading
# at ingestion (Polling SCHEMA).
DENOMINATOR_RANK = {
    "decided_plus_leaners": 0,
    "decided_only": 1,
    "all_respondents": 2,
    "other": 9,
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
    # Suspended Campaigns applied in this campaign (the forecast campaign only; C2).
    exits: tuple[Exit, ...] = ()


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


def _campaign_polls(
    key, candidate_ids, names, election_date, polls, outcome_shares, tail, exits=()
):
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
        exits=tuple(exits),
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
    polling_dir: Path,
    *,
    outcomes_csv: Path = OUTCOMES,
    elections_csv: Path = ELECTIONS,
    min_offered: int = 2,
) -> dict[str, CampaignPolls]:
    """The historical campaigns from a Polling release's corpus and classification."""
    polling_dir = Path(polling_dir)

    def table(name: str) -> list[dict]:
        return _read_csv(polling_dir / f"{HISTORICAL_PREFIX}{name}.csv")

    samples = {r["poll_sample_id"]: r for r in table("poll_samples")}
    readings = {r["poll_reading_id"]: r for r in table("poll_readings")}
    responses = defaultdict(list)
    for row in table("poll_responses"):
        responses[row["poll_reading_id"]].append(row)
    ordinary = [
        readings[r["poll_reading_id"]]
        for r in table("reading_classification")
        if r["scope"] == "citywide_mayoral" and r["measurement_class"] == ORDINARY
    ]
    outcomes = defaultdict(dict)
    for row in _read_csv(outcomes_csv):
        outcomes[row["election_cycle_id"]][row["candidate_id"]] = row
    election_dates = {
        r["election_cycle_id"]: date.fromisoformat(r["election_date"])
        for r in _read_csv(elections_csv)
    }

    by_cycle = defaultdict(list)
    for r in ordinary:
        by_cycle[samples[r["poll_sample_id"]]["election_cycle_id"]].append(r)

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
        for r in rows:  # a sample's readings are dependent evidence: one poll each
            groups[r["poll_sample_id"]].append(r)
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


# Polling's 2026 reading classification, shipped in every Polling release beside the
# poll tables; an explicit head-to-head is an ``alternative_ballot`` reading.
READING_CLASSIFICATION = "reading_classification.csv"
ALTERNATIVE_BALLOT = "alternative_ballot"
# Polling's model exclusions: samples the maintainer kept out of the fit. They stay
# in the record and the archive; no reading of theirs is modelled (ADR 0062).
MODEL_EXCLUSIONS = "model_exclusions.csv"


def _current_field(candidates_json: Path, extra_named: tuple[tuple[str, str], ...]):
    """(poll column slugs, display names, canonical ids) of the named 2026 candidates."""
    display = {_normalize(name): cid for cid, name, _ in certified_candidates(candidates_json)}
    field = (*CURRENT_FIELD, *extra_named)
    columns = [column for column, _ in field]
    names = tuple(name for _, name in field)
    ids = tuple(display.get(_normalize(name), column) for column, name in field)
    return columns, names, ids


def _suspended(candidates_json: Path, ids: tuple[str, ...], cutoff: date) -> dict[int, date]:
    """Named candidates whose Suspended Campaign started on or before ``cutoff``.

    The dates come from the Results candidates feed, which must be at schema 6.
    """
    starts = load_campaign_suspensions(candidates_json)
    suspended = {
        i: starts[cid] for i, cid in enumerate(ids) if cid in starts and starts[cid] <= cutoff
    }
    base = range(len(CURRENT_FIELD))
    if len([i for i in base if i not in suspended]) < 2:
        raise ValueError("fewer than two named candidates remain after the Suspended Campaigns")
    return suspended


def _select_current_readings(
    polling_dir: Path,
    columns: list[str],
    require_full_field: bool,
    suspended: dict[int, date],
):
    """(sample, reading, shares by slug, present indices, base, departed) per modelled sample.

    A reading is eligible when it is a general vote-intention reading of the mayoral
    contest whose published candidates cover the certified three (or any two of them
    when the field is not required). Among a sample's eligible readings the best
    denominator wins; ties go to the reading naming more candidates, then to id.
    The base is the chosen reading's own (weighted, reported, unweighted), never the
    recruited sample size unless the reading reports no base at all.

    A Post-Suspension Reading is one whose fieldwork overlaps or follows the start of a
    Suspended Campaign in ``suspended`` (its fieldwork ends on or after that date). It
    is a composition over the remaining named candidates, who must all be present
    when the field is required; any share it reports for a ``departed`` candidate is
    set aside. In a Post-Suspension sample the full field beats a head-to-head: an
    ``alternative_ballot`` reading counts only when it is the sample's only general
    vote-intention reading, whatever its denominator (backend issue 31).
    """
    polling_dir = Path(polling_dir)
    excluded = {r["poll_sample_id"] for r in _read_csv(polling_dir / MODEL_EXCLUSIONS)}
    classes = {
        r["poll_reading_id"]: r["measurement_class"]
        for r in _read_csv(polling_dir / READING_CLASSIFICATION)
    }
    samples = [
        s
        for s in _read_csv(polling_dir / "poll_samples.csv")
        if s["election_cycle_id"] == CURRENT_KEY
        and s["geography_type"] == "citywide"
        and s["extraction_status"] == "extracted"
        and s["poll_sample_id"] not in excluded
    ]
    readings = defaultdict(list)
    for r in _read_csv(polling_dir / "poll_readings.csv"):
        if r["contest_type"] == "mayoral" and r["reading_purpose"] == "general_vote_intention":
            readings[r["poll_sample_id"]].append(r)
    shares_by_reading: dict[str, dict[str, float]] = defaultdict(dict)
    for row in _read_csv(polling_dir / "poll_responses.csv"):
        if row["response_kind"] != "candidate" or row["share"] == "":
            continue
        # The Polling bundle keys candidates by ``source_candidate_id`` (the response
        # slug, e.g. "chow") beside the canonical ``person_id``; the backend's model
        # copy collapses both into ``candidate_id``. CURRENT_FIELD is in slugs.
        key = row.get("source_candidate_id") or row.get("candidate_id") or ""
        if key:
            shares_by_reading[row["poll_reading_id"]][key] = float(row["share"])

    def measurement(reading: dict) -> str:
        rid = reading["poll_reading_id"]
        if rid not in classes:
            raise ValueError(f"2026 reading {rid} has no reading classification")
        return classes[rid]

    base_count = len(CURRENT_FIELD)
    selected = []
    for s in samples:
        end = date.fromisoformat(s["fieldwork_end"])
        departed = tuple(sorted(i for i, start in suspended.items() if start <= end))
        remaining = base_count - len([i for i in departed if i < base_count])
        need = remaining if require_full_field else 2
        options = readings[s["poll_sample_id"]]
        if departed:
            full_field = [r for r in options if measurement(r) != ALTERNATIVE_BALLOT]
            options = full_field or options
        candidates = []
        for r in options:
            shares = shares_by_reading[r["poll_reading_id"]]
            present = [
                i for i, column in enumerate(columns) if column in shares and i not in departed
            ]
            if len([i for i in present if i < base_count]) < need:
                continue
            rank = DENOMINATOR_RANK.get(r["denominator_semantics"], 9)
            candidates.append((rank, -len(present), r["poll_reading_id"], r, shares, present))
        if not candidates:
            continue
        _, _, _, r, shares, present = min(candidates, key=lambda c: c[:3])
        base = _first_number(
            r["weighted_base"], r["reported_base"], r["unweighted_base"], s["recruited_sample_size"]
        )
        if base is None:
            continue
        selected.append((s, r, shares, present, base, departed))
    return selected


def current_reading_selection(
    polling_dir: Path,
    candidates_json: Path,
    *,
    cutoff: date,
    require_full_field: bool = True,
    extra_named: tuple[tuple[str, str], ...] = (),
) -> list[dict]:
    """The reading chosen for each modelled 2026 sample, for the feed's model record.

    ``post_suspension`` marks a Post-Suspension Reading; ``set_aside`` lists the
    suspended candidates whose reported share it carried but the model did not use.
    """
    columns, _, ids = _current_field(candidates_json, extra_named)
    suspended = _suspended(candidates_json, ids, cutoff)
    rows = []
    for s, r, shares, present, base, departed in _select_current_readings(
        polling_dir, columns, require_full_field, suspended
    ):
        rows.append(
            {
                "poll_sample_id": s["poll_sample_id"],
                "poll_reading_id": r["poll_reading_id"],
                "pollster": s["pollster"],
                "fieldwork_end": s["fieldwork_end"],
                "denominator_semantics": r["denominator_semantics"],
                "base": base,
                "named_share": sum(shares[columns[i]] for i in present),
                "post_suspension": bool(departed),
                "set_aside": [ids[i] for i in departed if columns[i] in shares],
            }
        )
    rows.sort(key=lambda row: (row["fieldwork_end"], row["poll_sample_id"]))
    return rows


def current_campaign(
    polling_dir: Path,
    candidates_json: Path,
    *,
    election_date: date,
    cutoff: date,
    require_full_field: bool = True,
    extra_named: tuple[tuple[str, str], ...] = (),
) -> CampaignPolls:
    """The 2026 campaign from the hydrated Polling bundle (certified field only by default).

    One reading per sample by denominator rank (see ``DENOMINATOR_RANK``),
    renormalized over the named candidates it reports, weighted by that reading's
    own base times the named share. ``extra_named`` adds (response slug, display
    name) pairs as further named candidates; a poll offers them only when it
    reported them, otherwise its composition is conditional on the names it did
    report. The certified-field rule applies to the base three only.

    Suspended Campaigns that started on or before ``cutoff`` (Results feed, schema 6)
    become the campaign's ``exits`` (C2, ``exits.py``), each with the ten-case
    kept-fraction prior; Post-Suspension Readings enter over the remaining named
    candidates (see ``_select_current_readings``).
    """
    columns, names, ids = _current_field(candidates_json, extra_named)
    suspended = _suspended(candidates_json, ids, cutoff)
    polls = []
    for s, r, shares, present, base, _ in _select_current_readings(
        polling_dir, columns, require_full_field, suspended
    ):
        raw = [shares[columns[i]] for i in present]
        total = sum(raw)
        polls.append(
            Poll(
                reading_id=r["poll_reading_id"],
                group=s["poll_sample_id"],
                firm=s["pollster"],
                days_before_election=(election_date - date.fromisoformat(s["fieldwork_end"])).days,
                n_eff=base * total,
                offered=tuple(present),
                shares=tuple(x / total for x in raw),
            )
        )
    exits = ()
    if suspended:
        mu, sigma = kept_fraction_prior(load_cases())
        exits = tuple(
            Exit(i, start, (election_date - start).days, mu, sigma)
            for i, start in sorted(suspended.items(), key=lambda item: (item[1], item[0]))
        )
    return _campaign_polls(CURRENT_KEY, ids, names, election_date, polls, None, None, exits)


def minor_candidates_reported(
    polling_dir: Path, candidates_json: Path, *, cutoff: date
) -> list[dict]:
    """Certified candidates outside the modelled three that a modelled reading reported.

    Reads the readings the fit itself uses (``_select_current_readings``), so a
    Post-Suspension Reading counts and an Excluded Poll never does. Returns the latest
    reported share per candidate, newest poll first.
    """
    base_slugs = {slug for slug, _ in CURRENT_FIELD}
    minors = {
        slug: (cid, name)
        for cid, name, slug in certified_candidates(candidates_json)
        if slug not in base_slugs
    }
    columns, _, ids = _current_field(candidates_json, ())
    suspended = _suspended(candidates_json, ids, cutoff)
    latest: dict[str, dict] = {}
    for s, _, shares, _, _, _ in _select_current_readings(polling_dir, columns, True, suspended):
        for slug, (cid, name) in minors.items():
            if slug not in shares:
                continue
            record = {
                "candidate_id": cid,
                "display_name": name,
                "latest_polled_share": shares[slug],
                "poll_id": s["poll_sample_id"],
                "date_conducted": s["fieldwork_end"],
            }
            if cid not in latest or record["date_conducted"] > latest[cid]["date_conducted"]:
                latest[cid] = record
    return sorted(
        latest.values(), key=lambda r: (r["date_conducted"], r["latest_polled_share"]), reverse=True
    )
