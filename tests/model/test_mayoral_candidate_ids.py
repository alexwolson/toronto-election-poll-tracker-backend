import json

import pytest

from backend.model.mayoral_candidate_ids import (
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


@pytest.mark.parametrize("schema_version", [3, 4, 5])
def test_canonical_ids_accept_results_owned_full_career_feed(
    tmp_path, schema_version: int
) -> None:
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
