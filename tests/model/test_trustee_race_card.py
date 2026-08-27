from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from backend.model.trustee_race_card import (
    CONTINUOUS_METHOD,
    TDSB_METHOD,
    TRUSTEE_RACE_CARD_SCHEMA_VERSION,
    build_trustee_race_cards,
    validate_trustee_race_cards,
)

FIXTURE = Path(__file__).parents[1] / "fixtures/trustee_races.json"


def _source() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _board(payload: dict, board_id: str) -> dict:
    return next(board for board in payload["boards"] if board["board_id"] == board_id)


def _ward(payload: dict, board_id: str, ward_id: str) -> dict:
    return next(ward for ward in _board(payload, board_id)["wards"] if ward["ward_id"] == ward_id)


def _set_latest_share(payload: dict, board_id: str, ward_id: str, share: float) -> None:
    ward = _ward(payload, board_id, ward_id)
    incumbent = next(candidate for candidate in ward["candidates"] if candidate["is_incumbent"])
    represented_body = _board(payload, board_id)["represented_body"]
    wins = [
        election
        for election in incumbent["past_elections"]
        if election["office_type"] == "trustee"
        and election["represented_body"] == represented_body
        and election["district_name"] == f"Ward {ward_id}"
        and election["result"] == "won"
    ]
    latest = max(wins, key=lambda election: election["election_date"])
    latest["vote_share"] = share
    ward["comparable_prior_result"]["winner_share"] = share


def test_current_fixture_builds_all_wards_and_serializes_cleanly() -> None:
    cards = build_trustee_race_cards(_source())

    assert cards["schema_version"] == TRUSTEE_RACE_CARD_SCHEMA_VERSION
    assert sum(len(board["wards"]) for board in cards["boards"]) == 29
    assert all("race_context" in ward for board in cards["boards"] for ward in board["wards"])
    json.dumps(cards, allow_nan=False)


def test_tdsb_uses_field_structure_and_approved_order() -> None:
    cards = build_trustee_race_cards(_source())
    wards = _board(cards, "tdsb")["wards"]

    assert [(ward["ward_id"], ward["race_context"]["category"]) for ward in wards] == [
        ("2", "open"),
        ("5", "open"),
        ("9", "open"),
        ("10", "open"),
        ("11", "open"),
        ("1", "two_incumbents"),
        ("3", "one_incumbent"),
        ("4", "one_incumbent"),
        ("6", "one_incumbent"),
        ("7", "one_incumbent"),
        ("8", "one_incumbent"),
        ("12", "one_incumbent"),
    ]
    assert all(ward["race_context"]["method"] == TDSB_METHOD for ward in wards)
    assert all(ward["race_context"]["signal"] is None for ward in wards)


def test_tdsb_acclamation_precedes_incumbent_count() -> None:
    source = _source()
    ward = _ward(source, "tdsb", "1")
    ward["acclaimed"] = True
    cards = build_trustee_race_cards(source)

    assert _ward(cards, "tdsb", "1")["race_context"] == {
        "method": TDSB_METHOD,
        "category": "acclaimed",
        "sort_priority": 3,
        "signal": None,
    }


def test_only_current_tcdsb_wards_4_and_5_fire_vote_share_signal() -> None:
    cards = build_trustee_race_cards(_source())
    fired = [
        (board["board_id"], ward["ward_id"], ward["race_context"]["signal"])
        for board in cards["boards"]
        for ward in board["wards"]
        if ward["race_context"]["signal"] is not None
    ]

    assert [(board, ward) for board, ward, _ in fired] == [("tcdsb", "4"), ("tcdsb", "5")]
    assert fired[0][2] == {
        "key": "prior_win_under_50",
        "subject_person_id": "per_0277eb81ad4d5dc7a2bc6e55e4756875",
        "subject_name": "Teresa Lubinski",
        "election_year": 2022,
        "vote_share": pytest.approx(0.48851581957384),
    }
    assert fired[1][2]["subject_name"] == "Maria Rizzo"
    assert fired[1][2]["vote_share"] == pytest.approx(0.4521140436049077)


@pytest.mark.parametrize(
    ("share", "category"),
    [
        (0.499999, "won_without_majority"),
        (0.50, "contested_incumbent"),
        (0.500001, "contested_incumbent"),
    ],
)
def test_under_50_threshold_is_strict(share: float, category: str) -> None:
    source = _source()
    _set_latest_share(source, "tcdsb", "4", share)

    context = _ward(build_trustee_race_cards(source), "tcdsb", "4")["race_context"]

    assert context["category"] == category
    assert (context["signal"] is not None) is (category == "won_without_majority")


def test_name_only_match_cannot_fire_signal() -> None:
    source = _source()
    incumbent = next(
        candidate
        for candidate in _ward(source, "tcdsb", "4")["candidates"]
        if candidate["is_incumbent"]
    )
    incumbent["person_id"] = None

    context = _ward(build_trustee_race_cards(source), "tcdsb", "4")["race_context"]

    assert context["category"] == "contested_incumbent"
    assert context["signal"] is None


def test_conflicting_prior_result_fails_closed() -> None:
    source = _source()
    _ward(source, "tcdsb", "4")["comparable_prior_result"]["winner_share"] = 0.40

    context = _ward(build_trustee_race_cards(source), "tcdsb", "4")["race_context"]

    assert context["category"] == "contested_incumbent"
    assert context["signal"] is None


@pytest.mark.parametrize(("board_id", "ward_id"), [("viamonde", "3"), ("monavenir", "4")])
def test_january_2023_rerun_is_the_applicable_prior_win(board_id: str, ward_id: str) -> None:
    source = _source()
    _set_latest_share(source, board_id, ward_id, 0.49)

    context = _ward(build_trustee_race_cards(source), board_id, ward_id)["race_context"]

    assert context["category"] == "won_without_majority"
    assert context["signal"]["election_year"] == 2023


def test_continuous_boards_are_sorted_by_context_then_ward() -> None:
    cards = build_trustee_race_cards(_source())
    tcdsb = _board(cards, "tcdsb")["wards"]

    assert [ward["ward_id"] for ward in tcdsb] == [
        "1",
        "7",
        "9",
        "10",
        "4",
        "5",
        "2",
        "3",
        "8",
        "11",
        "6",
        "12",
    ]
    assert all(ward["race_context"]["method"] == CONTINUOUS_METHOD for ward in tcdsb)


def test_validator_rejects_invalid_signal_and_order() -> None:
    cards = build_trustee_race_cards(_source())
    malformed = copy.deepcopy(cards)
    _ward(malformed, "tcdsb", "4")["race_context"]["signal"]["vote_share"] = 0.50
    with pytest.raises(ValueError, match="invalid prior_win_under_50"):
        validate_trustee_race_cards(malformed)

    malformed = copy.deepcopy(cards)
    _board(malformed, "tcdsb")["wards"].reverse()
    with pytest.raises(ValueError, match="not in context order"):
        validate_trustee_race_cards(malformed)
