"""Confirmed endorsements for council race cards (ADR 0058).

Reads the endorsement tables every Results release carries (``endorsers.csv``,
``endorsements.csv``, ``endorsement_assertions.csv``) and groups the confirmed
facts by candidacy. Descriptive only: an endorsement is an observed fact shown
on the card, never a model input, and a candidate with no row has simply not
been recorded as endorsed (the dataset is open-world).
"""

from __future__ import annotations

import csv
from pathlib import Path


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_endorsements(results_dir: str | Path) -> dict[str, list[dict]]:
    """``candidacy_id`` -> its confirmed endorsements, ordered by endorser name.

    Returns an empty mapping when the release carries no endorsement tables.
    """
    root = Path(results_dir)
    paths = [
        root / name for name in ("endorsers.csv", "endorsements.csv", "endorsement_assertions.csv")
    ]
    if not all(path.is_file() for path in paths):
        return {}
    endorsers = {row["endorser_id"]: row for row in _rows(paths[0])}
    assertions: dict[str, dict[str, str]] = {}
    for row in _rows(paths[2]):
        key = row["endorsement_id"]
        if row["review_state"] == "confirmed" and key and key not in assertions:
            assertions[key] = row
    grouped: dict[str, list[dict]] = {}
    for fact in _rows(paths[1]):
        endorser = endorsers[fact["endorser_id"]]
        source = assertions.get(fact["endorsement_id"], {})
        grouped.setdefault(fact["candidacy_id"], []).append(
            {
                "endorser_id": fact["endorser_id"],
                "endorser_name": endorser["canonical_name"],
                "endorser_type": endorser["endorser_type"],
                "kind": source.get("endorsement_kind") or None,
                "announced": source.get("announcement_date") or None,
                "date_precision": source.get("date_precision") or None,
                "source_url": source.get("source_url") or None,
            }
        )
    for records in grouped.values():
        records.sort(key=lambda record: record["endorser_name"])
    return grouped
