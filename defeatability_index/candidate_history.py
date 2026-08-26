"""Build candidate-level own-history and Opponent-field history features.

The public interface is deliberately in-memory: callers supply normalized election
results plus any sourced external Candidacies and Office tenures. The module hides
strict temporal filtering, signed margins, career classification, Candidate regimes,
and self-excluding Opponent-field aggregation behind one DataFrame-to-DataFrame seam.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

CAREER_RECORDS_WITH_OFFICE = {"prior_officeholder", "mixed_prior_office_record"}


def _as_bool(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series.dtype):
        return series.astype("boolean")
    return (
        series.astype("string").str.casefold().map({"true": True, "false": False}).astype("boolean")
    )


def _with_performance_margins(results: pd.DataFrame) -> pd.DataFrame:
    """Attach the signed Vote-share margin for every resolved Candidacy."""
    rows = results.copy()
    rows["elected"] = _as_bool(rows["elected"])
    rows["prior_performance_margin"] = np.nan
    for _, contest in rows.groupby("contest_id", sort=False):
        valid = contest[contest["vote_share"].notna()]
        elected = valid[valid["elected"].fillna(False)]
        if elected.empty:
            continue
        winner_share = float(elected.iloc[0]["vote_share"])
        runner_up = valid.loc[~valid.index.isin(elected.index), "vote_share"].max()
        for idx, candidate in valid.iterrows():
            share = float(candidate["vote_share"])
            if bool(candidate["elected"]):
                if pd.notna(runner_up):
                    rows.at[idx, "prior_performance_margin"] = share - float(runner_up)
            else:
                rows.at[idx, "prior_performance_margin"] = share - winner_share
    return rows


def _normalise_external_candidacies(external: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "person_id",
        "election_date",
        "office_type",
        "elected",
        "vote_share",
        "prior_performance_margin",
        "source_detail",
    ]
    if external.empty:
        return pd.DataFrame(columns=columns)
    missing = set(columns) - set(external.columns)
    if missing:
        raise ValueError(f"external Candidacies missing columns: {sorted(missing)}")
    history = external[columns].copy()
    history["election_date"] = pd.to_datetime(history["election_date"])
    history["elected"] = _as_bool(history["elected"])
    return history


def _career_features(prior: pd.DataFrame, election_date: pd.Timestamp) -> dict:
    if prior.empty:
        return {
            "career_record": "no_observed_prior_office_record",
            "prior_candidacy_count": 0,
            "victory_count": 0,
            "prior_loss_count": 0,
            "office_breadth": 0,
            "prior_office_types_contested": "",
            "prior_office_types_won": "",
            "most_recent_prior_margin": np.nan,
            "best_prior_margin": np.nan,
            "mean_prior_win_margin": np.nan,
            "most_recent_prior_date": pd.NaT,
            "years_since_last_run": np.nan,
            "years_since_last_win": np.nan,
        }

    prior = prior.sort_values("election_date")
    won = prior["elected"].fillna(False).astype(bool)
    wins = prior[won]
    losses = prior[~won]
    if not wins.empty and not losses.empty:
        record = "mixed_prior_office_record"
    elif not wins.empty:
        record = "prior_officeholder"
    else:
        record = "prior_unsuccessful_candidate"

    margins = prior["prior_performance_margin"].dropna()
    win_margins = wins["prior_performance_margin"].dropna()
    last = prior.iloc[-1]
    last_win_date = wins["election_date"].max() if not wins.empty else pd.NaT
    return {
        "career_record": record,
        "prior_candidacy_count": len(prior),
        "victory_count": len(wins),
        "prior_loss_count": len(losses),
        "office_breadth": int(wins["office_type"].nunique()),
        "prior_office_types_contested": "|".join(sorted(prior["office_type"].unique())),
        "prior_office_types_won": "|".join(sorted(wins["office_type"].unique())),
        "most_recent_prior_margin": float(last["prior_performance_margin"])
        if pd.notna(last["prior_performance_margin"])
        else np.nan,
        "best_prior_margin": float(margins.max()) if not margins.empty else np.nan,
        "mean_prior_win_margin": float(win_margins.mean()) if not win_margins.empty else np.nan,
        "most_recent_prior_date": last["election_date"],
        "years_since_last_run": (election_date - last["election_date"]).days / 365.25,
        "years_since_last_win": (election_date - last_win_date).days / 365.25
        if pd.notna(last_win_date)
        else np.nan,
    }


def _prior_council_features(prior: pd.DataFrame, *, is_incumbent: bool) -> dict:
    prior = prior.sort_values("election_date")
    won = prior["elected"].fillna(False).astype(bool) if not prior.empty else pd.Series(dtype=bool)
    wins = prior[won] if not prior.empty else prior
    last = prior.iloc[-1] if not prior.empty else None
    return {
        "prior_council_candidacy_count": len(prior),
        "prior_council_victory_count": len(wins),
        "most_recent_prior_council_margin": (
            float(last["prior_performance_margin"])
            if last is not None and pd.notna(last["prior_performance_margin"])
            else np.nan
        ),
        "most_recent_prior_council_date": last["election_date"] if last is not None else pd.NaT,
        "returning_councillor": bool(len(wins) and not is_incumbent),
    }


def _combined_prior_elected_features(career: dict, council: dict) -> dict:
    include_council = bool(council["returning_councillor"])
    non_council_date = career["most_recent_prior_date"]
    council_date = council["most_recent_prior_council_date"] if include_council else pd.NaT
    use_council_margin = pd.notna(council_date) and (
        pd.isna(non_council_date) or council_date > non_council_date
    )
    return {
        "prior_elected_candidacy_count": career["prior_candidacy_count"]
        + (council["prior_council_candidacy_count"] if include_council else 0),
        "prior_elected_victory_count": career["victory_count"]
        + (council["prior_council_victory_count"] if include_council else 0),
        "most_recent_prior_elected_margin": (
            council["most_recent_prior_council_margin"]
            if use_council_margin
            else career["most_recent_prior_margin"]
        ),
    }


def _holds_office(
    tenures: pd.DataFrame, person_id: str, election_date: pd.Timestamp, *, office: str | None
) -> bool:
    if tenures.empty:
        return False
    held = tenures[tenures["person_id"].eq(person_id)]
    if office is None:
        held = held[~held["office_type"].eq("councillor")]
    else:
        held = held[held["office_type"].eq(office)]
    starts_before = held["started_on"].isna() | held["started_on"].lt(election_date)
    ends_after = held["ended_on"].isna() | held["ended_on"].ge(election_date)
    return bool((starts_before & ends_after).any())


def _assign_regimes(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    regimes = pd.Series(index=frame.index, dtype="string")
    for _, contest in frame.groupby("contest_id", sort=False):
        incumbents = contest["_is_incumbent"].fillna(False)
        n_incumbents = int(incumbents.sum())
        if n_incumbents == 0:
            regimes.loc[contest.index] = "open_contest"
        elif n_incumbents > 1:
            regimes.loc[contest.index] = "incumbent_collision"
        else:
            regimes.loc[contest.index] = np.where(
                incumbents, "incumbent", "non_incumbent_facing_incumbent"
            )
    frame["candidate_regime"] = regimes
    return frame


def _attach_opponent_field(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    output = {
        "opponent_count": [],
        "any_prior_officeholder_opponent": [],
        "prior_officeholder_opponent_count": [],
        "prior_officeholder_opponent_share": [],
        "strongest_opponent_prior_margin": [],
        "opponent_office_types": [],
        "max_opponent_victory_count": [],
        "total_opponent_victory_count": [],
        "any_current_other_officeholder_opponent": [],
        "any_returning_councillor_opponent": [],
        "returning_councillor_opponent_count": [],
        "strongest_opponent_prior_council_margin": [],
        "strongest_opponent_prior_elected_margin": [],
        "max_opponent_prior_elected_victory_count": [],
        "any_prior_elected_office_opponent": [],
        "any_incumbent_opponent": [],
        "opponent_history_complete": [],
        "any_opponent_all_prior_victory": [],
        "any_opponent_prior_council_run_without_victory": [],
        "strongest_opponent_most_recent_all_prior_margin": [],
        "any_opponent_prior_trustee_victory": [],
        "sole_candidate_with_all_prior_race": [],
        "sole_candidate_with_all_prior_victory": [],
    }
    row_order = []
    for _, contest in frame.groupby("contest_id", sort=False):
        for idx in contest.index:
            opponents = contest.drop(index=idx)
            officeholders = opponents["career_record"].isin(CAREER_RECORDS_WITH_OFFICE)
            count = int(officeholders.sum())
            opponent_count = len(opponents)
            types = set()
            for value in opponents["prior_office_types_won"].dropna():
                types.update(part for part in str(value).split("|") if part)
            victories = pd.to_numeric(opponents["victory_count"], errors="coerce")
            returning = opponents["returning_councillor"].fillna(False).astype(bool)
            any_prior_elected = officeholders | returning
            opponent_history_complete = bool(opponents["history_status"].eq("confirmed").all())
            opponent_all_victories = opponents["has_all_prior_victory"].fillna(False).astype(bool)
            opponent_unsuccessful_council = pd.to_numeric(
                opponents["prior_council_candidacy_count"], errors="coerce"
            ).gt(0) & pd.to_numeric(opponents["prior_council_victory_count"], errors="coerce").eq(0)
            opponent_trustee_victories = (
                opponents["prior_office_types_won"]
                .fillna("")
                .str.split("|")
                .map(lambda values: "trustee" in values)
            )
            current_has_history = bool(
                pd.notna(frame.at[idx, "all_prior_candidacy_count"])
                and frame.at[idx, "all_prior_candidacy_count"] > 0
            )
            current_has_victory = bool(
                pd.notna(frame.at[idx, "has_all_prior_victory"])
                and frame.at[idx, "has_all_prior_victory"]
            )

            row_order.append(idx)
            output["opponent_count"].append(opponent_count)
            output["any_prior_officeholder_opponent"].append(count > 0)
            output["prior_officeholder_opponent_count"].append(count)
            output["prior_officeholder_opponent_share"].append(
                count / opponent_count if opponent_count else np.nan
            )
            output["strongest_opponent_prior_margin"].append(
                opponents["most_recent_prior_margin"].max(skipna=True)
            )
            output["opponent_office_types"].append("|".join(sorted(types)))
            output["max_opponent_victory_count"].append(
                victories.max(skipna=True) if victories.notna().any() else np.nan
            )
            output["total_opponent_victory_count"].append(victories.sum(min_count=1))
            output["any_current_other_officeholder_opponent"].append(
                bool(opponents["current_other_officeholder"].fillna(False).any())
            )
            output["any_returning_councillor_opponent"].append(bool(returning.any()))
            output["returning_councillor_opponent_count"].append(int(returning.sum()))
            output["strongest_opponent_prior_council_margin"].append(
                opponents["most_recent_prior_council_margin"].max(skipna=True)
            )
            output["strongest_opponent_prior_elected_margin"].append(
                opponents["most_recent_prior_elected_margin"].max(skipna=True)
            )
            output["max_opponent_prior_elected_victory_count"].append(
                opponents["prior_elected_victory_count"].max(skipna=True)
            )
            output["any_prior_elected_office_opponent"].append(bool(any_prior_elected.any()))
            output["any_incumbent_opponent"].append(
                bool(opponents["_is_incumbent"].fillna(False).any())
            )
            output["opponent_history_complete"].append(opponent_history_complete)
            output["any_opponent_all_prior_victory"].append(
                True
                if opponent_all_victories.any()
                else False
                if opponent_history_complete
                else pd.NA
            )
            output["any_opponent_prior_council_run_without_victory"].append(
                True
                if opponent_unsuccessful_council.any()
                else False
                if opponent_history_complete
                else pd.NA
            )
            output["strongest_opponent_most_recent_all_prior_margin"].append(
                opponents["most_recent_all_prior_margin"].max(skipna=True)
                if opponent_history_complete
                else np.nan
            )
            output["any_opponent_prior_trustee_victory"].append(
                True
                if opponent_trustee_victories.any()
                else False
                if opponent_history_complete
                else pd.NA
            )
            output["sole_candidate_with_all_prior_race"].append(
                bool(current_has_history and not opponents["all_prior_candidacy_count"].gt(0).any())
                if opponent_history_complete
                else pd.NA
            )
            output["sole_candidate_with_all_prior_victory"].append(
                bool(current_has_victory and not opponent_all_victories.any())
                if opponent_history_complete
                else pd.NA
            )
    field = pd.DataFrame(output, index=row_order)
    for column in field:
        frame.loc[field.index, column] = field[column]
    return frame


def build_candidate_history_frame(
    election_results: pd.DataFrame,
    career_candidacies: pd.DataFrame,
    career_tenures: pd.DataFrame,
) -> pd.DataFrame:
    """Return council Candidacies with strictly prior own and Opponent-field history."""
    results = _with_performance_margins(election_results)
    results["election_date"] = pd.to_datetime(results["election_date"])
    external = _normalise_external_candidacies(career_candidacies)

    history_columns = [
        "person_id",
        "election_date",
        "office_type",
        "elected",
        "vote_share",
        "prior_performance_margin",
    ]
    history = pd.concat([results[history_columns], external[history_columns]], ignore_index=True)

    tenures = career_tenures.copy()
    if not tenures.empty:
        required = {"person_id", "office_type", "started_on", "ended_on"}
        missing = required - set(tenures.columns)
        if missing:
            raise ValueError(f"Office tenures missing columns: {sorted(missing)}")
        tenures["started_on"] = pd.to_datetime(tenures["started_on"])
        tenures["ended_on"] = pd.to_datetime(tenures["ended_on"])

    council = results[results["office_type"].eq("councillor")].copy()
    feature_rows = []
    for candidate in council.itertuples():
        person_id = candidate.person_id
        election_date = candidate.election_date
        if pd.isna(person_id):
            features = {
                "history_status": "identity_unresolved",
                "career_record": pd.NA,
                "prior_candidacy_count": pd.NA,
                "victory_count": pd.NA,
                "prior_loss_count": pd.NA,
                "office_breadth": pd.NA,
                "prior_office_types_contested": pd.NA,
                "prior_office_types_won": pd.NA,
                "most_recent_prior_margin": np.nan,
                "best_prior_margin": np.nan,
                "mean_prior_win_margin": np.nan,
                "most_recent_prior_date": pd.NaT,
                "years_since_last_run": np.nan,
                "years_since_last_win": np.nan,
                "current_other_officeholder": pd.NA,
                "prior_council_candidacy_count": pd.NA,
                "prior_council_victory_count": pd.NA,
                "most_recent_prior_council_margin": np.nan,
                "most_recent_prior_council_date": pd.NaT,
                "returning_councillor": pd.NA,
                "has_prior_elected_office": pd.NA,
                "prior_elected_candidacy_count": pd.NA,
                "prior_elected_victory_count": pd.NA,
                "most_recent_prior_elected_margin": np.nan,
                "all_prior_candidacy_count": pd.NA,
                "all_prior_victory_count": pd.NA,
                "has_all_prior_victory": pd.NA,
                "most_recent_all_prior_margin": np.nan,
                "most_recent_all_prior_was_victory": pd.NA,
                "prior_council_run_without_victory": pd.NA,
                "multiple_prior_council_runs_without_victory": pd.NA,
                "_is_incumbent": bool(candidate.incumbent is True),
            }
        else:
            all_prior = history[
                history["person_id"].eq(person_id) & history["election_date"].lt(election_date)
            ].sort_values("election_date")
            prior = history[
                history["person_id"].eq(person_id)
                & ~history["office_type"].eq("councillor")
                & history["election_date"].lt(election_date)
            ]
            prior_council = history[
                history["person_id"].eq(person_id)
                & history["office_type"].eq("councillor")
                & history["election_date"].lt(election_date)
            ]
            is_incumbent = bool(candidate.incumbent is True) or _holds_office(
                tenures, person_id, election_date, office="councillor"
            )
            council_features = _prior_council_features(prior_council, is_incumbent=is_incumbent)
            career_features = _career_features(prior, election_date)
            combined_features = _combined_prior_elected_features(career_features, council_features)
            most_recent_all_prior = all_prior.iloc[-1] if len(all_prior) else None
            features = {
                "history_status": "confirmed",
                **career_features,
                **council_features,
                **combined_features,
                "all_prior_candidacy_count": len(all_prior),
                "all_prior_victory_count": int(
                    all_prior["elected"].fillna(False).astype(bool).sum()
                ),
                "has_all_prior_victory": bool(
                    all_prior["elected"].fillna(False).astype(bool).any()
                ),
                "most_recent_all_prior_margin": (
                    float(most_recent_all_prior["prior_performance_margin"])
                    if most_recent_all_prior is not None
                    and pd.notna(most_recent_all_prior["prior_performance_margin"])
                    else np.nan
                ),
                "most_recent_all_prior_was_victory": (
                    bool(most_recent_all_prior["elected"])
                    if most_recent_all_prior is not None
                    and pd.notna(most_recent_all_prior["elected"])
                    else pd.NA
                ),
                "prior_council_run_without_victory": bool(
                    council_features["prior_council_candidacy_count"] > 0
                    and council_features["prior_council_victory_count"] == 0
                ),
                "multiple_prior_council_runs_without_victory": bool(
                    council_features["prior_council_candidacy_count"] >= 2
                    and council_features["prior_council_victory_count"] == 0
                ),
                "has_prior_elected_office": bool(
                    career_features["career_record"] in CAREER_RECORDS_WITH_OFFICE
                    or council_features["returning_councillor"]
                ),
                "current_other_officeholder": _holds_office(
                    tenures, person_id, election_date, office=None
                ),
                "_is_incumbent": is_incumbent,
            }
        feature_rows.append(features)

    features = pd.DataFrame(feature_rows, index=council.index)
    frame = pd.concat([council, features], axis=1)
    frame["is_by_election"] = frame["election_type"].eq("by_election")
    frame = _assign_regimes(frame)
    frame = _attach_opponent_field(frame)
    return frame.drop(
        columns=[
            "_is_incumbent",
            "prior_performance_margin",
            "most_recent_prior_date",
            "most_recent_prior_council_date",
        ]
    ).reset_index(drop=True)
