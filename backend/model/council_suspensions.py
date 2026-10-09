"""Councillor Suspended Campaign dates from the pinned Results release (Results ADR 0010)."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

COUNCIL_CAMPAIGN_SUSPENSIONS_SCHEMA_VERSION = 1
COUNCIL_CAMPAIGN_SUSPENSIONS_FILENAME = "council_campaign_suspensions.json"


def _iso_date(value: object) -> date | None:
    try:
        parsed = date.fromisoformat(str(value))
    except ValueError:
        return None
    return parsed if parsed.isoformat() == value else None


def load_council_campaign_suspensions(path: str | Path) -> dict[str, str]:
    """Map each suspended councillor Candidacy to its date; fail closed on a bad feed.

    An empty mapping means no councillor Suspended Campaign is recorded. A missing
    file raises, so a Results release too old to carry the feed cannot build cards.
    """

    feed = json.loads(Path(path).read_text(encoding="utf-8"))
    if feed.get("schema_version") != COUNCIL_CAMPAIGN_SUSPENSIONS_SCHEMA_VERSION:
        raise ValueError(
            "council campaign suspensions feed must be schema 1; "
            f"got {feed.get('schema_version')!r}"
        )
    election_day = _iso_date(feed.get("election_date"))
    if election_day is None:
        raise ValueError("council campaign suspensions feed has an invalid election_date")
    dates: dict[str, str] = {}
    for entry in feed["suspensions"]:
        candidacy_id = entry["candidacy_id"]
        suspended_on = _iso_date(entry["campaign_suspended_on"])
        if suspended_on is None:
            raise ValueError(
                f"council suspension {candidacy_id} has an invalid campaign_suspended_on"
            )
        if suspended_on > election_day:
            raise ValueError(f"council suspension {candidacy_id} is dated after election day")
        if candidacy_id in dates:
            raise ValueError(f"council suspension {candidacy_id} is repeated")
        dates[candidacy_id] = entry["campaign_suspended_on"]
    return dates
