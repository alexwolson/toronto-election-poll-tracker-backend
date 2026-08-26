"""2014 -> 2018 electorate crosswalk (ADR 0002).

Toronto went from 44 wards (2014) to 25 (2018), so a 2018 incumbent's growth term
needs a like-for-like 2014 baseline on 2018 boundaries. We reproject 2014 ward
electorate onto 2018 wards at the subdivision (poll) level: parse per-subdivision
2014 electors, rake each ward's polygonized subs up to that ward's true total (the
~8% of electors on special/advance polls have no polygon), then area-weight each
2014 subdivision's electors into the 2018 wards it overlaps.
"""

import re
from pathlib import Path

import geopandas as gpd
import pandas as pd

METRIC_CRS = "EPSG:32617"  # UTM 17N — metres, for area-correct overlay.


def parse_2014_subdivision_electorate(xls_path: Path) -> pd.DataFrame:
    """Per-subdivision 2014 eligible electors from the raw voter-statistics workbook.

    The shipped pipeline sums the `Sub` column away; we keep it. Total ("Ward N
    Total" / "Grand Total") rows have non-numeric Ward/Sub and drop out via coercion.
    """
    raw = pd.read_excel(xls_path, sheet_name="2014 Voter Turnout")
    # Header cells carry embedded newlines ("Total Eligible\nElectors"); normalise them.
    raw.columns = [re.sub(r"\s+", " ", str(c)).strip() for c in raw.columns]

    df = pd.DataFrame(
        {
            "ward_number": pd.to_numeric(raw["Ward"], errors="coerce"),
            "subdivision_id": pd.to_numeric(raw["Sub"], errors="coerce"),
            "electors": pd.to_numeric(raw["Total Eligible Electors"], errors="coerce"),
        }
    ).dropna()

    df["ward_number"] = df["ward_number"].astype(int)
    df["subdivision_id"] = df["subdivision_id"].astype(int)
    df["electors"] = df["electors"].astype(float)
    df["area_code"] = df["ward_number"].map("{:02d}".format) + df["subdivision_id"].map(
        "{:03d}".format
    )
    return df[["ward_number", "subdivision_id", "area_code", "electors"]]


def rake_electorate(
    subs: pd.DataFrame, ward_totals: pd.Series, *, electors_col: str = "electors"
) -> pd.DataFrame:
    """Scale each ward's (polygonized) subdivisions so they sum to the ward's true total.

    ``ward_totals`` includes the poly-less special/advance polls, so the scale factor
    (> 1) redistributes those electors across the ward's real polling geography and
    keeps every ward's electorate exact before the spatial crosswalk.
    """
    subs = subs.copy()
    poly_sum = subs.groupby("ward_number")[electors_col].transform("sum")
    factor = subs["ward_number"].map(ward_totals) / poly_sum
    subs["raked_electors"] = subs[electors_col] * factor
    return subs


def area_weighted_reallocate(
    source_gdf: gpd.GeoDataFrame,
    target_gdf: gpd.GeoDataFrame,
    *,
    value_col: str,
    src_id_col: str,
    target_id_col: str,
) -> pd.Series:
    """Apportion each source polygon's ``value_col`` into the targets it overlaps,
    weighted by intersection area. Weights are normalised per source (sum to 1 over
    the intersections that exist), so each source's value is fully conserved. Both
    GeoDataFrames must already be in the same area-true (projected) CRS.

    Returns a Series indexed by ``target_id_col`` of the reallocated totals.
    """
    inter = gpd.overlay(
        source_gdf[[src_id_col, value_col, "geometry"]],
        target_gdf[[target_id_col, "geometry"]],
        how="intersection",
        keep_geom_type=True,
    )
    inter["_area"] = inter.geometry.area
    inter["_src_area"] = inter.groupby(src_id_col)["_area"].transform("sum")
    inter["_alloc"] = inter[value_col] * inter["_area"] / inter["_src_area"]
    return inter.groupby(target_id_col)["_alloc"].sum()


def build_2018_baseline(results_dir: Path) -> pd.DataFrame:
    """The 2014 electorate reprojected onto each 2018 ward (`baseline_2014_electors`)."""
    out = results_dir / "data" / "out"
    raw = results_dir / "data" / "raw" / "voter_stats" / "2014-voter-statistics.xls"

    subs = parse_2014_subdivision_electorate(raw)
    ward_totals = subs.groupby("ward_number")["electors"].sum()

    published = out / "subdivision_boundaries.parquet"
    if published.exists():
        boundaries = gpd.read_parquet(published)
    else:
        frames = []
        for year in (2014, 2018):
            path = (
                results_dir
                / "data"
                / "raw"
                / "subdivisions"
                / f"voting-subdivisions-{year}-4326.geojson"
            )
            frame = gpd.read_file(path)
            long_code = frame["AREA_LONG_CODE"].astype(str).str.replace(r"\.0$", "", regex=True)
            frame["election_year"] = year
            frame["ward_number"] = pd.to_numeric(long_code.str[:-3], errors="raise").astype(int)
            frame["area_code"] = long_code
            frames.append(frame[["election_year", "ward_number", "area_code", "geometry"]])
        boundaries = gpd.GeoDataFrame(pd.concat(frames, ignore_index=True), crs=frames[0].crs)
    polys_2014 = boundaries[boundaries["election_year"] == 2014][
        ["ward_number", "area_code", "geometry"]
    ].merge(subs[["area_code", "electors"]], on="area_code", how="inner")

    raked = rake_electorate(polys_2014, ward_totals)
    source = raked.to_crs(METRIC_CRS)

    wards_2018 = (
        boundaries[boundaries["election_year"] == 2018]
        .dissolve(by="ward_number")
        .reset_index()[["ward_number", "geometry"]]
        .to_crs(METRIC_CRS)
    )

    baseline = area_weighted_reallocate(
        source,
        wards_2018,
        value_col="raked_electors",
        src_id_col="area_code",
        target_id_col="ward_number",
    )
    return baseline.rename("baseline_2014_electors").reset_index()
