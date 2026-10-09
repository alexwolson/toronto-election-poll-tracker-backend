import json
from pathlib import Path

import pytest

from backend.model.council_suspensions import load_council_campaign_suspensions


def _write(path: Path, **overrides) -> Path:
    feed = {
        "schema_version": 1,
        "election_date": "2026-10-26",
        "suspensions": [
            {
                "candidacy_id": "can_w5",
                "person_id": "per_w5",
                "display_name": "Ward Incumbent",
                "ward": "5",
                "campaign_suspended_on": "2026-10-09",
            }
        ],
    }
    feed.update(overrides)
    path.write_text(json.dumps(feed), encoding="utf-8")
    return path


def test_loads_suspension_dates_by_candidacy(tmp_path: Path) -> None:
    assert load_council_campaign_suspensions(_write(tmp_path / "f.json")) == {
        "can_w5": "2026-10-09"
    }


def test_an_empty_feed_records_no_suspension(tmp_path: Path) -> None:
    assert load_council_campaign_suspensions(_write(tmp_path / "f.json", suspensions=[])) == {}


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"schema_version": 2}, "schema 1"),
        (
            {"suspensions": [{"candidacy_id": "can_w5", "campaign_suspended_on": "Oct 9"}]},
            "invalid campaign_suspended_on",
        ),
        (
            {"suspensions": [{"candidacy_id": "can_w5", "campaign_suspended_on": "2026-10-27"}]},
            "after election day",
        ),
        (
            {
                "suspensions": [
                    {"candidacy_id": "can_w5", "campaign_suspended_on": "2026-10-09"},
                    {"candidacy_id": "can_w5", "campaign_suspended_on": "2026-10-10"},
                ]
            },
            "repeated",
        ),
    ],
    ids=["schema", "bad_date", "after_election_day", "repeated"],
)
def test_rejects_a_feed_it_cannot_trust(tmp_path: Path, overrides, message) -> None:
    with pytest.raises(ValueError, match=message):
        load_council_campaign_suspensions(_write(tmp_path / "f.json", **overrides))


def test_a_missing_feed_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_council_campaign_suspensions(tmp_path / "absent.json")
