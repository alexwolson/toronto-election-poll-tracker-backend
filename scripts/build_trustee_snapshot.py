#!/usr/bin/env python3
"""Build descriptive trustee race cards from a hydrated Results release."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.model.trustee_race_card import build_trustee_race_cards, load_trustee_races
from backend.release_inputs import load_release_input_paths


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    inputs = load_release_input_paths(args.input_manifest)
    snapshot = build_trustee_race_cards(load_trustee_races(inputs.trustee_races))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        json.dump(snapshot, handle, allow_nan=False, separators=(",", ":"))

    ward_count = sum(len(board["wards"]) for board in snapshot["boards"])
    signals = [
        f"{board['board_id']} {ward['ward_id']}"
        for board in snapshot["boards"]
        for ward in board["wards"]
        if ward["race_context"]["signal"] is not None
    ]
    print(f"Trustee race cards written to {args.output}")
    print(f"  {ward_count} wards | prior-win signals: {', '.join(signals) or 'none'}")


if __name__ == "__main__":
    main()
