"""Stable current-cycle identifiers for registered mayoral candidates."""

from __future__ import annotations

import csv
import json
import re
import unicodedata
from datetime import date
from pathlib import Path

_MAJOR_IDS = {
    ("olivia", "chow"): "chow",
    ("brad", "bradford"): "bradford",
    ("chris", "alexander"): "alexander",
}


def mayoral_candidate_id(first_name: str, last_name: str) -> str:
    """Return the poll-compatible current-cycle ID for one registered name."""
    first = first_name.strip()
    last = last_name.strip()
    known = _MAJOR_IDS.get((first.lower(), last.lower()))
    if known:
        return known
    ascii_name = (
        unicodedata.normalize("NFKD", f"{first} {last}").encode("ascii", "ignore").decode().lower()
    )
    candidate_id = re.sub(r"[^a-z0-9]+", "-", ascii_name).strip("-")
    if not candidate_id:
        raise ValueError("mayoral candidate name does not produce an id")
    return candidate_id


def load_mayoral_candidate_ids(path: str | Path) -> tuple[str, ...]:
    """Read the registered field in source order and return unique IDs."""
    ids: list[str] = []
    with Path(path).open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            candidate_id = mayoral_candidate_id(row["first_name"], row["last_name"])
            if candidate_id in ids:
                raise ValueError(f"duplicate mayoral candidate id: {candidate_id}")
            ids.append(candidate_id)
    return tuple(ids)


def load_canonical_mayoral_candidate_ids(path: str | Path) -> tuple[str, ...]:
    """Load the certified field using Results-owned Person/Candidacy keys."""

    with Path(path).open(encoding="utf-8") as handle:
        feed = json.load(handle)
    schema_version = feed.get("schema_version")
    if schema_version not in {2, 3, 4, 5, 6}:
        raise ValueError("unsupported Results mayoral candidate feed schema")
    if not feed.get("ballot_certified"):
        raise ValueError("Results mayoral field is not certified")
    if schema_version in {3, 4, 5, 6}:
        coverage = feed.get("coverage", {})
        if (
            coverage.get("policy") != "full_verified_canadian_electoral_career"
            or coverage.get("jurisdiction") != "Canada"
            or coverage.get("year_cutoff") is not None
        ):
            raise ValueError("Results mayoral field has unsupported career coverage")
    ids = tuple(
        candidate.get("person_id") or candidate["candidacy_id"] for candidate in feed["candidates"]
    )
    if len(ids) != len(set(ids)):
        raise ValueError("Results mayoral field contains duplicate canonical candidate IDs")
    return ids


SUSPENSION_SCHEMA_VERSION = 6
_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def load_campaign_suspensions(path: str | Path) -> dict[str, date]:
    """Suspended Campaign start dates by canonical candidate id, from the Results feed.

    The forecast needs schema 6, where every candidate carries ``campaign_suspended_on``
    (an ISO date, or null when the campaign was never suspended); an older feed fails
    closed rather than silently reading as "nobody suspended".
    """
    with Path(path).open(encoding="utf-8") as handle:
        feed = json.load(handle)
    if feed.get("schema_version") != SUSPENSION_SCHEMA_VERSION:
        raise ValueError(
            "the forecast needs the Results mayoral candidate feed at schema 6 "
            f"(campaign_suspended_on); got {feed.get('schema_version')!r}"
        )
    out: dict[str, date] = {}
    for candidate in feed["candidates"]:
        cid = candidate.get("person_id") or candidate["candidacy_id"]
        if "campaign_suspended_on" not in candidate:
            raise ValueError(f"Results candidate {cid} lacks campaign_suspended_on")
        value = candidate["campaign_suspended_on"]
        if value is None:
            continue
        if not isinstance(value, str) or not _ISO_DATE.match(value):
            raise ValueError(f"Results candidate {cid} has an invalid campaign_suspended_on")
        out[cid] = date.fromisoformat(value)
    return out
