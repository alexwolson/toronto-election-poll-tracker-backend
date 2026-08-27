"""Build descriptive trustee race cards from the Results-owned trustee feed.

This module assigns factual race context and ordering only. It does not model an
election outcome, infer identity from names, or estimate trustee electorate size.
"""

from __future__ import annotations

import copy
import json
import math
import re
from pathlib import Path

TRUSTEE_RACE_CARD_SCHEMA_VERSION = 2

TDSB_METHOD = "tdsb_field_structure"
CONTINUOUS_METHOD = "continuous_ward_vote_share"

TDSB_PRIORITIES = {
    "open": 0,
    "two_incumbents": 1,
    "one_incumbent": 2,
    "acclaimed": 3,
}
CONTINUOUS_PRIORITIES = {
    "open": 0,
    "won_without_majority": 1,
    "contested_incumbent": 2,
    "acclaimed": 3,
}

_WARD_NAME = re.compile(r"Ward\s+(\d+)\Z")
_SHARE_TOLERANCE = 1e-12


def load_trustee_races(path: str | Path) -> dict:
    """Read the Results-owned trustee feed without adapting its identities."""

    with Path(path).open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if payload.get("schema_version") not in {1, 2, 3} or not isinstance(payload.get("boards"), list):
        raise ValueError("unsupported trustee races input")
    return payload


def _incumbents(ward: dict) -> list[dict]:
    return [candidate for candidate in ward["candidates"] if candidate.get("is_incumbent") is True]


def _context(method: str, category: str, signal: dict | None = None) -> dict:
    priorities = TDSB_PRIORITIES if method == TDSB_METHOD else CONTINUOUS_PRIORITIES
    return {
        "method": method,
        "category": category,
        "sort_priority": priorities[category],
        "signal": signal,
    }


def _tdsb_context(ward: dict) -> dict:
    if ward.get("acclaimed") is True:
        return _context(TDSB_METHOD, "acclaimed")
    incumbent_count = len(_incumbents(ward))
    if incumbent_count == 0:
        return _context(TDSB_METHOD, "open")
    if incumbent_count == 1:
        return _context(TDSB_METHOD, "one_incumbent")
    if incumbent_count == 2:
        return _context(TDSB_METHOD, "two_incumbents")
    raise ValueError(f"TDSB ward {ward.get('ward_id')} has more than two incumbents")


def _applicable_prior_win(candidate: dict, board: dict, ward: dict) -> dict | None:
    """Return the latest canonically linked win that agrees with the prior-result fact."""

    if not candidate.get("person_id"):
        return None
    ward_id = str(ward["ward_id"])
    matches: list[dict] = []
    for election in candidate.get("past_elections", []):
        district = election.get("district_name")
        parsed = _WARD_NAME.fullmatch(district) if isinstance(district, str) else None
        if (
            election.get("office_type") == "trustee"
            and election.get("represented_body") == board.get("represented_body")
            and election.get("result") == "won"
            and election.get("rank") == 1
            and parsed is not None
            and parsed.group(1) == ward_id
            and isinstance(election.get("vote_share"), int | float)
            and election.get("election_date", "") < "2026-10-26"
        ):
            matches.append(election)
    if not matches:
        return None
    latest_date = max(election["election_date"] for election in matches)
    latest = [election for election in matches if election["election_date"] == latest_date]
    if len(latest) != 1:
        return None
    election = latest[0]
    prior = ward.get("comparable_prior_result")
    if not isinstance(prior, dict):
        return None
    if election.get("year") != prior.get("year"):
        return None
    if not isinstance(prior.get("winner_share"), int | float) or not math.isclose(
        float(election["vote_share"]),
        float(prior["winner_share"]),
        rel_tol=0,
        abs_tol=_SHARE_TOLERANCE,
    ):
        return None
    return election


def _continuous_context(board: dict, ward: dict) -> dict:
    if ward.get("acclaimed") is True:
        return _context(CONTINUOUS_METHOD, "acclaimed")
    incumbents = _incumbents(ward)
    if not incumbents:
        return _context(CONTINUOUS_METHOD, "open")
    if len(incumbents) != 1:
        return _context(CONTINUOUS_METHOD, "contested_incumbent")
    incumbent = incumbents[0]
    prior_win = _applicable_prior_win(incumbent, board, ward)
    if prior_win is None or float(prior_win["vote_share"]) >= 0.50:
        return _context(CONTINUOUS_METHOD, "contested_incumbent")
    return _context(
        CONTINUOUS_METHOD,
        "won_without_majority",
        {
            "key": "prior_win_under_50",
            "subject_person_id": incumbent["person_id"],
            "subject_name": incumbent["display_name"],
            "election_year": prior_win["year"],
            "vote_share": prior_win["vote_share"],
        },
    )


def validate_trustee_race_cards(payload: dict) -> None:
    """Reject internally inconsistent backend trustee-card artifacts."""

    if payload.get("schema_version") != TRUSTEE_RACE_CARD_SCHEMA_VERSION:
        raise ValueError("unsupported trustee race card schema")
    boards = payload.get("boards")
    if not isinstance(boards, list):
        raise TypeError("trustee race cards require boards")
    for board in boards:
        board_id = board.get("board_id")
        method = TDSB_METHOD if board_id == "tdsb" else CONTINUOUS_METHOD
        priorities = TDSB_PRIORITIES if method == TDSB_METHOD else CONTINUOUS_PRIORITIES
        wards = board.get("wards")
        if not isinstance(wards, list):
            raise TypeError(f"trustee board {board_id} requires wards")
        order: list[tuple[int, int]] = []
        for ward in wards:
            context = ward.get("race_context")
            if not isinstance(context, dict) or context.get("method") != method:
                raise ValueError(f"trustee ward {board_id}/{ward.get('ward_id')} has wrong method")
            category = context.get("category")
            if category not in priorities or context.get("sort_priority") != priorities[category]:
                raise ValueError(
                    f"trustee ward {board_id}/{ward.get('ward_id')} has invalid category priority"
                )
            signal = context.get("signal")
            if category == "won_without_majority":
                if not isinstance(signal, dict):
                    raise ValueError("won_without_majority requires a signal")
                share = signal.get("vote_share")
                if (
                    signal.get("key") != "prior_win_under_50"
                    or not isinstance(signal.get("subject_person_id"), str)
                    or not signal["subject_person_id"]
                    or not isinstance(signal.get("subject_name"), str)
                    or not signal["subject_name"]
                    or not isinstance(signal.get("election_year"), int)
                    or not isinstance(share, int | float)
                    or not math.isfinite(float(share))
                    or not 0 <= float(share) < 0.50
                ):
                    raise ValueError("invalid prior_win_under_50 signal")
            elif signal is not None:
                raise ValueError(f"trustee category {category} cannot carry a signal")
            order.append((priorities[category], int(ward["ward_id"])))
        if order != sorted(order):
            raise ValueError(f"trustee board {board_id} wards are not in context order")


def build_trustee_race_cards(source: dict) -> dict:
    """Carry through Results facts and add one backend-owned context per ward."""

    payload = copy.deepcopy(source)
    payload["schema_version"] = TRUSTEE_RACE_CARD_SCHEMA_VERSION
    for board in payload["boards"]:
        for ward in board["wards"]:
            ward["race_context"] = (
                _tdsb_context(ward)
                if board.get("board_id") == "tdsb"
                else _continuous_context(board, ward)
            )
        board["wards"].sort(
            key=lambda ward: (ward["race_context"]["sort_priority"], int(ward["ward_id"]))
        )
    validate_trustee_race_cards(payload)
    return payload
