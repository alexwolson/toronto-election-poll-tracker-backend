#!/usr/bin/env python3
"""Build the Council v1 race-card snapshot (ADR 0043).

Assembles the 25 descriptive race cards and writes them to the explicit output
path. Descriptive only — no forecast — and independent of the mayoral pipeline
(ADR 0014).

Run with ``--input-manifest`` and ``--output``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.model.council_biography import load_council_results
from backend.model.council_hints import (
    load_officeholding_history,
    load_supported_hints,
)
from backend.model.council_race import load_registered_field, load_ward_incumbency
from backend.model.council_race_card import load_ward_poll_readings
from backend.model.council_snapshot import build_council_snapshot, load_ward_names
from backend.release_inputs import load_release_input_paths

RAW = ROOT / "data" / "raw"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    inputs = load_release_input_paths(args.input_manifest)
    canonical = inputs.election_results
    snapshot = build_council_snapshot(
        load_ward_incumbency(RAW / "defeatability" / "ward_defeatability.csv"),
        load_registered_field(canonical),
        load_council_results(canonical),
        load_ward_poll_readings(inputs.polling_dir / "ward_poll_readings.csv"),
        ward_names=load_ward_names(inputs.electoral_districts),
        officeholding=load_officeholding_history(canonical, inputs.electoral_districts),
        supported_hints=load_supported_hints(RAW / "hints" / "supported_historical_hints.csv"),
        geometry_path=inputs.electoral_districts_parquet,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        json.dump(snapshot, handle, allow_nan=False, indent=None)

    wards = snapshot["wards"]
    open_seats = [w for w, c in wards.items() if c["is_open_seat"]]
    polled = [w for w, c in wards.items() if c["ward_polls"]]
    disagree = [w for w, c in wards.items() if c["incumbency_flag_disagrees"]]
    print(f"Council race cards written to {args.output}")
    print(
        f"  {len(wards)} wards | open seats: {sorted(open_seats, key=int)} "
        f"| with ward polls: {sorted(polled, key=int)}"
    )
    if disagree:
        # Field membership contradicts the CDI is_running flag: a departed/moved
        # incumbent the flag hasn't caught up to. Review + refresh ward_defeatability.csv.
        print(f"  incumbency flag disagrees (review): {sorted(disagree, key=int)}")


if __name__ == "__main__":
    main()
