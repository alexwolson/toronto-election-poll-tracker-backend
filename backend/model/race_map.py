"""Turn canonical current district geometry into presentation-ready SVG maps.

Results owns boundaries. This module performs the one spatial transformation used
by public race feeds so the frontend only needs to render paths and factual cards.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import geopandas as gpd
import shapely
from shapely.affinity import affine_transform
from shapely.geometry import MultiPolygon, Polygon
from shapely.geometry.polygon import orient
from shapely.ops import polylabel

VIEW_WIDTH = 1000
VIEW_HEIGHT = 720
VIEW_MARGIN = 24
PROJECTED_CRS = "EPSG:26917"
SIMPLIFICATION_TOLERANCE_METRES = 35.0
MAX_MAP_BYTES = 250_000


def _ward_id(value: object) -> str:
    return str(value or "").strip().removeprefix("ward-")


def _number(value: float) -> str:
    if not math.isfinite(value):
        raise ValueError("race map contains a non-finite coordinate")
    return f"{value:.2f}"


def _ring_path(coordinates) -> str:
    points = list(coordinates)
    if len(points) < 4:
        raise ValueError("race map contains an invalid polygon ring")
    return "M" + " L".join(f"{_number(x)} {_number(y)}" for x, y in points) + " Z"


def _polygon_path(polygon: Polygon) -> str:
    normalized = orient(polygon, sign=1.0)
    rings = [_ring_path(normalized.exterior.coords)]
    rings.extend(_ring_path(interior.coords) for interior in normalized.interiors)
    return " ".join(rings)


def _geometry_path(geometry: Polygon | MultiPolygon) -> str:
    if isinstance(geometry, Polygon):
        return _polygon_path(geometry)
    if not isinstance(geometry, MultiPolygon):
        raise TypeError("race maps support only Polygon and MultiPolygon geometry")
    polygons = sorted(
        geometry.geoms,
        key=lambda polygon: (-polygon.area, *polygon.bounds),
    )
    return " ".join(_polygon_path(polygon) for polygon in polygons)


def _label_polygon(geometry: Polygon | MultiPolygon) -> Polygon:
    if isinstance(geometry, Polygon):
        return geometry
    return max(geometry.geoms, key=lambda polygon: polygon.area)


def _normalized_geometries(frame: gpd.GeoDataFrame) -> list[Polygon | MultiPolygon]:
    projected = frame.to_crs(PROJECTED_CRS)
    # Very small rings can become invalid during reprojection even when the
    # canonical WGS84 polygon is valid. Repair in projected space before the
    # shared-boundary simplifier sees it.
    geometries = list(
        shapely.make_valid(list(projected.geometry), method="structure", keep_collapsed=False)
    )
    if any(not isinstance(geometry, Polygon | MultiPolygon) for geometry in geometries):
        raise ValueError("race map reprojection produced unsupported geometry")
    simplified = list(
        shapely.coverage_simplify(geometries, tolerance=SIMPLIFICATION_TOLERANCE_METRES)
    )
    if any(
        geometry.is_empty
        or not geometry.is_valid
        or not isinstance(geometry, Polygon | MultiPolygon)
        for geometry in simplified
    ):
        raise ValueError("race map simplification produced invalid geometry")

    min_x = min(geometry.bounds[0] for geometry in simplified)
    min_y = min(geometry.bounds[1] for geometry in simplified)
    max_x = max(geometry.bounds[2] for geometry in simplified)
    max_y = max(geometry.bounds[3] for geometry in simplified)
    width = max_x - min_x
    height = max_y - min_y
    if not all(math.isfinite(value) for value in (min_x, min_y, max_x, max_y)):
        raise ValueError("race map bounds are not finite")
    if width <= 0 or height <= 0:
        raise ValueError("race map bounds have no area")

    usable_width = VIEW_WIDTH - 2 * VIEW_MARGIN
    usable_height = VIEW_HEIGHT - 2 * VIEW_MARGIN
    scale = min(usable_width / width, usable_height / height)
    x_offset = VIEW_MARGIN + (usable_width - width * scale) / 2 - min_x * scale
    y_offset = VIEW_MARGIN + (usable_height - height * scale) / 2 + max_y * scale
    return [
        affine_transform(geometry, [scale, 0, 0, -scale, x_offset, y_offset])
        for geometry in simplified
    ]


def build_race_map(
    geometry_path: str | Path,
    *,
    represented_body: str,
    boundary_regime: str,
    ordered_ward_ids: list[str],
    feature_facts: dict[str, dict],
    aria_label: str,
    palette: str,
    legend: list[dict],
    supported_signal_keys: set[str],
) -> dict | None:
    """Build one complete deterministic map, or omit it when geometry is absent.

    A missing complete layer is an allowed release state. Once any geometry is
    present, however, partial or mismatched inventory is a build error.
    """

    path = Path(geometry_path)
    if not path.is_file():
        return None
    frame = gpd.read_parquet(path)
    selected = frame[
        (frame["represented_body"] == represented_body)
        & (frame["boundary_regime"] == boundary_regime)
    ].copy()
    if selected.empty:
        return None
    selected["_ward_id"] = selected["official_district_id"].map(_ward_id)
    # The Council regime also contains a convenient citywide aggregate polygon;
    # it is not an electoral feature on the ward map.
    selected = selected[selected["_ward_id"] != "city"].copy()
    expected = [str(ward_id) for ward_id in ordered_ward_ids]
    if len(expected) != len(set(expected)) or set(feature_facts) != set(expected):
        raise ValueError("race map expected inventory is invalid")
    if selected["_ward_id"].duplicated().any() or set(selected["_ward_id"]) != set(expected):
        raise ValueError("race map geometry does not match the expected ward inventory")
    missing = selected.geometry.isna() | selected.geometry.is_empty
    if missing.all():
        return None
    if missing.any() or (selected.get("geometry_status") != "available").any():
        raise ValueError("race map geometry is only partially available")

    selected = selected.set_index("_ward_id").loc[expected].reset_index()
    normalized = _normalized_geometries(selected)
    features: list[dict] = []
    for row, geometry in zip(selected.to_dict("records"), normalized, strict=True):
        ward_id = row["_ward_id"]
        facts = feature_facts[ward_id]
        signal_key = facts.get("signal_key")
        if signal_key not in supported_signal_keys:
            raise ValueError(f"unsupported race map signal: {signal_key}")
        signal_value = facts.get("signal_value")
        if signal_value is not None and (
            not isinstance(signal_value, int | float) or not math.isfinite(float(signal_value))
        ):
            raise ValueError("race map signal value must be finite or null")
        panel = dict(facts.get("panel") or {})
        panel.setdefault("geography", row.get("geographic_name") or "")
        required_panel = {"heading", "geography", "status", "candidate_count", "href"}
        if any(panel.get(key) in (None, "") for key in required_panel):
            raise ValueError(f"race map panel is incomplete for ward {ward_id}")
        anchor = polylabel(_label_polygon(geometry), tolerance=0.25)
        accessible_name = facts.get("accessible_name") or row.get("district_display_name")
        if not accessible_name:
            raise ValueError(f"race map feature {ward_id} has no accessible name")
        features.append(
            {
                "ward_id": ward_id,
                "accessible_name": accessible_name,
                "path": _geometry_path(geometry),
                "label": {
                    "x": float(_number(anchor.x)),
                    "y": float(_number(anchor.y)),
                    "text": facts.get("label_text") or ward_id,
                    "leader_line": None,
                },
                "signal_key": signal_key,
                "signal_value": signal_value,
                "panel": panel,
            }
        )

    payload = {
        "view_box": f"0 0 {VIEW_WIDTH} {VIEW_HEIGHT}",
        "aria_label": aria_label,
        "palette": palette,
        "legend": legend,
        "features": features,
    }
    if len(json.dumps(payload, separators=(",", ":")).encode()) > MAX_MAP_BYTES:
        raise ValueError("race map exceeds the 250 KB payload budget")
    return payload
