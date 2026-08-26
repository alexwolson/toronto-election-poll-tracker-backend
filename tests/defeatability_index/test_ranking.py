"""Ranking core: faithful reproduction of Matt Elliott's rank-sum method (ADR 0001)."""

from pathlib import Path

import pandas as pd

from defeatability_index.ranking import compute_index

# Matt Elliott's own City Hall Watcher export, copied verbatim as ground truth.
# Provenance: toronto-election-poll-tracker-data/data/raw/defeatability/data-qT4Kx.csv
FIXTURE = Path(__file__).parent / "fixtures" / "matt_cdi_2026.csv"


def _pct(value) -> float:
    return float(str(value).rstrip("%"))


def test_reproduces_matt_stored_defeatability_scores():
    """The faithfulness lock: feeding Matt's own component values through our
    ranking must reproduce his stored Rank columns and Defeatability Score exactly
    (Matlow 3, Fletcher 7, Saxe 68, Malik 70). His pool is 25 wards + Mayor (N=26)."""
    raw = pd.read_csv(FIXTURE)
    pool = pd.DataFrame(
        {
            "vote_share": raw["Vote Share"].map(_pct),
            "elector_share": raw["Elector Share"].map(_pct),
            "new_voter_margin": raw["New Voter Margin"].astype(int),
        }
    )

    out = compute_index(pool)

    assert (out["rank_vote_share"] == raw["Rank: Vote Share"]).all()
    assert (out["rank_elector_share"] == raw["Rank: Elector Share"]).all()
    assert (out["rank_new_voter_margin"] == raw["Rank: New Voter Margin"]).all()
    assert (out["rank_sum"] == raw["Defeatability Score"]).all()
    assert out["pool_size"].eq(26).all()


def test_rank_orientation_rank_one_is_safest():
    """Highest vote/elector share and lowest new-voter margin are the safest -> rank 1."""
    pool = pd.DataFrame(
        {
            "label": ["safe", "mid", "exposed"],
            "vote_share": [0.80, 0.50, 0.20],
            "elector_share": [0.30, 0.15, 0.05],
            "new_voter_margin": [-100, 0, 100],
        }
    )

    out = compute_index(pool).set_index("label")

    assert out.loc["safe", "rank_vote_share"] == 1
    assert out.loc["safe", "rank_elector_share"] == 1
    assert out.loc["safe", "rank_new_voter_margin"] == 1
    assert out.loc["exposed", "rank_vote_share"] == 3
    assert out.loc["exposed", "rank_new_voter_margin"] == 3


def test_defeatability_100_endpoints_and_range():
    """0 = safest on every component, 100 = most defeatable on every component."""
    pool = pd.DataFrame(
        {
            "label": ["safe", "mid", "exposed"],
            "vote_share": [0.80, 0.50, 0.20],
            "elector_share": [0.30, 0.15, 0.05],
            "new_voter_margin": [-100, 0, 100],
        }
    )

    out = compute_index(pool).set_index("label")

    assert out["defeatability_100"].between(0, 100).all()
    assert out.loc["safe", "defeatability_100"] == 0
    assert out.loc["exposed", "defeatability_100"] == 100
    assert out.loc["mid", "defeatability_100"] == 50
