"""Assembly: prior-win selection, contest margins, and end-to-end index build."""

import hashlib

import numpy as np
import pandas as pd
import pytest

from defeatability_index.build import (
    SCOREABLE_YEARS,
    build_index,
    contest_margins,
    latest_prior_win,
)
from defeatability_index.paths import results_dir


def test_contest_margins_winner_minus_runner_up():
    """Margin is winner (rank 1) minus runner-up (rank 2); acclaimed contests (no
    runner-up) are NaN."""
    res = pd.DataFrame(
        {
            "office": ["councillor", "councillor", "councillor", "councillor"],
            "contest_id": ["x", "x", "x", "y"],
            "vote_rank": [1, 2, 3, 1],
            "votes": [100, 60, 40, 50],
        }
    )

    margins = contest_margins(res)

    assert margins["x"] == 40
    assert pd.isna(margins["y"])


def test_latest_prior_win_picks_most_recent_before_year():
    """The prior win is the most recent elected row strictly before the scored year,
    spanning general and by-election wins alike."""
    wins = pd.DataFrame(
        {
            "candidate_id": ["c1", "c1", "c2"],
            "election_year": [2010, 2014, 2014],
            "votes": [10, 20, 30],
        }
    )

    assert latest_prior_win(wins, "c1", 2018).votes == 20  # 2014 beats 2010
    assert latest_prior_win(wins, "c1", 2012).votes == 10  # only 2010 qualifies
    assert latest_prior_win(wins, "c2", 2014) is None  # 2014 is not < 2014


@pytest.mark.skipif(
    not (results_dir() / "data" / "out" / "election_results.csv").exists(),
    reason="source election-results dataset not available",
)
def test_build_index_accepts_normalized_v2_results():
    df = build_index(results_dir())

    # Every scored year present; only in-scope years.
    assert set(df["election_year"]) == set(SCOREABLE_YEARS)

    # Ranked rows are exactly the runners with a full three-component vector.
    ranked = df[df["rank_sum"].notna()]
    assert (ranked["ran_for_reelection"]).all()
    assert ranked[["vote_share", "elector_share", "new_voter_margin"]].notna().all().all()
    assert ranked["defeatability_100"].between(0, 100).all()

    # pool_size per year equals the number of ranked rows that year.
    for year, grp in ranked.groupby("election_year"):
        assert (grp["pool_size"] == len(grp)).all()

    # Retirees are kept, flagged, and never ranked (no silent drop).
    retirees = df[~df["ran_for_reelection"] & df["candidate_id"].notna()]
    assert retirees["rank_sum"].isna().all()

    # 2018 is the only cross-era year; every 2018 row is flagged.
    assert df.loc[df["election_year"] == 2018, "cross_era"].all()
    assert not df.loc[df["election_year"] != 2018, "cross_era"].any()

    # no_prior_result rows carry no components.
    npr = df[df["no_prior_result"]]
    assert npr["vote_share"].isna().all()

    # The roster is the official pre-election tenure snapshot: 44 councillors before
    # each 44-ward election and 25 before 2022.
    assert df.groupby("election_year").size().to_dict() == {
        2006: 44,
        2010: 44,
        2014: 44,
        2018: 44,
        2022: 25,
    }
    assert ranked.groupby("election_year").size().to_dict() == {
        2006: 34,
        2010: 34,
        2014: 37,
        2018: 31,
        2022: 17,
    }

    # Outside the corrected 2018 Shelley Carroll roster classification, the
    # normalized v2 migration reproduces every committed faithful CDI component
    # and rank. The digest is over sorted, rounded numeric values—not implementation
    # details or unstable identity labels.
    faithful_columns = [
        "election_year",
        "prior_win_year",
        "vote_share",
        "elector_share",
        "prior_winning_margin",
        "new_electors",
        "new_voter_margin",
        "rank_vote_share",
        "rank_elector_share",
        "rank_new_voter_margin",
        "rank_sum",
        "pool_size",
        "defeatability_100",
    ]
    stable = (
        ranked[ranked.election_year != 2018][faithful_columns]
        .astype(float)
        .sort_values(faithful_columns)
        .to_numpy()
    )
    digest = hashlib.sha256(np.round(stable, 9).astype("<f8").tobytes()).hexdigest()
    assert digest == "9b0a4806d1a7af66b66525bbd6756b585769a86e0728554154278b7bdcc6985d"

    # ran_for_reelection is complete: every officially identified incumbent who
    # appears in that year's general is flagged — even the unscoreable ones.
    res = pd.read_csv(results_dir() / "data" / "out" / "election_results.csv")
    for year in SCOREABLE_YEARS:
        reported_runners = set(
            res[
                (res.election_year == year)
                & (res.office_type == "councillor")
                & (res.election_type == "general")
                & (res.incumbent == True)
            ].person_id.dropna()
        )
        built_runners = set(
            df[(df.election_year == year) & df.ran_for_reelection].candidate_id.dropna()
        )
        assert built_runners == reported_runners
