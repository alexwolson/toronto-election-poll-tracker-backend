#!/usr/bin/env python3
"""Build the frontend publication package (INT).

Emits the typed data feeds the frontend ingests into an explicit output directory:
  - mayoral_forecast.json  schema 4: joint election-day distributions from the
                           compact model (ADR 0054); the fit must pass the
                           numerical qualification gate or this build fails
  - manifest.json          model index + live-cycle Final-Ballot state
The council feed (council_race_cards.json) is produced by build_council_snapshot.py.

Run with ``--input-manifest`` and ``--output-dir``.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.model.compact_mayoral_feed import (
    MAYORAL_FORECAST_FEED_SCHEMA_VERSION,
    build_compact_mayoral_forecast_feed,
)
from backend.model.council_snapshot import COUNCIL_RACE_CARD_SCHEMA_VERSION
from backend.model.publication_manifest import (
    build_publication_manifest,
    load_live_cycle,
)
from backend.model.trustee_race_card import TRUSTEE_RACE_CARD_SCHEMA_VERSION
from backend.release_inputs import load_release_input_paths


def _publication_summary(forecast: dict) -> dict:
    margin = forecast["election_day"]["pairwise_margin"]
    return {
        "evidence_tier": forecast["evidence_tier"],
        "publication_policy": forecast["publication_policy"],
        "forecast_favourite": forecast["forecast_favourite"]["availability"],
        "candidate_win": {
            candidate_id: card["availability"]
            for candidate_id, card in forecast["candidate_win"].items()
        },
        "pairwise_margin": {
            "leader_candidate_id": margin["leader_candidate_id"],
            "challenger_candidate_id": margin["challenger_candidate_id"],
        },
        "qualification_passed": forecast["model"]["qualification_passed"],
    }


RAW = ROOT / "data" / "raw"


def _write(output_dir: Path, name: str, payload: dict) -> None:
    path = output_dir / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, allow_nan=False, indent=None)
    shown = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
    print(f"  wrote {shown}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--analysis-cutoff", type=datetime.fromisoformat)
    args = parser.parse_args()
    inputs = load_release_input_paths(args.input_manifest)
    cutoff = args.analysis_cutoff or datetime.now(ZoneInfo("America/Toronto"))
    if cutoff.utcoffset() is None:
        parser.error("--analysis-cutoff requires an offset-aware timestamp")
    as_of = cutoff.astimezone(ZoneInfo("America/Toronto")).date().isoformat()

    live_cycle = load_live_cycle(RAW / "elections" / "live_cycle.json")
    # The compact model reads the release's descriptive polls.csv for the current
    # campaign (hydrated into the polling bundle dir) and the backend-tracked audited
    # corpus for history; it fits, qualifies (fail closed) and assembles schema 4.
    forecast = build_compact_mayoral_forecast_feed(
        ROOT,
        live_cycle,
        polls_dir=inputs.polling_dir,
        analysis_cutoff=cutoff,
    )
    _write(args.output_dir, "mayoral_forecast.json", forecast)

    manifest = build_publication_manifest(
        as_of=as_of,
        live_cycle=live_cycle,
        feed_versions={
            "mayoral_forecast": MAYORAL_FORECAST_FEED_SCHEMA_VERSION,
            "council_race_cards": COUNCIL_RACE_CARD_SCHEMA_VERSION,
            "trustee_race_cards": TRUSTEE_RACE_CARD_SCHEMA_VERSION,
        },
        mayoral_publication_summary=_publication_summary(forecast),
    )
    _write(args.output_dir, "manifest.json", manifest)

    print(
        f"Publication package built (as of {as_of}); "
        f"Final Ballot certified: {manifest['election']['final_ballot_certified']}"
    )


if __name__ == "__main__":
    main()
