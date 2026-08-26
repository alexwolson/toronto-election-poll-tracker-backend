from pathlib import Path

import pytest

from backend.model.council_hints import CandidacyRecord, load_officeholding_history
from backend.model.mayoral_candidates_feed import (
    MAYORAL_CANDIDATES_FEED_SCHEMA_VERSION,
    MayoralRegistration,
    build_mayoral_candidates_feed,
    load_registered_mayoral_candidates,
)

ROOT = Path(__file__).resolve().parents[2]
FIELD = ROOT / "data/raw/candidates/mayor_registered.csv"
RESULTS = ROOT / "data/raw/canonical/election_results.csv"


def registration(first: str, last: str) -> MayoralRegistration:
    return MayoralRegistration(first, last, "Active", "2026-08-01")


def record(person_id: str, *, date: str = "2023-06-26") -> CandidacyRecord:
    return CandidacyRecord(
        person_id=person_id,
        office_type="mayor",
        election_date=date,
        is_win=True,
        vote_share=0.37,
        margin=0.03,
        contest_id=f"mayor-{date}",
        represented_body="toronto_city_council",
        vote_rank=1,
        field_size=102,
    )


def live_cycle(**overrides):
    return {
        "election_cycle_id": "toronto-2026",
        "field_certified": True,
        "incumbent_candidate_id": "chow",
        **overrides,
    }


def test_certified_feed_attaches_unique_history_and_marks_incumbent() -> None:
    registrations = (registration("Olivia", "Chow"), registration("Alex", "Smith"))
    officeholding = (
        {"p1": [record("p1", date="2023-06-26"), record("p1", date="2014-10-27")]},
        {"p1": {frozenset({"olivia", "chow"})}},
    )

    feed = build_mayoral_candidates_feed(registrations, live_cycle(), officeholding)

    assert feed["schema_version"] == MAYORAL_CANDIDATES_FEED_SCHEMA_VERSION == 1
    assert feed["ballot_certified"] is True
    chow = feed["candidates"][0]
    assert chow["display_name"] == "Olivia Chow"
    assert chow["candidate_id"] == "chow"
    assert chow["person_id"] == "p1"
    assert chow["is_matched"] is True
    assert chow["is_incumbent"] is True
    assert [race["election_date"] for race in chow["past_elections"]] == [
        "2023-06-26",
        "2014-10-27",
    ]
    smith = feed["candidates"][1]
    assert smith["person_id"] is None
    assert smith["is_matched"] is False
    assert smith["past_elections"] == []


def test_ambiguous_name_is_not_guessed() -> None:
    registrations = (registration("Alex", "Smith"),)
    officeholding = (
        {"p1": [record("p1")], "p2": [record("p2")]},
        {
            "p1": {frozenset({"alex", "smith"})},
            "p2": {frozenset({"alex", "smith"})},
        },
    )

    [candidate] = build_mayoral_candidates_feed(
        registrations, live_cycle(), officeholding
    )["candidates"]

    assert candidate["person_id"] is None
    assert candidate["is_matched"] is False
    assert candidate["past_elections"] == []


def test_uncertified_feed_never_exposes_a_provisional_field() -> None:
    feed = build_mayoral_candidates_feed(
        (registration("Olivia", "Chow"),),
        live_cycle(field_certified=False),
        ({}, {}),
    )
    assert feed["ballot_certified"] is False
    assert feed["candidates"] == []


def test_duplicate_current_cycle_ids_fail_loudly() -> None:
    duplicate = registration("Alex", "Smith")
    with pytest.raises(ValueError, match="duplicate mayoral candidate id"):
        build_mayoral_candidates_feed((duplicate, duplicate), live_cycle(), ({}, {}))


def test_inactive_registrations_are_excluded() -> None:
    withdrawn = MayoralRegistration("Alex", "Smith", "Withdrawn", "2026-08-01")
    feed = build_mayoral_candidates_feed(
        (registration("Olivia", "Chow"), withdrawn), live_cycle(), ({}, {})
    )
    assert [candidate["display_name"] for candidate in feed["candidates"]] == [
        "Olivia Chow"
    ]


def test_committed_certified_field_contains_all_53_candidates_once() -> None:
    registrations = load_registered_mayoral_candidates(FIELD)
    feed = build_mayoral_candidates_feed(
        registrations,
        live_cycle(),
        load_officeholding_history(RESULTS),
    )
    candidates = feed["candidates"]
    assert len(candidates) == 53
    assert len({candidate["candidate_id"] for candidate in candidates}) == 53
    names = [candidate["display_name"] for candidate in candidates]
    assert names == sorted(names, key=lambda name: tuple(reversed(name.rsplit(" ", 1))))
