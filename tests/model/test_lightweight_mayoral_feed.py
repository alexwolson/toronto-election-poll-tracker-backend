"""The lightweight poll-average model is the published mayoral forecast producer.
It emits schema v3 keyed by canonical Results person IDs (the frontend contract),
mapping the model's local poll keys via the certified candidate feed.

Hermetic: the builder reads the hydrated ``data/upstream/results/mayoral_candidates.json``
(produced by the release chain, not committed), so the tests construct a fixture root
with that file plus a polls.csv, rather than depending on a hydrated tree.
"""

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from backend.model.lightweight_mayoral_feed import (
    MAYORAL_FORECAST_FEED_SCHEMA_VERSION,
    build_lightweight_mayoral_forecast_feed,
)

CHOW = "per_chow0000000000000000000000000"
BRAD = "per_brad0000000000000000000000000"
ALEX = "per_alex0000000000000000000000000"
LIVE = {
    "election_cycle_id": "toronto-2026",
    "viable_field": [CHOW, BRAD, ALEX],  # order: incumbent/leader first (ADR frame)
    "incumbent_candidate_id": CHOW,
}


def _fixture_root(tmp_path: Path) -> Path:
    results = tmp_path / "data/upstream/results"
    results.mkdir(parents=True)
    (results / "mayoral_candidates.json").write_text(
        json.dumps(
            {
                "schema_version": 5,
                "ballot_certified": True,
                "candidates": [
                    {"person_id": CHOW, "display_name": "Olivia Chow"},
                    {"person_id": BRAD, "display_name": "Brad Bradford"},
                    {"person_id": ALEX, "display_name": "Chris Alexander"},
                ],
            }
        )
    )
    polls = tmp_path / "polls"
    polls.mkdir()
    # Minimal descriptive polls.csv covering the full viable field, Chow ahead.
    (polls / "polls.csv").write_text(
        "poll_id,firm,date_conducted,sample_size,alexander,bradford,chow,other\n"
        "mainstreet-2026-09-14,Mainstreet Research,2026-09-17,1000,0.096,0.377,0.458,0.069\n"
        "liaison-2026-09-05,Liaison Strategies,2026-09-05,600,0.10,0.39,0.50,0.01\n"
        "pallas-2026-08-21,Pallas Data,2026-08-21,611,0.08,0.393,0.501,0.026\n"
    )
    return tmp_path


def _build(tmp_path: Path) -> dict:
    root = _fixture_root(tmp_path)
    return build_lightweight_mayoral_forecast_feed(
        root,
        LIVE,
        polls_dir=root / "polls",
        analysis_cutoff=datetime(2026, 9, 21, 12, 0, tzinfo=ZoneInfo("America/Toronto")),
    )


def test_feed_is_schema_v3_keyed_by_canonical_person_ids(tmp_path: Path) -> None:
    feed = _build(tmp_path)
    assert feed["schema_version"] == MAYORAL_FORECAST_FEED_SCHEMA_VERSION == 3
    assert feed["publication_policy"] == "central-band-with-sensitivity-v1"
    assert set(feed["candidate_win"]) == set(LIVE["viable_field"])
    assert feed["incumbent_candidate_id"] == LIVE["incumbent_candidate_id"]
    assert feed["forecast_favourite"]["candidate_id"] in LIVE["viable_field"]
    for pid, card in feed["candidate_win"].items():
        assert card["candidate_id"] == pid
        assert card["availability"] == "Forecast Available"
        assert 0.0 <= card["probability"] <= 1.0
        assert card["sensitivity"]["lower"] <= card["probability"] <= card["sensitivity"]["upper"]
        assert {s["label"] for s in card["sensitivity"]["scenarios"]} == {
            "bridge-base",
            "stable",
            "volatile",
        }


def test_named_win_probabilities_sum_to_about_one(tmp_path: Path) -> None:
    feed = _build(tmp_path)
    total = sum(card["probability"] for card in feed["candidate_win"].values())
    assert abs(total - 1.0) < 0.05


def test_incumbent_chow_leads_and_only_full_field_polls_are_used(tmp_path: Path) -> None:
    feed = _build(tmp_path)
    assert feed["forecast_favourite"]["candidate_id"] == CHOW
    assert set(feed["final_field_samples"]) == {
        "mainstreet-2026-09-14",
        "liaison-2026-09-05",
        "pallas-2026-08-21",
    }


def test_margin_distribution_is_nonnegative_over_a_nonnegative_gap(tmp_path: Path) -> None:
    md = _build(tmp_path)["margin_distribution"]
    assert md["unit"] == "share_gap"
    assert all(x >= 0 for x in md["x"])
    assert all(d >= 0 for d in md["density"])
