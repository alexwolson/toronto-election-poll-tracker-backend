"""2014->2018 electorate crosswalk (ADR 0002): raking + area-weighted reallocation."""

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import box

from defeatability_index.crosswalk import (
    area_weighted_reallocate,
    build_2018_baseline,
    rake_electorate,
)
from defeatability_index.paths import results_dir

# 2014 citywide eligible electors, from the source dataset's own ward-level total.
CITYWIDE_2014 = 1_824_770


def test_rake_conserves_each_ward_true_total():
    """Scaling polygonized subs up to the ward's true total (incl. poly-less special
    polls) must make each ward's raked subs sum to that true total exactly."""
    subs = pd.DataFrame(
        {
            "ward_number": [1, 1, 2],
            "subdivision_id": [1, 2, 1],
            "electors": [100, 100, 300],
        }
    )
    ward_totals = pd.Series({1: 250, 2: 300})  # ward 1 has 50 electors on poly-less polls

    raked = rake_electorate(subs, ward_totals, electors_col="electors")

    by_ward = raked.groupby("ward_number")["raked_electors"].sum()
    assert by_ward.loc[1] == pytest.approx(250)
    assert by_ward.loc[2] == pytest.approx(300)
    # ward 1's two equal subs each carry half the scaled-up total.
    assert raked.loc[raked["ward_number"] == 1, "raked_electors"].tolist() == [125, 125]


def _square(x0, y0, x1, y1):
    return box(x0, y0, x1, y1)


def test_area_weighted_reallocate_splits_by_overlap_and_conserves():
    """A source polygon fully inside one target gives it everything; a source split
    across two targets splits its electors by overlap area; totals are conserved."""
    source = gpd.GeoDataFrame(
        {
            "src_id": ["A", "B"],
            "electors": [100.0, 200.0],
            "geometry": [_square(0, 0, 1, 1), _square(1, 0, 2, 1)],
        },
        crs="EPSG:32617",
    )
    target = gpd.GeoDataFrame(
        {
            "ward": [10, 20],
            "geometry": [_square(0, 0, 1.5, 1), _square(1.5, 0, 2, 1)],
        },
        crs="EPSG:32617",
    )

    baseline = area_weighted_reallocate(
        source, target, value_col="electors", src_id_col="src_id", target_id_col="ward"
    )

    # A (100) all in ward 10; B (200) split 50/50 -> ward 10 gets 200, ward 20 gets 100.
    assert baseline.loc[10] == pytest.approx(200.0)
    assert baseline.loc[20] == pytest.approx(100.0)
    assert baseline.sum() == pytest.approx(300.0)


@pytest.mark.skipif(
    not (results_dir() / "data" / "out" / "subdivision_boundaries.parquet").exists(),
    reason="source election-results dataset not available",
)
def test_build_2018_baseline_conserves_citywide_electorate():
    """End-to-end on real data: the 2014 electorate reprojected onto 2018 wards must
    total the 2014 citywide electorate (raking removes the ~8% poly-less undercount),
    and land on all 25 wards."""
    baseline = build_2018_baseline(results_dir())

    assert set(baseline["ward_number"]) == set(range(1, 26))
    assert baseline["baseline_2014_electors"].sum() == pytest.approx(CITYWIDE_2014, rel=1e-6)
