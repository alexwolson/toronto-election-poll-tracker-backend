from __future__ import annotations

import hashlib
import json
from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import Polygon

from backend.release_inputs import hydrate_release_inputs, load_release_input_paths


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


HISTORICAL_TABLES = (
    "source_documents",
    "poll_sample_documents",
    "poll_samples",
    "poll_readings",
    "poll_responses",
    "reading_classification",
)


def _write_historical_tables(polling: Path) -> None:
    for table in HISTORICAL_TABLES:
        (polling / f"historical_mayoral_{table}.csv").write_text("id\n", encoding="utf-8")


def test_hydration_is_isolated_and_returns_explicit_model_paths(tmp_path: Path) -> None:
    project = tmp_path / "backend"
    raw = project / "data" / "raw"
    raw.mkdir(parents=True)
    sentinel = raw / "sentinel.csv"
    sentinel.write_text("tracked fixture\n", encoding="utf-8")

    results = tmp_path / "results"
    polling = tmp_path / "polling"
    results.mkdir()
    polling.mkdir()
    (results / "election_results.csv").write_text("result_status\nfinal\n", encoding="utf-8")
    (results / "electoral_districts.csv").write_text(
        "district_id,district_display_name\ndst_1,Ward 1 — Etobicoke North\n",
        encoding="utf-8",
    )
    gpd.GeoDataFrame(
        {"district_id": ["dst_1"]},
        geometry=[Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])],
        crs="EPSG:4326",
    ).to_parquet(results / "electoral_districts.parquet")
    _write_json(results / "trustee_races.json", {"schema_version": 1, "boards": []})
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
    (polling / "poll_readings.csv").write_text(
        "poll_reading_id,source_contest_id\nreading-1,contest-1\n", encoding="utf-8"
    )
    (polling / "poll_responses.csv").write_text(
        "poll_reading_id,response_option_id,person_id,source_candidate_id,candidate_name\n"
        "reading-1,chow,person-chow,chow,Olivia Chow\n",
        encoding="utf-8",
    )

    _write_historical_tables(polling)

    paths, _ = hydrate_release_inputs(project, results, polling, results_release="results-test")

    assert sentinel.read_text(encoding="utf-8") == "tracked fixture\n"
    assert paths == load_release_input_paths(project / "data/upstream/input_manifest.json")
    assert paths.election_results == project / "data/upstream/results/election_results.csv"
    assert paths.electoral_districts == project / "data/upstream/results/electoral_districts.csv"
    assert paths.electoral_districts_parquet == (
        project / "data/upstream/results/electoral_districts.parquet"
    )
    assert paths.trustee_races == project / "data/upstream/results/trustee_races.json"
    assert paths.model_polls == project / "data/upstream/model/polls"
    responses = (paths.model_polls / "poll_responses.csv").read_text(encoding="utf-8")
    assert "candidate_id" in responses.splitlines()[0]
    assert "person-chow" in responses

    paths.trustee_races.unlink()
    with pytest.raises(FileNotFoundError):
        load_release_input_paths(project / "data/upstream/input_manifest.json")


@pytest.mark.parametrize("table", HISTORICAL_TABLES)
def test_hydration_refuses_a_polling_release_without_the_historical_corpus(
    tmp_path: Path, table: str
) -> None:
    # The historical corpus is read from the pinned Polling release (ADR 0060); a
    # release that lacks any of its tables fails closed (ADR 0032).
    project = tmp_path / "backend"
    project.mkdir()
    results = tmp_path / "results"
    polling = tmp_path / "polling"
    results.mkdir()
    polling.mkdir()
    _write_json(
        results / "release_manifest.json",
        {"repository": "alexwolson/toronto-election-results", "source_commit": "c"},
    )
    sha = hashlib.sha256((results / "release_manifest.json").read_bytes()).hexdigest()
    _write_json(
        polling / "release_manifest.json",
        {
            "repository": "alexwolson/toronto-election-poll-tracker-data",
            "dependencies": {
                "results": {
                    "repository": "alexwolson/toronto-election-results",
                    "release": "results-test",
                    "source_commit": "c",
                    "manifest_sha256": sha,
                }
            },
        },
    )
    _write_historical_tables(polling)
    (polling / f"historical_mayoral_{table}.csv").unlink()
    with pytest.raises(ValueError, match="historical"):
        hydrate_release_inputs(project, results, polling, results_release="results-test")
    assert not (project / "data" / "upstream").exists()
