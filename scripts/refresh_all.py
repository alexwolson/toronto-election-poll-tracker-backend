#!/usr/bin/env python3
"""Rebuild backend feeds from exact Results and Polling release bundles.

This command performs no upstream scraping or identity matching. It validates the
release dependency chain, hydrates model inputs, runs the model checks and builds
an immutable backend release bundle that pins both upstream releases.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYTHON = sys.executable
DEFAULT_RESULTS = ROOT.parent.parent / "toronto-election-results" / "dist"
DEFAULT_POLLING = ROOT.parent / "toronto-election-poll-tracker-data" / "dist"


def _run(label: str, command: list[str], *, dry_run: bool) -> None:
    print(f"\n{label}\n  {' '.join(command)}")
    if not dry_run:
        subprocess.run(command, cwd=ROOT, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-bundle", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--polling-bundle", type=Path, default=DEFAULT_POLLING)
    parser.add_argument("--results-release", required=True)
    parser.add_argument("--polling-release", required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    parser.add_argument("--skip-tests", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    input_manifest = ROOT / "data" / "upstream" / "input_manifest.json"
    generated = ROOT / "data" / "upstream" / "generated"

    hydrate_code = (
        "from backend.release_inputs import hydrate_release_inputs; "
        f"hydrate_release_inputs({str(ROOT)!r}, {str(args.results_bundle)!r}, "
        f"{str(args.polling_bundle)!r}, results_release={args.results_release!r})"
    )
    _run(
        "Validate and hydrate upstream releases",
        [PYTHON, "-c", hydrate_code],
        dry_run=args.dry_run,
    )
    _run(
        "Run Ruff lint",
        [PYTHON, "-m", "ruff", "check", "."],
        dry_run=args.dry_run,
    )
    _run(
        "Check Ruff formatting",
        [PYTHON, "-m", "ruff", "format", "--check", "."],
        dry_run=args.dry_run,
    )
    if not args.skip_tests:
        _run("Run backend test suite", [PYTHON, "-m", "pytest", "-q"], dry_run=args.dry_run)
    _run(
        "Build mayoral forecast",
        [
            PYTHON,
            "scripts/build_publication_snapshot.py",
            "--input-manifest",
            str(input_manifest),
            "--output-dir",
            str(generated),
        ],
        dry_run=args.dry_run,
    )
    _run(
        "Build council race cards",
        [
            PYTHON,
            "scripts/build_council_snapshot.py",
            "--input-manifest",
            str(input_manifest),
            "--output",
            str(generated / "council_race_cards.json"),
        ],
        dry_run=args.dry_run,
    )
    _run(
        "Build trustee race cards",
        [
            PYTHON,
            "scripts/build_trustee_snapshot.py",
            "--input-manifest",
            str(input_manifest),
            "--output",
            str(generated / "trustee_race_cards.json"),
        ],
        dry_run=args.dry_run,
    )
    _run(
        "Build pinned backend release bundle",
        [
            PYTHON,
            "-m",
            "backend.release_bundle",
            "build",
            "--processed",
            str(generated),
            "--results-bundle",
            str(args.results_bundle),
            "--polling-bundle",
            str(args.polling_bundle),
            "--results-release",
            args.results_release,
            "--polling-release",
            args.polling_release,
            "--output",
            str(args.output),
        ],
        dry_run=args.dry_run,
    )
    print("\nBackend refresh complete." if not args.dry_run else "\nDry run complete.")


if __name__ == "__main__":
    main()
