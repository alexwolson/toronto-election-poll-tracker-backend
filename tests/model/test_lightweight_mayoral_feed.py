"""The lightweight poll-average model is the published mayoral forecast producer.
It emits schema v3 keyed by canonical Results person IDs (the frontend contract),
mapping the model's local poll keys via the certified candidate feed."""

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from backend.model.lightweight_mayoral_feed import (
    MAYORAL_FORECAST_FEED_SCHEMA_VERSION,
    build_lightweight_mayoral_forecast_feed,
)
from backend.model.publication_manifest import load_live_cycle

ROOT = Path(__file__).resolve().parents[2]


def _polls_dir(tmp_path: Path) -> Path:
    # Minimal descriptive polls.csv covering the full viable field, Chow ahead.
    (tmp_path / "polls.csv").write_text(
        "poll_id,firm,date_conducted,sample_size,alexander,bradford,chow,other\n"
        "mainstreet-2026-09-14,Mainstreet Research,2026-09-17,1000,0.096,0.377,0.458,0.069\n"
        "liaison-2026-09-05,Liaison Strategies,2026-09-05,600,0.10,0.39,0.50,0.01\n"
        "pallas-2026-08-21,Pallas Data,2026-08-21,611,0.08,0.393,0.501,0.026\n"
    )
    return tmp_path


def _build(tmp_path: Path) -> dict:
    live = load_live_cycle(ROOT / "data/raw/elections/live_cycle.json")
    return build_lightweight_mayoral_forecast_feed(
        ROOT,
        live,
        polls_dir=_polls_dir(tmp_path),
        analysis_cutoff=datetime(2026, 9, 21, 12, 0, tzinfo=ZoneInfo("America/Toronto")),
    )


def test_feed_is_schema_v3_keyed_by_canonical_person_ids(tmp_path: Path) -> None:
    live = load_live_cycle(ROOT / "data/raw/elections/live_cycle.json")
    feed = _build(tmp_path)
    assert feed["schema_version"] == MAYORAL_FORECAST_FEED_SCHEMA_VERSION == 3
    assert feed["publication_policy"] == "central-band-with-sensitivity-v1"
    assert set(feed["candidate_win"]) == set(live["viable_field"])
    assert feed["incumbent_candidate_id"] == live["incumbent_candidate_id"]
    assert feed["forecast_favourite"]["candidate_id"] in live["viable_field"]
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
    live = load_live_cycle(ROOT / "data/raw/elections/live_cycle.json")
    feed = _build(tmp_path)
    # Chow (the incumbent person id) is the favourite on this Chow-ahead fixture.
    assert feed["forecast_favourite"]["candidate_id"] == live["incumbent_candidate_id"]
    # All three fixture polls cover the full field, so all are used.
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
