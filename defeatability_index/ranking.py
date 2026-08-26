"""Faithful reproduction of Matt Elliott's Council Defeatability Index rank-sum.

Each of the three components is ranked across the pool with rank 1 = safest, and the
score is the sum of the three ranks (higher = more defeatable). See ADR 0001. A pool
is one election year's scoreable incumbents; the caller ranks per year.
"""

import pandas as pd

RANK_COLUMNS = ("rank_vote_share", "rank_elector_share", "rank_new_voter_margin")


def compute_index(
    pool: pd.DataFrame,
    *,
    vote_share: str = "vote_share",
    elector_share: str = "elector_share",
    new_voter_margin: str = "new_voter_margin",
) -> pd.DataFrame:
    """Add rank, ``rank_sum`` and ``defeatability_100`` columns to a single-year pool.

    Orientation (rank 1 = safest): vote share and elector share rank descending
    (highest share is safest); new-voter margin ranks ascending (most negative is
    safest). Ties take the lower rank (competition ranking), matching spreadsheet RANK.

    ``defeatability_100`` is the mean of the three per-component percentiles
    ``(rank - 1) / (N - 1)`` scaled to 0-100, so it is comparable across years with
    different pool sizes (0 = safest, 100 = most defeatable).
    """
    out = pool.copy()
    n = len(out)

    out["rank_vote_share"] = out[vote_share].rank(ascending=False, method="min").astype(int)
    out["rank_elector_share"] = out[elector_share].rank(ascending=False, method="min").astype(int)
    out["rank_new_voter_margin"] = (
        out[new_voter_margin].rank(ascending=True, method="min").astype(int)
    )

    out["rank_sum"] = out.loc[:, list(RANK_COLUMNS)].sum(axis=1)
    out["pool_size"] = n

    if n > 1:
        percentiles = sum((out[col] - 1) / (n - 1) for col in RANK_COLUMNS) / len(RANK_COLUMNS)
        out["defeatability_100"] = percentiles * 100.0
    else:
        out["defeatability_100"] = 0.0

    return out
