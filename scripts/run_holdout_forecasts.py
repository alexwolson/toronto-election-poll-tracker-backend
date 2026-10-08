#!/usr/bin/env python3
"""Held-out mayoral forecasts on the production path (election-night spec S4).

Hides one historical campaign's result, keeps its polls from at least
``--horizon-days`` out, and runs production's own joint fit of the compact model
(every other campaign, the 2026 campaign with its Suspended Campaigns, population
hyperpriors, production settings, the qualification gate and its retry). Writes
that campaign's Election Outcome Draws and a provenance record (see
``write_draws``); a fit that fails the gate writes nothing.

The inputs must be a production Backend release's: hydrate its Results and
Polling pins (``backend.release_inputs.hydrate_release_inputs``), download its
``release_manifest.json`` and ``mayoral_forecast.json`` into one directory, and
run from a clean checkout::

    uv run python scripts/run_holdout_forecasts.py \\
        --input-manifest data/upstream/input_manifest.json \\
        --production-release dist/backend-2026-10-07.1 \\
        --holdout toronto_2023 --horizon-days 1 --out dist/holdout-1d

The driver refuses hydrated inputs whose manifests differ from the release's
pins, and takes the release's analysis cutoff. Fits run on the CPU, never a GPU.
"""

from __future__ import annotations

import argparse
import csv
import dataclasses
import hashlib
import json
import shlex
import subprocess
import sys
import tempfile
import time
from datetime import UTC, date, datetime
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.model.compact_mayoral.hyperpriors import population_hyperpriors
from backend.model.compact_mayoral.qualification import qualify
from backend.model.compact_mayoral.readings import (
    OUTCOMES,
    CampaignPolls,
    current_campaign,
    historical_campaigns,
    with_horizon,
)
from backend.model.compact_mayoral.sampling import PRODUCTION, FitResult
from backend.model.compact_mayoral_feed import TORONTO, _qualified_fit, forecast_draws
from backend.model.publication_manifest import load_live_cycle
from backend.release_bundle import DRAWS_ARRAYS
from backend.release_inputs import ReleaseInputPaths, load_release_input_paths, sha256_file


def holdout_campaigns(
    polling_dir: Path,
    candidates_json: Path,
    *,
    held_out: str,
    horizon_days: int,
    election_date: date,
    cutoff: date,
    outcomes_csv: Path = OUTCOMES,
) -> tuple[CampaignPolls, ...]:
    """Production's joint-fit campaigns with ``held_out``'s result hidden.

    The campaign is read from an outcomes table whose rows for it keep the ballot
    (ids and names) but not the count: production orders a campaign's candidates
    by final share, so nulling the outcome after reading would still pass the
    result to the fit through that order. With the count masked the order falls to
    candidate id; the model treats candidates symmetrically, so the order changes
    only which random numbers go where. Then only polls at least ``horizon_days``
    out are kept. Every other campaign, and 2026, is exactly production's.
    """
    with tempfile.TemporaryDirectory() as tmp:
        masked = _mask_result(Path(outcomes_csv), held_out, Path(tmp) / "outcomes.csv")
        history = historical_campaigns(polling_dir, outcomes_csv=masked)
    hidden = with_horizon(history[held_out], horizon_days)
    history[held_out] = dataclasses.replace(hidden, outcome_shares=None, outcome_tail=None)
    current = current_campaign(
        polling_dir, candidates_json, election_date=election_date, cutoff=cutoff
    )
    return (*history.values(), current)


def _mask_result(outcomes_csv: Path, cycle: str, destination: Path) -> Path:
    """A copy of the outcomes table with one campaign's count removed (ballot kept)."""
    with outcomes_csv.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fields, rows = reader.fieldnames, list(reader)
    if not any(r["election_cycle_id"] == cycle for r in rows):
        raise ValueError(f"no outcome rows for {cycle}")
    for row in rows:
        if row["election_cycle_id"] == cycle:
            row.update(votes="1", valid_vote_total="", share="0", is_winner="")
    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return destination


def run_holdout(
    polling_dir: Path,
    candidates_json: Path,
    *,
    held_out: str,
    horizon_days: int,
    election_date: date,
    cutoff: date,
) -> tuple[CampaignPolls, FitResult]:
    """Production's fit (settings, hyperpriors, gate and retry) with one result hidden.

    Raises ``QualificationError`` if the fit fails the gate after its retry.
    """
    campaigns = holdout_campaigns(
        polling_dir,
        candidates_json,
        held_out=held_out,
        horizon_days=horizon_days,
        election_date=election_date,
        cutoff=cutoff,
    )
    result = _qualified_fit(campaigns, population_hyperpriors(), PRODUCTION, qualify)
    return {c.key: c for c in campaigns}[held_out], result


def write_draws(out_dir: Path, held: CampaignPolls, result: FitResult, provenance: dict) -> Path:
    """Write the held-out campaign's Election Outcome Draws and their record.

    ``<campaign>.npz`` holds ``candidate_ids``, ``full_ballot`` (draws x named
    candidates, shares of valid votes) and ``residual_pool`` (draws: every other
    candidate on the ballot); each draw sums to 1. ``<campaign>.json`` records the
    command, Backend commit, inputs, seed and diagnostics, and the npz's sha256.
    Existing files are never overwritten. Returns the record's path.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    npz, record_path = out_dir / f"{held.key}.npz", out_dir / f"{held.key}.json"
    for path in (npz, record_path):
        if path.exists():
            raise FileExistsError(f"refusing to overwrite {path}")
    arrays = forecast_draws(held, result.draws)
    with npz.open("xb") as handle:
        np.savez_compressed(handle, **arrays)
    settings = result.settings
    record = {
        "campaign": held.key,
        **provenance,
        "election_date": held.election_date.isoformat(),
        "candidates": [
            {"candidate_id": cid, "name": name}
            for cid, name in zip(held.candidates, held.names, strict=True)
        ],
        "draws": int(arrays["full_ballot"].shape[0]),
        "npz": npz.name,
        "npz_sha256": hashlib.sha256(npz.read_bytes()).hexdigest(),
        "arrays": DRAWS_ARRAYS,
        "polls_used": len(held.polls),
        "latest_poll_days_before_election": min(p.days_before_election for p in held.polls),
        "fit": {
            "seed": settings.seed,
            "target_accept": settings.target_accept,
            "retried": settings != PRODUCTION,
            "warmup": settings.warmup,
            "chains": settings.chains,
            "draws_per_chain": settings.draws,
            "diagnostics": result.diagnostics.as_dict(),
            "elapsed_seconds": round(result.elapsed_seconds, 1),
        },
    }
    record_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return record_path


def _production_inputs(production_dir: Path, inputs: ReleaseInputPaths) -> tuple[datetime, dict]:
    """The release's analysis cutoff, and its pins after checking the hydrated inputs."""
    manifest = json.loads((production_dir / "release_manifest.json").read_text(encoding="utf-8"))
    forecast = json.loads((production_dir / "mayoral_forecast.json").read_text(encoding="utf-8"))
    pins = {"production_source_commit": manifest["source_commit"]}
    for name, directory in (("results", inputs.results_dir), ("polling", inputs.polling_dir)):
        pinned = manifest["dependencies"][name]
        hydrated = sha256_file(directory / "release_manifest.json")
        if hydrated != pinned["manifest_sha256"]:
            raise SystemExit(
                f"hydrated {name} inputs are not the production release's {pinned['release']} "
                f"(manifest sha256 {hydrated} != {pinned['manifest_sha256']})"
            )
        pins[name] = {"release": pinned["release"], "manifest_sha256": hydrated}
    return datetime.fromisoformat(forecast["analysis_cutoff"]), pins


# Paths whose contents must match the production release's source commit.
TRACKED = ("backend", "data/raw")


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def main(argv: list[str] | None = None) -> None:
    argv = sys.argv[1:] if argv is None else argv
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--input-manifest", type=Path, required=True)
    parser.add_argument("--production-release", type=Path, required=True)
    parser.add_argument("--holdout", required=True, help="historical campaign, e.g. toronto_2023")
    parser.add_argument("--horizon-days", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if _git("status", "--porcelain"):
        parser.error("refusing to run from a dirty working tree: the record names a commit")
    commit = _git("rev-parse", "HEAD")
    inputs = load_release_input_paths(args.input_manifest)
    cutoff, pins = _production_inputs(args.production_release, inputs)
    # The model code and the tracked election tables (outcomes, dates, live cycle)
    # must be production's too, not only the hydrated releases.
    if _git("diff", "--name-only", pins["production_source_commit"], "HEAD", "--", *TRACKED):
        parser.error("model code or tracked inputs differ from the production release's commit")
    live_cycle = load_live_cycle(ROOT / "data" / "raw" / "elections" / "live_cycle.json")

    started = time.monotonic()
    held, result = run_holdout(
        inputs.polling_dir,
        inputs.results_dir / "mayoral_candidates.json",
        held_out=args.holdout,
        horizon_days=args.horizon_days,
        election_date=date.fromisoformat(live_cycle["election_date"]),
        cutoff=cutoff.astimezone(TORONTO).date(),
    )
    wall = time.monotonic() - started
    path = write_draws(
        args.out,
        held,
        result,
        {
            "horizon_days": args.horizon_days,
            "command": shlex.join([Path(sys.executable).name, sys.argv[0], *argv]),
            "backend_commit": commit,
            "inputs": {**pins, "analysis_cutoff": cutoff.isoformat()},
            "wall_seconds": round(wall, 1),
            "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        },
    )
    print(
        f"[holdout] {held.key} at {args.horizon_days} d: {wall:.0f}s, "
        f"divergences {result.diagnostics.divergences}, "
        f"retried {result.settings != PRODUCTION}; wrote {path}",
        flush=True,
    )


if __name__ == "__main__":
    main()
