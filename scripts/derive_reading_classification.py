#!/usr/bin/env python3
"""Derive the tracked reading-classification table from the research register.

The 2026-09-12 measurement classification register (research artifact, 1.2 MB)
annotates every poll reading with a measurement class, denominator semantics and
same-sample dependence group. The compact mayoral model needs only those columns.
This script writes them to ``data/raw/polls/mayoral_reading_classification.csv``
and records the register's SHA-256 in a sidecar provenance JSON.

    uv run python scripts/derive_reading_classification.py \
        docs/research/mayoral-measurement-classification-2026-09-12.json
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "data" / "raw" / "polls" / "mayoral_reading_classification.csv"
PROVENANCE = OUTPUT.with_suffix(".provenance.json")
COLUMNS = (
    "poll_reading_id",
    "election_cycle_id",
    "corpus",
    "scope",
    "measurement_class",
    "denominator_semantics",
    "same_sample_dependence_group",
)


def derive(register_path: Path, output: Path = OUTPUT, provenance: Path = PROVENANCE) -> int:
    payload = json.loads(register_path.read_text(encoding="utf-8"))
    rows = sorted(
        ({column: reading[column] for column in COLUMNS} for reading in payload["readings"]),
        key=lambda r: (
            r["election_cycle_id"],
            r["same_sample_dependence_group"],
            r["poll_reading_id"],
        ),
    )
    ids = [r["poll_reading_id"] for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("register contains duplicate reading ids")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    provenance.write_text(
        json.dumps(
            {
                "source": str(register_path.resolve().relative_to(ROOT))
                if register_path.resolve().is_relative_to(ROOT)
                else str(register_path),
                "source_sha256": hashlib.sha256(register_path.read_bytes()).hexdigest(),
                "register_as_of": payload.get("as_of"),
                "derived_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                "rows": len(rows),
                "columns": list(COLUMNS),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("register", type=Path)
    args = parser.parse_args()
    print(f"wrote {derive(args.register)} rows to {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
