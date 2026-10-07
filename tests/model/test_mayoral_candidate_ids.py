import json
from datetime import date

import pytest

from backend.model.mayoral_candidate_ids import (
    load_campaign_suspensions,
    load_canonical_mayoral_candidate_ids,
    mayoral_candidate_id,
)


def test_major_candidates_keep_poll_compatible_ids() -> None:
    assert mayoral_candidate_id("Olivia", "Chow") == "chow"
    assert mayoral_candidate_id("Brad", "Bradford") == "bradford"
    assert mayoral_candidate_id("Chris", "Alexander") == "alexander"


def test_minor_candidate_ids_are_normalized_name_slugs() -> None:
    assert mayoral_candidate_id("José María", "Núñez") == "jose-maria-nunez"
    assert mayoral_candidate_id("  Odessa Paloma ", " Parker ") == "odessa-paloma-parker"


@pytest.mark.parametrize("schema_version", [3, 4, 5, 6])
def test_canonical_ids_accept_results_owned_full_career_feed(tmp_path, schema_version: int) -> None:
    path = tmp_path / "mayoral_candidates.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": schema_version,
                "ballot_certified": True,
                "coverage": {
                    "policy": "full_verified_canadian_electoral_career",
                    "jurisdiction": "Canada",
                    "year_cutoff": None,
                },
                "candidates": [
                    {"person_id": "per_chow", "candidacy_id": "can_chow"},
                    {"person_id": None, "candidacy_id": "can_unresolved"},
                ],
            }
        )
    )

    assert load_canonical_mayoral_candidate_ids(path) == ("per_chow", "can_unresolved")


def test_canonical_ids_reject_unknown_schema(tmp_path) -> None:
    path = tmp_path / "mayoral_candidates.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "ballot_certified": True,
                "coverage": {},
                "candidates": [],
            }
        )
    )

    with pytest.raises(ValueError, match="unsupported Results mayoral candidate feed schema"):
        load_canonical_mayoral_candidate_ids(path)


def _schema_6(tmp_path, candidates, schema_version=6):
    path = tmp_path / "mayoral_candidates.json"
    path.write_text(
        json.dumps(
            {"schema_version": schema_version, "ballot_certified": True, "candidates": candidates}
        )
    )
    return path


def test_campaign_suspensions_come_from_the_schema_6_feed(tmp_path) -> None:
    path = _schema_6(
        tmp_path,
        [
            {"person_id": "per_chow", "candidacy_id": "can_chow", "campaign_suspended_on": None},
            {
                "person_id": "per_alex",
                "candidacy_id": "can_alex",
                "campaign_suspended_on": "2026-10-06",
            },
            {"person_id": None, "candidacy_id": "can_x", "campaign_suspended_on": "2026-09-01"},
        ],
    )
    assert load_campaign_suspensions(path) == {
        "per_alex": date(2026, 10, 6),
        "can_x": date(2026, 9, 1),
    }


def test_campaign_suspensions_refuse_an_older_results_feed(tmp_path) -> None:
    path = _schema_6(tmp_path, [{"person_id": "per_chow", "candidacy_id": "c"}], schema_version=5)
    with pytest.raises(ValueError, match="schema 6"):
        load_campaign_suspensions(path)


@pytest.mark.parametrize(
    "row", [{}, {"campaign_suspended_on": "Oct 6"}, {"campaign_suspended_on": "20261006"}]
)
def test_campaign_suspensions_require_the_field_as_an_iso_date_or_null(tmp_path, row) -> None:
    path = _schema_6(tmp_path, [{"person_id": "per_alex", "candidacy_id": "c", **row}])
    with pytest.raises(ValueError, match="campaign_suspended_on"):
        load_campaign_suspensions(path)
