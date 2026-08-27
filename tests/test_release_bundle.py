from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from backend.release_bundle import build_backend_release_bundle


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def _upstream_bundles(tmp_path: Path) -> tuple[Path, Path]:
    results = tmp_path / "results"
    polling = tmp_path / "polling"
    results.mkdir()
    polling.mkdir()
    results_manifest = {
        "repository": "alexwolson/toronto-election-results",
        "source_commit": "results-commit",
    }
    _write_json(results / "release_manifest.json", results_manifest)
    results_sha = hashlib.sha256((results / "release_manifest.json").read_bytes()).hexdigest()
    _write_json(
        polling / "release_manifest.json",
        {
            "repository": "alexwolson/toronto-election-poll-tracker-data",
            "source_commit": "polling-commit",
            "dependencies": {
                "results": {
                    "repository": "alexwolson/toronto-election-results",
                    "release": "results-test",
                    "source_commit": "results-commit",
                    "manifest_sha256": results_sha,
                }
            },
        },
    )
    return results, polling


def test_backend_bundle_requires_and_indexes_trustee_cards(tmp_path: Path) -> None:
    processed = tmp_path / "processed"
    processed.mkdir()
    for filename in (
        "mayoral_forecast.json",
        "council_race_cards.json",
        "trustee_race_cards.json",
    ):
        _write_json(processed / filename, {"feed": filename})
    results, polling = _upstream_bundles(tmp_path)
    output = tmp_path / "dist"

    build_backend_release_bundle(
        processed,
        results,
        polling,
        output,
        results_release="results-test",
        polling_release="polling-test",
        source_commit="backend-commit",
        dirty=False,
        generated_at="2026-08-27T12:00:00Z",
    )

    manifest = json.loads((output / "release_manifest.json").read_text(encoding="utf-8"))
    assert manifest["feeds"]["trustee_race_cards"] == "trustee_race_cards.json"
    assert (output / "trustee_race_cards.json").is_file()
    trustee_asset = next(
        asset for asset in manifest["assets"] if asset["filename"] == "trustee_race_cards.json"
    )
    assert (
        trustee_asset["sha256"]
        == hashlib.sha256((output / "trustee_race_cards.json").read_bytes()).hexdigest()
    )


def test_backend_bundle_rejects_missing_trustee_cards(tmp_path: Path) -> None:
    processed = tmp_path / "processed"
    processed.mkdir()
    _write_json(processed / "mayoral_forecast.json", {})
    _write_json(processed / "council_race_cards.json", {})
    results, polling = _upstream_bundles(tmp_path)

    with pytest.raises(FileNotFoundError, match="trustee_race_cards.json"):
        build_backend_release_bundle(
            processed,
            results,
            polling,
            tmp_path / "dist",
            results_release="results-test",
            polling_release="polling-test",
            source_commit="backend-commit",
            dirty=False,
        )
