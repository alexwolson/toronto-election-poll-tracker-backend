from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import MultiPolygon, Polygon

from backend.model.race_map import build_race_map


def _write_geometry(path: Path, *, reverse: bool = False, missing: str | None = None) -> None:
    first = Polygon(
        [(0, 0), (2, 0), (2, 2), (0, 2)],
        holes=[[(0.5, 0.5), (1, 0.5), (1, 1), (0.5, 1)]],
    )
    second = MultiPolygon(
        [
            Polygon([(2, 0), (4, 0), (4, 2), (2, 2)]),
            Polygon([(4.2, 0), (4.4, 0), (4.4, 0.2), (4.2, 0.2)]),
        ]
    )
    rows = [
        {
            "represented_body": "example_board",
            "boundary_regime": "example-2026",
            "official_district_id": "1",
            "district_display_name": "Ward 1 — West",
            "geographic_name": "West",
            "geometry_status": "available",
            "geometry": None if missing == "1" else first,
        },
        {
            "represented_body": "example_board",
            "boundary_regime": "example-2026",
            "official_district_id": "2",
            "district_display_name": "Ward 2 — East",
            "geographic_name": "East",
            "geometry_status": "available",
            "geometry": None if missing == "2" else second,
        },
    ]
    if reverse:
        rows.reverse()
    gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:26917").to_parquet(path)


def _facts() -> dict[str, dict]:
    return {
        ward: {
            "accessible_name": f"Ward {ward}",
            "signal_key": "open" if ward == "1" else "quiet",
            "signal_value": None,
            "panel": {
                "heading": f"Ward {ward}",
                "status": "Open race" if ward == "1" else "One incumbent",
                "candidate_count": int(ward) + 1,
                "href": f"/example/{ward}",
            },
        }
        for ward in ("1", "2")
    }


def _build(path: Path) -> dict | None:
    return build_race_map(
        path,
        represented_body="example_board",
        boundary_regime="example-2026",
        ordered_ward_ids=["2", "1"],
        feature_facts=_facts(),
        aria_label="Example wards",
        palette="example",
        legend=[{"key": "open", "label": "Open"}, {"key": "quiet", "label": "Quiet"}],
        supported_signal_keys={"open", "quiet"},
    )


def test_builds_deterministic_polygon_and_multipolygon_svg(tmp_path: Path) -> None:
    first_path = tmp_path / "districts.parquet"
    second_path = tmp_path / "shuffled.parquet"
    _write_geometry(first_path)
    _write_geometry(second_path, reverse=True)

    first = _build(first_path)
    second = _build(second_path)

    assert first == second
    assert first is not None
    assert first["view_box"] == "0 0 1000 720"
    assert [feature["ward_id"] for feature in first["features"]] == ["2", "1"]
    assert first["features"][0]["path"].count("M") == 2  # mainland + island
    assert first["features"][1]["path"].count("M") == 1  # source gap suppressed
    assert all(
        0 <= feature["label"][axis] <= (1000 if axis == "x" else 720)
        for feature in first["features"]
        for axis in ("x", "y")
    )
    assert len(json.dumps(first, separators=(",", ":")).encode()) < 250_000


def test_absent_layer_is_omitted_but_partial_layer_fails(tmp_path: Path) -> None:
    assert _build(tmp_path / "missing.parquet") is None
    path = tmp_path / "partial.parquet"
    _write_geometry(path, missing="2")
    with pytest.raises(ValueError, match="partially available"):
        _build(path)


def test_mismatched_or_duplicate_inventory_fails(tmp_path: Path) -> None:
    path = tmp_path / "districts.parquet"
    _write_geometry(path)
    with pytest.raises(ValueError, match="expected inventory"):
        build_race_map(
            path,
            represented_body="example_board",
            boundary_regime="example-2026",
            ordered_ward_ids=["1", "1"],
            feature_facts={"1": _facts()["1"]},
            aria_label="Example",
            palette="example",
            legend=[],
            supported_signal_keys={"open"},
        )
