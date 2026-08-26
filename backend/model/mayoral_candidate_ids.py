"""Stable current-cycle identifiers for registered mayoral candidates."""

from __future__ import annotations

import csv
import re
import unicodedata
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
        unicodedata.normalize("NFKD", f"{first} {last}")
        .encode("ascii", "ignore")
        .decode()
        .lower()
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
