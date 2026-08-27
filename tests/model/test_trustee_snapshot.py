from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import geopandas as gpd
from shapely.geometry import box

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests/fixtures/trustee_races.json"


def test_snapshot_command_reads_only_the_hydrated_trustee_input(tmp_path: Path) -> None:
    results = tmp_path / "results"
    polling = tmp_path / "polling"
    model_polls = tmp_path / "model/polls"
    results.mkdir()
    polling.mkdir()
    model_polls.mkdir(parents=True)
    (results / "election_results.csv").write_text("result_status\n", encoding="utf-8")
    (results / "electoral_districts.csv").write_text(
        "district_id,district_display_name\n", encoding="utf-8"
    )
    gpd.GeoDataFrame(
        {
            "represented_body": ["unrelated"],
            "boundary_regime": ["unrelated"],
            "official_district_id": ["1"],
            "geometry_status": ["available"],
        },
        geometry=[box(0, 0, 1, 1)],
        crs="EPSG:26917",
    ).to_parquet(results / "electoral_districts.parquet")
    (results / "trustee_races.json").write_bytes(FIXTURE.read_bytes())
    manifest = tmp_path / "input_manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "paths": {
                    "results_dir": "results",
                    "polling_dir": "polling",
                    "election_results": "results/election_results.csv",
                    "electoral_districts": "results/electoral_districts.csv",
                    "electoral_districts_parquet": "results/electoral_districts.parquet",
                    "trustee_races": "results/trustee_races.json",
                    "model_polls": "model/polls",
                },
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / "generated/trustee_race_cards.json"

    subprocess.run(
        [
            sys.executable,
            "scripts/build_trustee_snapshot.py",
            "--input-manifest",
            str(manifest),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        check=True,
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 3
    assert [board["board_id"] for board in payload["boards"]] == [
        "tdsb",
        "tcdsb",
        "viamonde",
        "monavenir",
    ]
    assert sum(len(board["wards"]) for board in payload["boards"]) == 29
    assert [
        (board["board_id"], ward["ward_id"])
        for board in payload["boards"]
        for ward in board["wards"]
        if ward["race_context"]["signal"] is not None
    ] == [("tcdsb", "4"), ("tcdsb", "5")]
