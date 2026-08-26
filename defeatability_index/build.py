"""Assemble the historical Council Defeatability Index (see SPEC.md).

Population is the last valid councillor roster before each scored election, supplied
by the normalized ``office_tenures`` artifact. Each person is joined through the
persistent Person ID to their most recent prior council win (general or by-election)
for the two vote-based components; the growth component and rank are computed only
for those who ran. 2018's growth uses the 2014->2018 electorate crosswalk (ADR 0002).
"""

from pathlib import Path

import pandas as pd

from .crosswalk import build_2018_baseline
from .paths import output_dir, results_dir
from .ranking import compute_index

SCOREABLE_YEARS = (2006, 2010, 2014, 2018, 2022)
CROSS_ERA_YEAR = 2018

OUTPUT_COLUMNS = [
    "election_year",
    "ward_system",
    "ward_number",
    "candidate_id",
    "candidate_name",
    "incumbent_source",
    "prior_win_year",
    "prior_win_type",
    "prior_n_candidates",
    "vote_share",
    "elector_share",
    "prior_winning_margin",
    "new_electors",
    "new_voter_margin",
    "n_candidates_Y",
    "rank_vote_share",
    "rank_elector_share",
    "rank_new_voter_margin",
    "rank_sum",
    "pool_size",
    "defeatability_100",
    "ran_for_reelection",
    "elected_Y",
    "new_vote_share_Y",
    "margin_Y",
    "cross_era",
    "dual_incumbent_2018",
    "by_election_incumbent",
    "no_prior_result",
]


def contest_margins(res: pd.DataFrame) -> pd.Series:
    """Winner-minus-runner-up vote margin per councillor contest (NaN if acclaimed)."""
    council = res[res["office"] == "councillor"]
    winner = council[council["vote_rank"] == 1].set_index("contest_id")["votes"]
    runner_up = council[council["vote_rank"] == 2].set_index("contest_id")["votes"]
    return winner.subtract(runner_up)


def latest_prior_win(wins: pd.DataFrame, candidate_id: str, year: int):
    """Most recent elected councillor win for ``candidate_id`` strictly before ``year``."""
    hits = wins[(wins["candidate_id"] == candidate_id) & (wins["election_year"] < year)]
    if hits.empty:
        return None
    return hits.sort_values("election_year").iloc[-1]


def _elected_council_wins(res: pd.DataFrame, margins: pd.Series) -> pd.DataFrame:
    """All elected councillor rows (general + by-election) with their winning margin."""
    wins = res[(res["office"] == "councillor") & res["elected"]].copy()
    wins["winning_margin"] = wins["contest_id"].map(margins)
    return wins


def _load_normalized_inputs(out_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Adapt upstream v2's normalized artifacts to the faithful CDI vocabulary."""
    res = pd.read_csv(out_dir / "election_results.csv", parse_dates=["election_date"])
    res = res.rename(
        columns={
            "office_type": "office",
            "person_id": "candidate_id",
            "boundary_regime": "ward_system",
            "official_district_id": "ward_number",
        }
    )
    res["ward_number"] = pd.to_numeric(
        res["ward_number"].astype("string").str.extract(r"(\d+)$", expand=False),
        errors="coerce",
    )
    res["ward_system"] = res["ward_system"].replace(
        {
            "toronto_council_44_wards": "44-ward",
            "toronto_council_25_wards": "25-ward",
        }
    )

    tenures = pd.read_csv(out_dir / "office_tenures.csv", parse_dates=["ended_on"])
    people = pd.read_csv(out_dir / "people.csv")
    election_dates = (
        res[
            res["election_year"].isin(SCOREABLE_YEARS)
            & res["election_type"].eq("general")
            & res["office"].eq("councillor")
        ][["election_year", "election_date"]]
        .drop_duplicates()
        .set_index("election_date")["election_year"]
    )
    comp = tenures[
        tenures["office_type"].eq("councillor") & tenures["ended_on"].isin(election_dates.index)
    ].copy()
    comp["election_year"] = comp["ended_on"].map(election_dates)
    comp = comp.merge(
        people[["person_id", "preferred_name"]], on="person_id", how="left", validate="many_to_one"
    )
    comp = comp.rename(
        columns={
            "person_id": "candidate_id",
            "preferred_name": "member_name",
            "source_authority": "incumbent_source",
            "office_type": "office",
        }
    )
    if comp.duplicated(["election_year", "candidate_id"]).any():
        raise ValueError("normalized office tenures contain duplicate pre-election councillors")
    return comp, res


def build_index(rd: Path | None = None) -> pd.DataFrame:
    """Build the full incumbent-year defeatability table and write it to data/out/."""
    rd = Path(rd) if rd is not None else results_dir()
    out_dir = rd / "data" / "out"

    comp, res = _load_normalized_inputs(out_dir)

    margins = contest_margins(res)
    wins = _elected_council_wins(res, margins)
    baseline_2018 = build_2018_baseline(rd).set_index("ward_number")["baseline_2014_electors"]

    rows = []
    for year in SCOREABLE_YEARS:
        incumbents = comp[(comp["election_year"] == year) & (comp["office"] == "councillor")]
        general = res[
            (res["election_year"] == year)
            & (res["office"] == "councillor")
            & (res["election_type"] == "general")
        ]
        ran_row = {
            r.candidate_id: r for r in general.itertuples(index=False) if pd.notna(r.candidate_id)
        }
        # top opponent votes per contest, for the realized year-Y margin.
        top_two = general[general["vote_rank"].isin([1, 2])]

        for inc in incumbents.itertuples(index=False):
            row = {
                "election_year": year,
                "candidate_id": inc.candidate_id,
                "candidate_name": inc.member_name,
                "incumbent_source": inc.incumbent_source,
                "cross_era": year == CROSS_ERA_YEAR,
                "ran_for_reelection": False,
                "no_prior_result": False,
                "dual_incumbent_2018": False,
            }

            # Realized year-Y outcome — recorded whether or not a prior win exists,
            # so an unscoreable incumbent who still ran keeps their ran flag/result.
            ran = None if pd.isna(inc.candidate_id) else ran_row.get(inc.candidate_id)
            if ran is not None:
                row["ran_for_reelection"] = True
                row["ward_system"] = ran.ward_system
                row["ward_number"] = ran.ward_number
                row["elected_Y"] = bool(ran.elected)
                row["new_vote_share_Y"] = ran.vote_share
                row["n_candidates_Y"] = ran.n_candidates
                contest = top_two[top_two["contest_id"] == ran.contest_id]
                winner_v = contest[contest["vote_rank"] == 1]["votes"].iloc[0]
                if ran.elected:
                    runner_v = contest[contest["vote_rank"] == 2]["votes"]
                    row["margin_Y"] = winner_v - (runner_v.iloc[0] if len(runner_v) else 0)
                else:
                    row["margin_Y"] = ran.votes - winner_v

            # Prior-win components (the two vote-based measures + the growth term).
            prior = (
                None
                if pd.isna(inc.candidate_id)
                else latest_prior_win(wins, inc.candidate_id, year)
            )
            if prior is None or pd.isna(prior.vote_share):
                # No usable electoral baseline (appointee, pre-dataset win, or acclaimed).
                row["no_prior_result"] = True
                rows.append(row)
                continue

            row["prior_win_year"] = int(prior.election_year)
            row["prior_win_type"] = prior.election_type
            row["prior_n_candidates"] = prior.n_candidates
            row["by_election_incumbent"] = prior.election_type == "by_election"
            row["vote_share"] = prior.vote_share
            row["elector_share"] = prior.votes / prior.eligible_electors
            row["prior_winning_margin"] = prior.winning_margin
            if ran is None:
                row.setdefault("ward_system", prior.ward_system)
                row.setdefault("ward_number", prior.ward_number)
            else:
                # Growth needs the year-Y ward the incumbent contested (Q17b).
                baseline = (
                    baseline_2018.get(ran.ward_number)
                    if year == CROSS_ERA_YEAR
                    else prior.eligible_electors
                )
                row["new_electors"] = ran.eligible_electors - baseline
                row["new_voter_margin"] = row["new_electors"] - prior.winning_margin

            rows.append(row)

    df = pd.DataFrame(rows)

    # Rank within each year's pool of runners that have a full three-component vector.
    df["rank_sum"] = pd.NA
    poolable = df["ran_for_reelection"] & df[
        ["vote_share", "elector_share", "new_voter_margin"]
    ].notna().all(axis=1)
    ranked_parts = []
    for year, pool in df[poolable].groupby("election_year"):
        ranked_parts.append(compute_index(pool))
    ranked = pd.concat(ranked_parts)
    rank_cols = [
        "rank_vote_share",
        "rank_elector_share",
        "rank_new_voter_margin",
        "rank_sum",
        "pool_size",
        "defeatability_100",
    ]
    df.loc[ranked.index, rank_cols] = ranked[rank_cols]

    # Two former incumbents running in the same 2018 ward.
    ran_2018 = df[(df["election_year"] == 2018) & df["ran_for_reelection"]]
    dual_wards = ran_2018["ward_number"].value_counts()
    dual_wards = set(dual_wards[dual_wards >= 2].index)
    df.loc[
        (df["election_year"] == 2018)
        & df["ward_number"].isin(dual_wards)
        & df["ran_for_reelection"],
        "dual_incumbent_2018",
    ] = True

    return df.reindex(columns=OUTPUT_COLUMNS)


def main() -> None:
    df = build_index(results_dir())
    dest = output_dir() / "defeatability_index.csv"
    dest.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(dest, index=False)
    print(f"wrote {len(df)} incumbent-year rows to {dest}")


if __name__ == "__main__":
    main()
