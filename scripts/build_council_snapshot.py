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
from backend.model.council_endorsements import load_endorsements
from backend.model.council_hints import (
    load_officeholding_history,
    load_supported_hints,
)
from backend.model.council_race import load_registered_field, load_ward_incumbency
from backend.model.council_race_card import load_ward_poll_readings
from backend.model.council_snapshot import build_council_snapshot, load_ward_names
from backend.model.council_suspensions import (
    COUNCIL_CAMPAIGN_SUSPENSIONS_FILENAME,
    load_council_campaign_suspensions,
)
from backend.model.ward_poll_context import historical_benchmark, poll_contexts
from backend.release_inputs import load_release_input_paths

RAW = ROOT / "data" / "raw"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    inputs = load_release_input_paths(args.input_manifest)
    canonical = inputs.election_results
    polls = load_ward_poll_readings(inputs.polling_dir / "ward_poll_readings.csv")
    benchmark = historical_benchmark(RAW / "polls/historical_council/poll_responses.csv", canonical)
    context = poll_contexts(polls, inputs.polling_dir, benchmark)
    benchmark["model"]["named_share_shape_sensitivity_max_endpoint_difference"] = (
        max(
            abs(row[key] - item["sensitivity"]["logistic_normal_shape"][key][index])
            for item in context.values()
            for index, row in enumerate(item["rows"])
            for key in ["lower", "upper"]
        )
        if context
        else 0.0
    )
    benchmark["model"]["shape_sensitivity_max_endpoint_difference"] = (
        max(
            abs(item["leader"]["ranges"][0][key] - item["leader"]["ranges"][1][key])
            for item in context.values()
            for key in ["lower", "upper"]
        )
        if context
        else 0.0
    )
    snapshot = build_council_snapshot(
        load_ward_incumbency(RAW / "defeatability" / "ward_defeatability.csv"),
        load_registered_field(canonical),
        load_council_results(canonical),
        polls,
        ward_names=load_ward_names(inputs.electoral_districts),
        officeholding=load_officeholding_history(canonical, inputs.electoral_districts),
        supported_hints=load_supported_hints(RAW / "hints" / "supported_historical_hints.csv"),
        geometry_path=inputs.electoral_districts_parquet,
        endorsements=load_endorsements(inputs.results_dir),
        poll_context=context,
        poll_benchmark=benchmark,
        campaign_suspensions=load_council_campaign_suspensions(
            inputs.results_dir / COUNCIL_CAMPAIGN_SUSPENSIONS_FILENAME
        ),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        json.dump(snapshot, handle, allow_nan=False, indent=None)

    wards = snapshot["wards"]
    open_seats = [w for w, c in wards.items() if c["is_open_seat"]]
    polled = [w for w, c in wards.items() if c["ward_polls"]]
    disagree = [w for w, c in wards.items() if c["incumbency_flag_disagrees"]]
    suspended = [w for w, c in wards.items() if c["incumbent_campaign_suspended_on"]]
    print(f"Council race cards written to {args.output}")
    print(
        f"  {len(wards)} wards | open seats: {sorted(open_seats, key=int)} "
        f"| with ward polls: {sorted(polled, key=int)} "
        f"| incumbent suspended campaign: {sorted(suspended, key=int)}"
    )
    if disagree:
        # Field membership contradicts the CDI is_running flag: a departed/moved
        # incumbent the flag hasn't caught up to. Review + refresh ward_defeatability.csv.
        print(f"  incumbency flag disagrees (review): {sorted(disagree, key=int)}")


if __name__ == "__main__":
    main()
