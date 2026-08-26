"""Shared semantic filters for canonical Results release rows."""

from __future__ import annotations


def is_completed_result(row: dict[str, str]) -> bool:
    """Return whether a canonical candidacy belongs to a completed contest."""

    return row.get("result_status", "").strip().lower() == "final"
