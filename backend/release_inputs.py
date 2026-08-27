"""Validate and hydrate the exact Results and Polling releases used by a model run."""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

RESULTS_REPOSITORY = "alexwolson/toronto-election-results"
POLLING_REPOSITORY = "alexwolson/toronto-election-poll-tracker-data"
INPUT_MANIFEST_SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class ReleaseInputPaths:
    """Validated, explicit paths used by one backend model run."""

    manifest: Path
    results_dir: Path
    polling_dir: Path
    election_results: Path
    electoral_districts: Path
    trustee_races: Path
    model_polls: Path


def load_release_input_paths(path: str | Path) -> ReleaseInputPaths:
    """Load and validate a hydrated input manifest without path discovery."""

    manifest_path = Path(path).resolve()
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != INPUT_MANIFEST_SCHEMA_VERSION:
        raise ValueError("unsupported backend input manifest schema")
    root = manifest_path.parent

    def resolve(key: str) -> Path:
        candidate = (root / payload["paths"][key]).resolve()
        if not candidate.is_relative_to(root):
            raise ValueError(f"backend input path escapes the hydrated root: {key}")
        if not candidate.exists():
            raise FileNotFoundError(candidate)
        return candidate

    return ReleaseInputPaths(
        manifest=manifest_path,
        results_dir=resolve("results_dir"),
        polling_dir=resolve("polling_dir"),
        election_results=resolve("election_results"),
        electoral_districts=resolve("electoral_districts"),
        trustee_races=resolve("trustee_races"),
        model_polls=resolve("model_polls"),
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _manifest(bundle: Path, repository: str) -> dict:
    path = bundle / "release_manifest.json"
    if not path.is_file():
        raise FileNotFoundError(f"release has no manifest: {bundle}")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("repository") != repository:
        raise ValueError(f"release manifest expected {repository}")
    return manifest


def validate_release_chain(
    results_bundle: str | Path, polling_bundle: str | Path, *, results_release: str
) -> tuple[dict, dict]:
    results = Path(results_bundle)
    polling = Path(polling_bundle)
    results_manifest = _manifest(results, RESULTS_REPOSITORY)
    polling_manifest = _manifest(polling, POLLING_REPOSITORY)
    pinned = polling_manifest.get("dependencies", {}).get("results", {})
    expected = {
        "repository": RESULTS_REPOSITORY,
        "release": results_release,
        "source_commit": results_manifest.get("source_commit"),
        "manifest_sha256": sha256_file(results / "release_manifest.json"),
    }
    if pinned != expected:
        raise ValueError("Polling release does not pin the supplied Results release exactly")
    return results_manifest, polling_manifest


def _write_legacy_model_responses(source: Path, destination: Path) -> None:
    with source.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    source_columns = list(rows[0]) if rows else []
    columns = [
        column for column in source_columns if column not in {"person_id", "source_candidate_id"}
    ]
    columns.insert(columns.index("candidate_name"), "candidate_id")
    for row in rows:
        row["candidate_id"] = row["person_id"] or row["source_candidate_id"]
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _write_model_readings(source: Path, destination: Path) -> None:
    with source.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    source_columns = list(rows[0]) if rows else []
    columns = [column for column in source_columns if column != "source_contest_id"]
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def hydrate_release_inputs(
    root: str | Path,
    results_bundle: str | Path,
    polling_bundle: str | Path,
    *,
    results_release: str,
) -> tuple[ReleaseInputPaths, tuple[dict, dict]]:
    """Atomically vendor validated release assets into the backend workspace."""

    project = Path(root)
    results = Path(results_bundle)
    polling = Path(polling_bundle)
    manifests = validate_release_chain(results, polling, results_release=results_release)
    upstream = project / "data" / "upstream"
    upstream.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".upstream-stage-", dir=upstream.parent) as tmp:
        stage = Path(tmp)
        shutil.copytree(results, stage / "results")
        shutil.copytree(polling, stage / "polling")
        model_polls = stage / "model" / "polls"
        model_polls.mkdir(parents=True)
        for name in (
            "source_documents.csv",
            "poll_sample_documents.csv",
            "poll_samples.csv",
            "historical_mayoral_polls.csv",
            "historical_mayoral_outcomes.csv",
            "legacy_historical_poll_crosswalk.csv",
        ):
            if (polling / name).is_file():
                shutil.copy2(polling / name, model_polls / name)
        _write_model_readings(polling / "poll_readings.csv", model_polls / "poll_readings.csv")
        _write_legacy_model_responses(
            polling / "poll_responses.csv", model_polls / "poll_responses.csv"
        )
        (stage / "input_manifest.json").write_text(
            json.dumps(
                {
                    "schema_version": INPUT_MANIFEST_SCHEMA_VERSION,
                    "paths": {
                        "results_dir": "results",
                        "polling_dir": "polling",
                        "election_results": "results/election_results.csv",
                        "electoral_districts": "results/electoral_districts.csv",
                        "trustee_races": "results/trustee_races.json",
                        "model_polls": "model/polls",
                    },
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        backup = upstream.with_name(".upstream-backup")
        if backup.exists():
            shutil.rmtree(backup)
        if upstream.exists():
            upstream.replace(backup)
        try:
            shutil.copytree(stage, upstream)
        except Exception:
            if backup.exists() and not upstream.exists():
                backup.replace(upstream)
            raise
        finally:
            if backup.exists():
                shutil.rmtree(backup)

    paths = load_release_input_paths(upstream / "input_manifest.json")
    return paths, manifests
