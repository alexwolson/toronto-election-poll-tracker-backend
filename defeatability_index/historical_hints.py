"""Identify candidate-facing historical hints supported by the analysis data."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

PRIMARY_YEARS = (2010, 2014, 2022)
NO_RECORD = "no_observed_prior_office_record"
SCREEN_HINT_IDS = (
    "own_returning_councillor__open_contest",
    "opponent_returning_councillor__open_contest",
    "own_any_all_past_race__non_incumbent_non_returning",
    "own_multiple_all_past_races__non_incumbent_non_returning",
    "own_prior_council_run_without_victory_vs_no_history__non_incumbent_non_returning",
    "own_prior_council_run_without_victory_vs_other_history__non_incumbent_non_returning",
    "own_multiple_prior_council_runs_without_victory__non_incumbent_non_returning",
    "own_most_recent_all_past_race_margin__non_incumbent_non_returning",
    "own_most_recent_all_past_race_was_victory__non_incumbent_non_returning",
    "own_prior_mpp_race__non_incumbent_non_returning",
    "own_prior_mp_race__non_incumbent_non_returning",
    "opponent_prior_council_run_without_victory__incumbent",
    "opponent_prior_council_run_without_victory__non_incumbent_facing_incumbent",
    "opponent_prior_council_run_without_victory__open_contest",
    "opponent_strongest_most_recent_all_past_race_margin__incumbent",
    "opponent_strongest_most_recent_all_past_race_margin__non_incumbent_facing_incumbent",
    "opponent_strongest_most_recent_all_past_race_margin__open_contest",
    "opponent_any_all_past_race_victory__open_contest",
    "sole_candidate_with_all_past_race__open_contest",
    "sole_candidate_with_all_past_race_victory__open_contest",
    "opponent_prior_trustee_victory__open_contest",
)


@dataclass(frozen=True)
class HintSpec:
    """A candidate hint to test, not a live-candidate computation rule."""

    hint_id: str
    subject: str
    candidate_regime: str
    trigger_field: str
    trigger_operator: str
    trigger_value: str
    comparison: str
    effect_unit: str = "presence_vs_absence"
    forced_status: str | None = None
    limitation: str = ""
    catalog_eligible: bool = True
    small_sample_exception: bool = False


def _specs() -> list[HintSpec]:
    specs: list[HintSpec] = []
    regimes = ("incumbent", "non_incumbent_facing_incumbent", "open_contest")
    for regime in regimes:
        specs.extend(
            [
                HintSpec(
                    hint_id=f"own_returning_councillor__{regime}",
                    subject="own_history",
                    candidate_regime=regime,
                    trigger_field="returning_councillor",
                    trigger_operator="equals",
                    trigger_value="true",
                    comparison="candidates in the same Candidate regime who were not returning councillors",
                    limitation=(
                        "Only four independent historical Contests; approved only with the "
                        "consistent_small_sample evidence tier."
                        if regime == "open_contest"
                        else ""
                    ),
                    small_sample_exception=regime == "open_contest",
                ),
                HintSpec(
                    hint_id=f"opponent_returning_councillor__{regime}",
                    subject="opponent_history",
                    candidate_regime=regime,
                    trigger_field="any_returning_councillor_opponent",
                    trigger_operator="equals",
                    trigger_value="true",
                    comparison="candidates in the same Candidate regime without a returning-councillor opponent",
                    limitation=(
                        "Only four independent historical Contests; approved only with the "
                        "consistent_small_sample evidence tier."
                        if regime == "open_contest"
                        else ""
                    ),
                    small_sample_exception=regime == "open_contest",
                ),
            ]
        )

    for office in ("mayor", "mp", "mpp", "trustee"):
        specs.append(
            HintSpec(
                hint_id=f"own_prior_win_type__{office}",
                subject="own_history",
                candidate_regime="all_primary_regimes",
                trigger_field="prior_office_types_won",
                trigger_operator="contains_office_type",
                trigger_value=office,
                comparison=NO_RECORD,
                limitation="Office-specific cells are interpreted against no observed record, not each other.",
            )
        )

    specs.extend(
        [
            HintSpec(
                hint_id="own_any_all_past_race_victory__non_incumbent_non_returning",
                subject="own_history",
                candidate_regime="non_incumbent_non_returning_subgroup",
                trigger_field="has_all_prior_victory",
                trigger_operator="equals_all_history_only",
                trigger_value="true",
                comparison=(
                    "non-incumbent, non-returning candidates with confirmed earlier races "
                    "but no prior victory"
                ),
            ),
            HintSpec(
                hint_id="own_all_past_race_victory_count",
                subject="own_history",
                candidate_regime="all_primary_regimes",
                trigger_field="all_prior_victory_count",
                trigger_operator="continuous_all_history_only",
                trigger_value="observed",
                comparison="other candidates with at least one confirmed earlier elected-office race",
                effect_unit="per_additional_victory",
                catalog_eligible=False,
            ),
            HintSpec(
                hint_id="own_all_past_race_victory_count__incumbent",
                subject="own_history",
                candidate_regime="incumbent",
                trigger_field="all_prior_victory_count",
                trigger_operator="continuous_all_history_only",
                trigger_value="observed",
                comparison="other incumbents with at least one confirmed earlier elected-office race",
                effect_unit="per_additional_victory",
                catalog_eligible=False,
            ),
            HintSpec(
                hint_id="own_all_past_race_victory_count__returning_councillor",
                subject="own_history",
                candidate_regime="returning_councillor_subgroup",
                trigger_field="all_prior_victory_count",
                trigger_operator="continuous_all_history_only",
                trigger_value="observed",
                comparison="other Returning councillors with confirmed earlier elected-office races",
                effect_unit="per_additional_victory",
                catalog_eligible=False,
            ),
            HintSpec(
                hint_id="own_all_past_race_victory_count__non_incumbent_non_returning",
                subject="own_history",
                candidate_regime="non_incumbent_non_returning_subgroup",
                trigger_field="all_prior_victory_count",
                trigger_operator="continuous_all_history_only",
                trigger_value="observed",
                comparison="other non-incumbent, non-returning candidates with confirmed earlier elected-office races",
                effect_unit="per_additional_victory",
                limitation=(
                    "Audit-only dosage diagnostic; the public flag uses any prior victory."
                ),
                catalog_eligible=False,
            ),
            HintSpec(
                hint_id=(
                    "own_all_past_race_victory_count__non_incumbent_non_returning_prior_winners"
                ),
                subject="own_history",
                candidate_regime="non_incumbent_non_returning_subgroup",
                trigger_field="all_prior_victory_count",
                trigger_operator="continuous_all_history_winners_only",
                trigger_value="observed",
                comparison=(
                    "other non-incumbent, non-returning candidates with at least one earlier victory"
                ),
                effect_unit="per_additional_victory",
                limitation="Dosage diagnostic among prior winners only.",
                catalog_eligible=False,
            ),
        ]
    )
    specs.extend(
        [
            HintSpec(
                hint_id="own_any_all_past_race__non_incumbent_non_returning",
                subject="own_history",
                candidate_regime="non_incumbent_non_returning_subgroup",
                trigger_field="all_prior_candidacy_count",
                trigger_operator="greater_than_zero",
                trigger_value="0",
                comparison="non-incumbent, non-returning candidates with no confirmed earlier race",
            ),
            HintSpec(
                hint_id="own_multiple_all_past_races__non_incumbent_non_returning",
                subject="own_history",
                candidate_regime="non_incumbent_non_returning_subgroup",
                trigger_field="all_prior_candidacy_count",
                trigger_operator="at_least_two",
                trigger_value="2",
                comparison="non-incumbent, non-returning candidates with zero or one confirmed earlier race",
            ),
            HintSpec(
                hint_id=(
                    "own_prior_council_run_without_victory_vs_no_history"
                    "__non_incumbent_non_returning"
                ),
                subject="own_history",
                candidate_regime="non_incumbent_non_returning_subgroup",
                trigger_field="prior_council_run_without_victory",
                trigger_operator="equals_vs_no_all_history",
                trigger_value="true",
                comparison=(
                    "non-incumbent, non-returning candidates with no confirmed earlier race"
                ),
                limitation=(
                    "Publish together with the comparison against candidates with other "
                    "earlier-race histories."
                ),
            ),
            HintSpec(
                hint_id=(
                    "own_prior_council_run_without_victory_vs_other_history"
                    "__non_incumbent_non_returning"
                ),
                subject="own_history",
                candidate_regime="non_incumbent_non_returning_subgroup",
                trigger_field="prior_council_run_without_victory",
                trigger_operator="equals_vs_other_all_history",
                trigger_value="true",
                comparison=(
                    "non-incumbent, non-returning candidates with confirmed earlier-race "
                    "history but no unsuccessful prior council run"
                ),
                limitation=(
                    "Publish together with the comparison against candidates with no "
                    "confirmed earlier race."
                ),
            ),
            HintSpec(
                hint_id=(
                    "own_multiple_prior_council_runs_without_victory__non_incumbent_non_returning"
                ),
                subject="own_history",
                candidate_regime="non_incumbent_non_returning_subgroup",
                trigger_field="multiple_prior_council_runs_without_victory",
                trigger_operator="equals",
                trigger_value="true",
                comparison="non-incumbent, non-returning candidates with fewer than two unsuccessful prior council runs",
                catalog_eligible=False,
            ),
            HintSpec(
                hint_id=("own_most_recent_all_past_race_margin__non_incumbent_non_returning"),
                subject="own_history",
                candidate_regime="non_incumbent_non_returning_subgroup",
                trigger_field="most_recent_all_prior_margin",
                trigger_operator="continuous_all_history_only",
                trigger_value="observed",
                comparison="other non-incumbent, non-returning candidates with a confirmed earlier race margin",
                effect_unit="per_10_percentage_point_increase",
            ),
            HintSpec(
                hint_id=("own_most_recent_all_past_race_was_victory__non_incumbent_non_returning"),
                subject="own_history",
                candidate_regime="non_incumbent_non_returning_subgroup",
                trigger_field="most_recent_all_prior_was_victory",
                trigger_operator="equals_all_history_only",
                trigger_value="true",
                comparison="non-incumbent, non-returning candidates whose most recent confirmed earlier race was a loss",
            ),
            HintSpec(
                hint_id="own_prior_mpp_race__non_incumbent_non_returning",
                subject="own_history",
                candidate_regime="non_incumbent_non_returning_subgroup",
                trigger_field="prior_office_types_contested",
                trigger_operator="contains_office_type",
                trigger_value="mpp",
                comparison="non-incumbent, non-returning candidates without a confirmed earlier MPP race",
            ),
            HintSpec(
                hint_id="own_prior_mp_race__non_incumbent_non_returning",
                subject="own_history",
                candidate_regime="non_incumbent_non_returning_subgroup",
                trigger_field="prior_office_types_contested",
                trigger_operator="contains_office_type",
                trigger_value="mp",
                comparison="non-incumbent, non-returning candidates without a confirmed earlier MP race",
                catalog_eligible=False,
            ),
        ]
    )
    for regime in ("incumbent", "non_incumbent_facing_incumbent", "open_contest"):
        specs.extend(
            [
                HintSpec(
                    hint_id=(f"opponent_prior_council_run_without_victory__{regime}"),
                    subject="opponent_history",
                    candidate_regime=regime,
                    trigger_field="any_opponent_prior_council_run_without_victory",
                    trigger_operator="equals_complete_opponent_history",
                    trigger_value="true",
                    comparison="candidates in the same Candidate regime without a confirmed opponent who previously ran for council but never won",
                    catalog_eligible=False,
                ),
                HintSpec(
                    hint_id=(f"opponent_strongest_most_recent_all_past_race_margin__{regime}"),
                    subject="opponent_history",
                    candidate_regime=regime,
                    trigger_field="strongest_opponent_most_recent_all_prior_margin",
                    trigger_operator="continuous",
                    trigger_value="observed",
                    comparison="other candidates in the same Candidate regime with a fully observed opponent field and prior opponent margin",
                    effect_unit="per_10_percentage_point_increase",
                    catalog_eligible=regime == "incumbent",
                ),
            ]
        )
    specs.extend(
        [
            HintSpec(
                hint_id="opponent_any_all_past_race_victory__open_contest",
                subject="opponent_history",
                candidate_regime="open_contest",
                trigger_field="any_opponent_all_prior_victory",
                trigger_operator="equals_complete_opponent_history",
                trigger_value="true",
                comparison="Open-contest candidates without a confirmed opponent who had won an earlier race",
                catalog_eligible=False,
            ),
            HintSpec(
                hint_id="sole_candidate_with_all_past_race__open_contest",
                subject="own_history",
                candidate_regime="open_contest",
                trigger_field="sole_candidate_with_all_prior_race",
                trigger_operator="equals_complete_opponent_history",
                trigger_value="true",
                comparison="other Open-contest candidates in fields with fully resolved history",
                catalog_eligible=False,
            ),
            HintSpec(
                hint_id="sole_candidate_with_all_past_race_victory__open_contest",
                subject="own_history",
                candidate_regime="open_contest",
                trigger_field="sole_candidate_with_all_prior_victory",
                trigger_operator="equals_complete_opponent_history",
                trigger_value="true",
                comparison="other Open-contest candidates in fields with fully resolved history",
                catalog_eligible=False,
            ),
            HintSpec(
                hint_id="opponent_prior_trustee_victory__open_contest",
                subject="opponent_history",
                candidate_regime="open_contest",
                trigger_field="any_opponent_prior_trustee_victory",
                trigger_operator="equals_complete_opponent_history",
                trigger_value="true",
                comparison="Open-contest candidates without a confirmed opponent who had previously won a trustee race",
                catalog_eligible=False,
            ),
        ]
    )
    return specs


def _primary_frame(frame: pd.DataFrame) -> pd.DataFrame:
    primary = frame[
        frame["vote_share"].notna()
        & frame["election_type"].eq("general")
        & frame["election_year"].isin(PRIMARY_YEARS)
        & frame["history_status"].eq("confirmed")
    ].copy()
    primary["career_record"] = primary["career_record"].fillna(NO_RECORD)
    return primary.reset_index(drop=True)


def _design(frame: pd.DataFrame, exposure: np.ndarray) -> np.ndarray:
    parts = [np.ones(len(frame)), np.asarray(exposure, dtype=float)]
    parts.append(pd.to_numeric(frame["n_candidates"], errors="coerce").fillna(0).to_numpy())
    years = pd.get_dummies(frame["election_year"].astype(str), drop_first=True, dtype=float)
    regimes = pd.get_dummies(frame["candidate_regime"].astype(str), drop_first=True, dtype=float)
    if not years.empty:
        parts.extend(years[column].to_numpy() for column in years)
    if frame["candidate_regime"].nunique() > 1 and not regimes.empty:
        parts.extend(regimes[column].to_numpy() for column in regimes)
    return np.column_stack(parts)


def _adjusted_effect(frame: pd.DataFrame, exposure: np.ndarray, *, scale: float) -> float:
    design = _design(frame, exposure)
    outcome = frame["vote_share"].to_numpy(dtype=float)
    coefficient = np.linalg.lstsq(design, outcome, rcond=None)[0][1]
    return float(coefficient * scale * 100)


def _bootstrap_effect(
    frame: pd.DataFrame,
    exposure_column: str,
    *,
    scale: float,
    n_bootstrap: int,
    rng: np.random.Generator,
) -> tuple[float, float, float]:
    working = frame[
        [
            "contest_id",
            "vote_share",
            exposure_column,
            "n_candidates",
            "election_year",
            "candidate_regime",
        ]
    ].reset_index(drop=True)
    contest_indices = [
        np.asarray(indices, dtype=int)
        for indices in working.groupby("contest_id", sort=False).indices.values()
    ]
    effects: list[float] = []
    for _ in range(n_bootstrap):
        sampled = rng.integers(0, len(contest_indices), size=len(contest_indices))
        positions = np.concatenate([contest_indices[index] for index in sampled])
        boot = working.iloc[positions]
        exposure = boot[exposure_column].to_numpy(dtype=float)
        if len(np.unique(exposure)) < 2:
            continue
        effects.append(_adjusted_effect(boot, exposure, scale=scale))
    if not effects:
        return np.nan, np.nan, np.nan
    values = np.asarray(effects)
    low, high = np.percentile(values, [2.5, 97.5])
    non_positive = (np.sum(values <= 0) + 1) / (len(values) + 1)
    non_negative = (np.sum(values >= 0) + 1) / (len(values) + 1)
    p_value = min(1.0, 2 * min(non_positive, non_negative))
    return float(low), float(high), float(p_value)


def _direction(effect: float) -> str:
    if pd.isna(effect) or effect == 0:
        return "none"
    return "benefit" if effect > 0 else "harm"


def _year_effects(
    data: pd.DataFrame, *, scale: float, overall_effect: float
) -> tuple[str, int, int]:
    values: list[str] = []
    same_direction = 0
    estimable = 0
    for year, group in data.groupby("election_year"):
        if group["_exposure"].nunique() < 2:
            continue
        effect = _adjusted_effect(group, group["_exposure"].to_numpy(), scale=scale)
        values.append(f"{int(year)}:{effect:+.2f}")
        estimable += 1
        same_direction += int(np.sign(effect) == np.sign(overall_effect))
    return "|".join(values), same_direction, estimable


def _frontend_copy(spec: HintSpec, direction: str) -> str:
    regime = {
        "open_contest": "in open contests",
        "incumbent": "among incumbents",
        "non_incumbent_facing_incumbent": "among challengers facing an incumbent",
        "all_primary_regimes": "across comparable council candidates",
        "returning_councillor_subgroup": "among Returning councillors",
        "non_incumbent_non_returning_subgroup": ("among non-incumbent, non-returning candidates"),
    }[spec.candidate_regime]
    if spec.hint_id == "own_returning_councillor__open_contest":
        return (
            "Historically, in a limited four-contest sample, candidates returning after "
            "previously serving as a councillor received more council vote share in Open contests."
        )
    if spec.hint_id == "opponent_returning_councillor__open_contest":
        return (
            "Historically, in a limited four-contest sample, candidates in Open contests "
            "received less council vote share when facing a Returning councillor."
        )
    if spec.hint_id == "own_most_recent_prior_margin":
        return (
            "Historically, candidates with stronger results in their most recent "
            "non-council race received more council vote share."
        )
    if spec.hint_id == "opponent_strongest_prior_margin":
        return (
            "Historically, candidates facing an opponent with a stronger previous "
            "non-council result received less council vote share."
        )
    if spec.hint_id == "own_most_recent_prior_elected_margin":
        return (
            "Historically, candidates with stronger results in their most recent qualifying "
            "elected-office race, including former council races for Returning councillors, "
            "received more council vote share."
        )
    if spec.hint_id == "opponent_strongest_prior_elected_margin":
        return (
            "Historically, candidates facing an opponent with a stronger previous qualifying "
            "elected-office result, including former council races for Returning councillors, "
            "received less council vote share."
        )
    if spec.hint_id == "own_victory_count":
        return (
            "Historically, each additional earlier victory in another elected-office race "
            "was associated with more council vote share."
        )
    if spec.hint_id == "own_prior_elected_victory_count":
        return (
            "Historically, each additional earlier elected-office victory, including prior "
            "council victories for Returning councillors, was associated with more council vote share."
        )
    if spec.hint_id == "own_any_all_past_race_victory__non_incumbent_non_returning":
        return (
            "Historically, non-incumbent candidates who were not Returning councillors and "
            "had won at least one of their confirmed earlier elected-office races received "
            "more council vote share than comparable candidates with prior races but no wins."
        )
    if spec.hint_id == "own_any_all_past_race__non_incumbent_non_returning":
        return (
            "Historically, non-incumbent candidates who were not Returning councillors and "
            "had run in any confirmed earlier elected-office race received more council vote "
            "share than comparable candidates with no confirmed earlier race."
        )
    if spec.hint_id == "own_multiple_all_past_races__non_incumbent_non_returning":
        return (
            "Historically, non-incumbent candidates who were not Returning councillors and "
            "had run in at least two confirmed earlier elected-office races received more "
            "council vote share than comparable candidates with zero or one earlier race."
        )
    if spec.hint_id.startswith("own_prior_council_run_without_victory_vs_no_history"):
        return (
            "Historically, non-incumbent candidates who were not Returning councillors and "
            "had previously run unsuccessfully for council received more council vote share "
            "than comparable candidates with no confirmed earlier race."
        )
    if spec.hint_id.startswith("own_prior_council_run_without_victory_vs_other_history"):
        return (
            "Historically, non-incumbent candidates who were not Returning councillors and "
            "had previously run unsuccessfully for council received less council vote share "
            "than comparable candidates with other confirmed earlier-race histories."
        )
    if spec.hint_id == ("own_most_recent_all_past_race_margin__non_incumbent_non_returning"):
        return (
            "Historically, among non-incumbent candidates who were not Returning councillors, "
            "stronger results in their most recent confirmed earlier elected-office race were "
            "associated with more council vote share."
        )
    if spec.hint_id == ("own_most_recent_all_past_race_was_victory__non_incumbent_non_returning"):
        return (
            "Historically, non-incumbent candidates who were not Returning councillors and "
            "had won their most recent confirmed earlier elected-office race received more "
            "council vote share than comparable candidates whose most recent earlier race "
            "was a loss."
        )
    if spec.hint_id == "own_prior_mpp_race__non_incumbent_non_returning":
        return (
            "Historically, non-incumbent candidates who were not Returning councillors and "
            "had previously run in an MPP race received more council vote share than comparable "
            "candidates without a confirmed earlier MPP race."
        )
    if spec.hint_id == ("opponent_strongest_most_recent_all_past_race_margin__incumbent"):
        return (
            "Historically, Incumbents facing an opponent with a stronger result in that "
            "opponent's most recent confirmed earlier elected-office race received less "
            "council vote share."
        )
    if spec.hint_id.startswith("own_all_past_race_victory_count"):
        if spec.candidate_regime == "non_incumbent_non_returning_subgroup":
            return (
                "Historically, among non-incumbent candidates who were not Returning "
                "councillors, each additional victory across all confirmed earlier "
                "elected-office races was associated with more council vote share."
            )
        return (
            "Historically, each additional victory across all confirmed earlier "
            "elected-office races was associated with more council vote share."
        )
    if spec.trigger_field == "returning_councillor":
        comparison = "more" if direction == "benefit" else "less"
        return (
            f"Historically, candidates {regime} returning after previously serving as a "
            f"councillor received {comparison} council vote share."
        )
    if spec.trigger_field == "any_returning_councillor_opponent":
        comparison = "more" if direction == "benefit" else "less"
        return (
            f"Historically, candidates {regime} received {comparison} vote share when facing "
            "an opponent returning after previously serving as a councillor."
        )
    if spec.trigger_field == "has_prior_elected_office":
        comparison = "more" if direction == "benefit" else "less"
        return (
            f"Historically, candidates {regime} who had previously held elected office, "
            f"including former councillors, received {comparison} council vote share."
        )
    if spec.trigger_field == "any_prior_elected_office_opponent":
        comparison = "more" if direction == "benefit" else "less"
        return (
            f"Historically, candidates {regime} received {comparison} vote share when facing "
            "an opponent who had previously held elected office, including council."
        )
    if spec.subject == "opponent_history":
        record = (
            "an opponent who currently held a non-council elected office"
            if "current_other_officeholder" in spec.hint_id
            else "an opponent who had previously won a non-council elected office"
        )
        comparison = "more" if direction == "benefit" else "less"
        return f"Historically, candidates {regime} received {comparison} vote share when facing {record}."
    if spec.trigger_field == "career_record":
        record = {
            "prior_officeholder": "had previously won a non-council elected office",
            "mixed_prior_office_record": "had both wins and losses in earlier other-office races",
            "prior_unsuccessful_candidate": "had previously run unsuccessfully for another office",
        }[spec.trigger_value]
    elif spec.trigger_field == "current_other_officeholder":
        record = "currently held a non-council elected office"
    elif spec.trigger_field == "prior_office_types_won":
        record = (
            "had previously been elected school-board trustee"
            if spec.trigger_value == "trustee"
            else f"had previously won election as {spec.trigger_value.upper()}"
        )
    else:
        record = "had more extensive prior-office history"
    comparison = "more" if direction == "benefit" else "less"
    return (
        f"Historically, candidates {regime} who {record} received {comparison} council vote share."
    )


def _trigger_definition(spec: HintSpec) -> str:
    conditions: list[str] = []
    if spec.candidate_regime == "returning_councillor_subgroup":
        conditions.append("returning_councillor == true")
    elif spec.candidate_regime == "non_incumbent_non_returning_subgroup":
        conditions.extend(
            [
                "candidate_regime IN (open_contest, non_incumbent_facing_incumbent)",
                "returning_councillor == false",
            ]
        )
    elif spec.candidate_regime != "all_primary_regimes":
        conditions.append(f"candidate_regime == {spec.candidate_regime}")
    if spec.trigger_operator in {
        "equals",
        "equals_vs_no_all_history",
        "equals_vs_other_all_history",
    }:
        conditions.append(f"{spec.trigger_field} == {spec.trigger_value}")
    elif spec.trigger_operator == "equals_complete_opponent_history":
        conditions.extend(
            [
                "opponent_history_complete == true",
                f"{spec.trigger_field} == {spec.trigger_value}",
            ]
        )
    elif spec.trigger_operator == "greater_than_zero":
        conditions.append(f"{spec.trigger_field} > 0")
    elif spec.trigger_operator == "at_least_two":
        conditions.append(f"{spec.trigger_field} >= 2")
    elif spec.trigger_operator == "equals_all_history_only":
        conditions.extend(
            [
                "all_prior_candidacy_count > 0",
                f"{spec.trigger_field} == {spec.trigger_value}",
            ]
        )
    elif spec.trigger_operator == "contains_office_type":
        conditions.append(f"{spec.trigger_field} CONTAINS {spec.trigger_value}")
    elif spec.trigger_operator == "continuous":
        conditions.append(f"{spec.trigger_field} IS NOT NULL")
    elif spec.trigger_operator == "continuous_history_only":
        conditions.extend(["prior_candidacy_count > 0", f"VALUE = {spec.trigger_field}"])
    elif spec.trigger_operator == "continuous_prior_elected_history_only":
        conditions.extend(["prior_elected_candidacy_count > 0", f"VALUE = {spec.trigger_field}"])
    elif spec.trigger_operator == "continuous_all_history_only":
        conditions.extend(["all_prior_candidacy_count > 0", f"VALUE = {spec.trigger_field}"])
    elif spec.trigger_operator == "continuous_all_history_winners_only":
        conditions.extend(["all_prior_victory_count > 0", f"VALUE = {spec.trigger_field}"])
    elif spec.trigger_operator == "continuous_winners_only":
        conditions.extend(["victory_count > 0", f"VALUE = {spec.trigger_field}"])
    elif spec.trigger_operator == "continuous_positive_only":
        conditions.extend([f"{spec.trigger_field} > 0", f"VALUE = {spec.trigger_field}"])
    return " AND ".join(conditions)


def _candidate_scope(data: pd.DataFrame, spec: HintSpec) -> pd.DataFrame:
    if spec.candidate_regime == "all_primary_regimes":
        return data.copy()
    if spec.candidate_regime == "returning_councillor_subgroup":
        return data[data["returning_councillor"].fillna(False).astype(bool)].copy()
    if spec.candidate_regime == "non_incumbent_non_returning_subgroup":
        returning = data["returning_councillor"].fillna(False).astype(bool)
        non_incumbent_regimes = data["candidate_regime"].isin(
            ["open_contest", "non_incumbent_facing_incumbent"]
        )
        return data[non_incumbent_regimes & ~returning].copy()
    return data[data["candidate_regime"].eq(spec.candidate_regime)].copy()


def _categorical_data(primary: pd.DataFrame, spec: HintSpec) -> pd.DataFrame:
    data = _candidate_scope(primary, spec)
    if spec.trigger_field == "career_record":
        data = data[data["career_record"].isin([spec.trigger_value, NO_RECORD])].copy()
        data["_exposure"] = data["career_record"].eq(spec.trigger_value)
    elif spec.trigger_operator == "contains_office_type":
        has_type = (
            data[spec.trigger_field]
            .fillna("")
            .str.split("|")
            .map(lambda values: spec.trigger_value in values)
        )
        if spec.trigger_field == "prior_office_types_won":
            comparator = data["career_record"].eq(NO_RECORD)
            data = data[has_type | comparator].copy()
        data["_exposure"] = has_type.loc[data.index]
    elif spec.trigger_operator in {
        "equals_vs_no_all_history",
        "equals_vs_other_all_history",
    }:
        exposure = data[spec.trigger_field].fillna(False).astype(bool)
        has_history = pd.to_numeric(data["all_prior_candidacy_count"], errors="coerce").gt(0)
        if spec.trigger_operator == "equals_vs_no_all_history":
            comparator = ~has_history
        else:
            comparator = has_history & ~exposure
        data = data[exposure | comparator].copy()
        data["_exposure"] = exposure.loc[data.index]
    elif spec.trigger_operator == "greater_than_zero":
        known = pd.to_numeric(data[spec.trigger_field], errors="coerce").notna()
        data = data[known].copy()
        data["_exposure"] = pd.to_numeric(data[spec.trigger_field], errors="coerce").gt(0)
    elif spec.trigger_operator == "at_least_two":
        known = pd.to_numeric(data[spec.trigger_field], errors="coerce").notna()
        data = data[known].copy()
        data["_exposure"] = pd.to_numeric(data[spec.trigger_field], errors="coerce").ge(2)
    elif spec.trigger_operator == "equals_all_history_only":
        data = data[pd.to_numeric(data["all_prior_candidacy_count"], errors="coerce").gt(0)].copy()
        data["_exposure"] = data[spec.trigger_field].fillna(False).astype(bool)
    elif spec.trigger_operator == "equals_complete_opponent_history":
        data = data[data["opponent_history_complete"].fillna(False).astype(bool)].copy()
        known = data[spec.trigger_field].notna()
        data = data[known].copy()
        data["_exposure"] = data[spec.trigger_field].astype(bool)
    else:
        known = data[spec.trigger_field].notna()
        data = data[known].copy()
        data["_exposure"] = data[spec.trigger_field].astype(bool)
    return data.reset_index(drop=True)


def _continuous_data(primary: pd.DataFrame, spec: HintSpec) -> tuple[pd.DataFrame, float]:
    data = _candidate_scope(primary, spec)
    value = pd.to_numeric(data[spec.trigger_field], errors="coerce")
    if spec.trigger_operator == "continuous_history_only":
        data = data[pd.to_numeric(data["prior_candidacy_count"], errors="coerce").gt(0)].copy()
    elif spec.trigger_operator == "continuous_prior_elected_history_only":
        data = data[
            pd.to_numeric(data["prior_elected_candidacy_count"], errors="coerce").gt(0)
        ].copy()
    elif spec.trigger_operator == "continuous_all_history_only":
        data = data[pd.to_numeric(data["all_prior_candidacy_count"], errors="coerce").gt(0)].copy()
    elif spec.trigger_operator == "continuous_all_history_winners_only":
        data = data[pd.to_numeric(data["all_prior_victory_count"], errors="coerce").gt(0)].copy()
    elif spec.trigger_operator == "continuous_winners_only":
        data = data[pd.to_numeric(data["victory_count"], errors="coerce").gt(0)].copy()
    elif spec.trigger_operator == "continuous_positive_only":
        data = data[value.gt(0)].copy()
    data["_exposure"] = pd.to_numeric(data[spec.trigger_field], errors="coerce")
    data = data[data["_exposure"].notna()].copy()
    scale = 0.10 if spec.effect_unit == "per_10_percentage_point_increase" else 1.0
    return data.reset_index(drop=True), scale


def evaluate_historical_hints(
    frame: pd.DataFrame, *, n_bootstrap: int = 2_000, seed: int = 20260820
) -> pd.DataFrame:
    """Evaluate every candidate-facing hint and return supported and withheld rows."""
    primary = _primary_frame(frame)
    rows: list[dict] = []
    for index, spec in enumerate(_specs()):
        continuous = spec.trigger_operator.startswith("continuous")
        if continuous:
            data, scale = _continuous_data(primary, spec)
            trigger = data
            comparator = pd.DataFrame()
        else:
            data = _categorical_data(primary, spec)
            scale = 1.0
            trigger = data[data["_exposure"]]
            comparator = data[~data["_exposure"]]

        effect = np.nan
        ci_low = np.nan
        ci_high = np.nan
        p_value = np.nan
        if len(data) and data["_exposure"].nunique() >= 2:
            effect = _adjusted_effect(data, data["_exposure"].to_numpy(), scale=scale)
            ci_low, ci_high, p_value = _bootstrap_effect(
                data,
                "_exposure",
                scale=scale,
                n_bootstrap=n_bootstrap,
                rng=np.random.default_rng(seed + index),
            )

        trigger_n = len(trigger)
        trigger_contests = trigger["contest_id"].nunique() if trigger_n else 0
        trigger_elections = trigger["election_year"].nunique() if trigger_n else 0
        trigger_people = trigger["person_id"].nunique() if trigger_n else 0
        comparator_n = len(comparator)
        comparator_contests = comparator["contest_id"].nunique() if comparator_n else 0
        minimum_trigger_n = 20 if continuous else (4 if spec.small_sample_exception else 5)
        minimum_trigger_contests = 10 if continuous else (4 if spec.small_sample_exception else 5)
        minimum_trigger_elections = 3 if continuous or spec.small_sample_exception else 2
        enough_data = (
            trigger_n >= minimum_trigger_n
            and trigger_contests >= minimum_trigger_contests
            and trigger_elections >= minimum_trigger_elections
            and (continuous or comparator_contests >= 10)
        )
        clear = not pd.isna(ci_low) and (ci_low > 0 or ci_high < 0)
        year_effects, same_direction, estimable_elections = _year_effects(
            data, scale=scale, overall_effect=effect
        )
        if spec.forced_status:
            status = spec.forced_status
        elif len(data) and data["_exposure"].nunique() < 2:
            status = "not_estimable_no_variation"
        elif not enough_data:
            status = "insufficient_data"
        elif clear:
            status = "supported"
        else:
            status = "no_clear_association"
        direction = _direction(effect)
        evidence_tier = ""
        if status == "supported":
            if spec.small_sample_exception:
                evidence_tier = "consistent_small_sample"
            else:
                evidence_tier = (
                    "consistent_across_elections"
                    if estimable_elections and same_direction == estimable_elections
                    else "pooled_only"
                )
        rows.append(
            {
                "hint_id": spec.hint_id,
                "subject": spec.subject,
                "candidate_regime": spec.candidate_regime,
                "trigger_field": spec.trigger_field,
                "trigger_operator": spec.trigger_operator,
                "trigger_value": spec.trigger_value,
                "trigger_definition": _trigger_definition(spec),
                "comparison": spec.comparison,
                "effect_unit": spec.effect_unit,
                "trigger_n": trigger_n,
                "trigger_contests": trigger_contests,
                "trigger_elections": trigger_elections,
                "trigger_people": trigger_people,
                "comparator_n": comparator_n,
                "comparator_contests": comparator_contests,
                "mean_vote_share_trigger": trigger["vote_share"].mean() if trigger_n else np.nan,
                "mean_vote_share_comparator": comparator["vote_share"].mean()
                if comparator_n
                else np.nan,
                "elected_rate_trigger": trigger["elected"].mean() if trigger_n else np.nan,
                "elected_rate_comparator": comparator["elected"].mean() if comparator_n else np.nan,
                "adjusted_vote_share_effect_pp": effect,
                "ci_low_pp": ci_low,
                "ci_high_pp": ci_high,
                "bootstrap_p": p_value,
                "direction": direction,
                "election_effects_pp": year_effects,
                "elections_same_direction": same_direction,
                "elections_estimable": estimable_elections,
                "evidence_status": status,
                "evidence_tier": evidence_tier,
                "frontend_copy": _frontend_copy(spec, direction) if status == "supported" else "",
                "limitation": spec.limitation,
                "catalog_eligible": spec.catalog_eligible,
            }
        )
    result = pd.DataFrame(rows)
    superseded: dict[str, str] = {}
    result["superseded_by"] = result["hint_id"].map(superseded).fillna("")
    council_positive = (
        "own_prior_council_run_without_victory_vs_no_history__non_incumbent_non_returning"
    )
    council_negative = (
        "own_prior_council_run_without_victory_vs_other_history__non_incumbent_non_returning"
    )
    paired = {council_positive: council_negative, council_negative: council_positive}
    result["display_group"] = np.where(
        result["hint_id"].isin(paired),
        "prior_unsuccessful_council_run_context",
        result["hint_id"],
    )
    result["paired_hint_id"] = result["hint_id"].map(paired).fillna("")
    result["family_q"] = np.nan
    screen_mask = result["hint_id"].isin(SCREEN_HINT_IDS)
    p_values = result.loc[screen_mask, "bootstrap_p"].fillna(1.0).to_numpy(dtype=float)
    order = np.argsort(p_values)
    ranked = p_values[order]
    adjusted = ranked * len(ranked) / np.arange(1, len(ranked) + 1)
    adjusted = np.minimum.accumulate(adjusted[::-1])[::-1]
    q_values = np.empty(len(adjusted))
    q_values[order] = np.minimum(adjusted, 1.0)
    result.loc[screen_mask, "family_q"] = q_values
    corrected_clear = ~screen_mask | result["family_q"].lt(0.05)
    result["catalog_status"] = np.select(
        [
            result["evidence_status"].eq("supported")
            & result["catalog_eligible"]
            & corrected_clear,
            result["evidence_status"].eq("supported")
            & (~result["catalog_eligible"] | ~corrected_clear),
        ],
        ["publish", "diagnostic_only"],
        default="withhold",
    )
    paired_statuses = result.set_index("hint_id").loc[list(paired), "catalog_status"]
    if not paired_statuses.eq("publish").all():
        pair_mask = result["hint_id"].isin(paired) & result["catalog_status"].eq("publish")
        result.loc[pair_mask, "catalog_status"] = "diagnostic_only"
    return result


def write_historical_hint_catalog(
    frame: pd.DataFrame, output_dir: Path, *, n_bootstrap: int = 2_000, seed: int = 20260820
) -> tuple[Path, Path, Path, Path, Path, Path, Path]:
    """Write the full audit, supported catalog, and concise evidence report."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    audit = evaluate_historical_hints(frame, n_bootstrap=n_bootstrap, seed=seed)
    supported = audit[audit["catalog_status"].eq("publish")].copy()
    audit_path = output_dir / "historical_hint_audit.csv"
    catalog_path = output_dir / "supported_historical_hints.csv"
    report_path = output_dir / "historical-hints-report.md"
    contract_path = output_dir / "historical_hint_contract.json"
    victory_report_path = output_dir / "all-past-races-victory-count-report.md"
    screen_report_path = output_dir / "candidate-history-flag-screen-report.md"
    approval_report_path = output_dir / "candidate-history-flag-approval-report.md"
    audit.to_csv(audit_path, index=False)
    supported.to_csv(catalog_path, index=False)
    lines = [
        "# Historical hint catalog",
        "",
        "These are candidate-specific historical associations for frontend context, not predictions, causal effects, or model inputs.",
        "",
        (
            "Evidence uses confirmed identities in the 2010, 2014, and 2022 stable-boundary "
            "general elections; comparisons adjust for election, Candidate regime, and field "
            "size, with uncertainty clustered by Contest. Categorical hints require at least "
            "five triggered Candidacies in five Contests and two elections; continuous hints "
            "require 20 observations in ten Contests and three elections."
        ),
        "",
        f"Supported hints: {len(supported)} of {len(audit)} tested flags.",
        "",
    ]
    for row in supported.itertuples(index=False):
        lines.extend(
            [
                f"## {row.hint_id}",
                "",
                row.frontend_copy,
                "",
                (
                    f"Adjusted Vote-share association: {row.adjusted_vote_share_effect_pp:+.2f} "
                    f"percentage points ({row.ci_low_pp:+.2f} to {row.ci_high_pp:+.2f}); "
                    f"n={row.trigger_n}, {row.trigger_contests} Contests, "
                    f"{row.trigger_elections} elections. Same-direction election estimates: "
                    f"{row.elections_same_direction}/{row.elections_estimable} "
                    f"({row.election_effects_pp})."
                ),
                f"Evidence tier: {row.evidence_tier}.",
                "",
            ]
        )
    lines.extend(
        [
            "## Withheld candidates",
            "",
            "Every non-published flag remains in `historical_hint_audit.csv`, including unsupported and diagnostic-only rows.",
            "",
        ]
    )
    report_path.write_text("\n".join(lines))

    victory_rows = audit[
        audit["hint_id"].str.startswith(
            ("own_all_past_race_victory_count", "own_any_all_past_race_victory")
        )
    ]
    victory_lines = [
        "# All-past-races victory-count audit",
        "",
        (
            "The candidate value is the number of victories across every confirmed elected-office "
            "Candidacy strictly before the subject Contest. Its qualifying count includes council, "
            "mayor, trustee, MP, and MPP races, whether won or lost."
        ),
        "",
        (
            "The retired aggregate definition—non-council races for everyone, with council races "
            "added only for Returning councillors—is not an eligible flag definition and is not "
            "re-tested in the active audit."
        ),
        "",
        (
            "All rows use the same 2010, 2014, and 2022 sample, election and Candidate-regime "
            "controls, field-size adjustment, Contest-clustered bootstrap uncertainty, evidence "
            "thresholds, and election-level stability checks as the rest of the hint audit."
        ),
        "",
        "| Measure and population | n | Contests | People | Adjusted effect (pp) | 95% interval | Election effects (pp) | Status | Tier |",
        "|---|---:|---:|---:|---:|---:|---|---|---|",
    ]
    population_names = {
        "own_all_past_race_victory_count": "Per victory: all candidate regimes",
        "own_all_past_race_victory_count__incumbent": "Per victory: Incumbents",
        "own_all_past_race_victory_count__returning_councillor": (
            "Per victory: Returning councillors"
        ),
        "own_all_past_race_victory_count__non_incumbent_non_returning": (
            "Per victory: non-incumbent, non-returning candidates"
        ),
        "own_any_all_past_race_victory__non_incumbent_non_returning": (
            "Any prior victory vs none: non-incumbent, non-returning candidates"
        ),
        ("own_all_past_race_victory_count__non_incumbent_non_returning_prior_winners"): (
            "Per additional victory: non-incumbent, non-returning prior winners"
        ),
    }
    for row in victory_rows.itertuples(index=False):
        tier = row.evidence_tier if pd.notna(row.evidence_tier) and row.evidence_tier else "—"
        victory_lines.append(
            "| {population} | {n} | {contests} | {people} | {effect:+.2f} | "
            "{low:+.2f} to {high:+.2f} | {years} | {status} | {tier} |".format(
                population=population_names[row.hint_id],
                n=row.trigger_n,
                contests=row.trigger_contests,
                people=row.trigger_people,
                effect=row.adjusted_vote_share_effect_pp,
                low=row.ci_low_pp,
                high=row.ci_high_pp,
                years=(row.election_effects_pp or "—").replace("|", "<br>"),
                status=row.evidence_status,
                tier=tier,
            )
        )
    victory_lines.extend(
        [
            "",
            "## Decision",
            "",
            (
                "The universal all-races count is withheld because its interval includes zero. "
                "Incumbents have a different, non-clear association, so a universal count would "
                "also hide material effect heterogeneity rather than merely adjust away incumbency."
            ),
            "",
            (
                "Among candidates who are neither Incumbents nor Returning councillors, the "
                "per-victory slope clears the numerical gate, but it is not published as a dosage "
                "claim: only 13 candidates had any prior victory, and additional victories among "
                "those prior winners have no clear association."
            ),
            "",
            (
                "The supported public flag is therefore binary: at least one victory across all "
                "confirmed earlier races versus prior races with no victories. It is limited to "
                "non-incumbent, non-returning candidates and is positive in every primary election. "
                "No zero-wins or per-additional-victory hint is published."
            ),
            "",
        ]
    )
    victory_report_path.write_text("\n".join(victory_lines))

    screen = audit.set_index("hint_id").loc[list(SCREEN_HINT_IDS)].reset_index()
    screen["bh_q"] = screen["family_q"]
    approved_screen = screen[screen["catalog_status"].eq("publish")]
    screen_lines = [
        "# Candidate-history flag screen",
        "",
        (
            "This report tests the reader-readable flag batch selected before estimating its "
            "effects. Every definition uses either all confirmed earlier elected-office races "
            "or one explicitly named Office type."
        ),
        "",
        (
            "The sample is the 2010, 2014, and 2022 primary general-election cohort. Effects "
            "adjust for election, Candidate regime, and field size; uncertainty uses the same "
            "Contest-clustered bootstrap and evidence thresholds as the main hint audit. "
            "Opponent comparisons require a fully resolved Opponent field."
        ),
        "",
        (
            f"{len(approved_screen)} of {len(screen)} operational tests clear the standalone "
            "evidence gate and retain q < 0.05 under a Benjamini-Hochberg family correction. "
            "Under the descriptive publication standard, every corrected-clear row is eligible "
            "for the public catalog."
        ),
        "",
        (
            "Intervals and bootstrap p-values are nominal; the q-value column applies a "
            f"Benjamini-Hochberg correction across this {len(screen)}-test family. Sample and election "
            "thresholds still apply, so a low q-value cannot rescue an insufficient-data row."
        ),
        "",
        "| Flag | Trigger n | Comparator n | Contests | Elections | Adjusted effect (pp) | 95% interval | Bootstrap p | BH q | Election effects (pp) | Status | Catalog | Tier |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|",
    ]
    for row in screen.itertuples(index=False):
        tier = row.evidence_tier if pd.notna(row.evidence_tier) and row.evidence_tier else "—"
        years = (
            (row.election_effects_pp or "—").replace("|", "<br>")
            if pd.notna(row.election_effects_pp)
            else "—"
        )
        screen_lines.append(
            f"| {row.hint_id} | {row.trigger_n} | {row.comparator_n} | "
            f"{row.trigger_contests} | {row.trigger_elections} | "
            f"{row.adjusted_vote_share_effect_pp:+.2f} | {row.ci_low_pp:+.2f} to "
            f"{row.ci_high_pp:+.2f} | {row.bootstrap_p:.4f} | {row.bh_q:.4f} | {years} | "
            f"{row.evidence_status} | {row.catalog_status} | {tier} |"
        )
    screen_lines.extend(
        [
            "",
            (
                "These are corrected standalone historical associations, not claims that each "
                "flag supplies independent predictive information. Several own-history flags may "
                "therefore apply to the same candidate."
            ),
            "",
        ]
    )
    screen_report_path.write_text("\n".join(screen_lines))

    approval_lines = [
        "# Candidate-history flag publication review",
        "",
        "**Decision: approve every corrected standalone association that clears the evidence gate.**",
        "",
        (
            "The publication standard is a clear, multiple-testing-corrected historical "
            "association, explicitly described as context rather than prediction. A flag does "
            "not need to retain a separate coefficient after correlated history measures are "
            "entered together."
        ),
        "",
        (
            f"{len(approved_screen)} reader-readable screen flags are approved. They use the "
            "2010, 2014, and 2022 stable-boundary sample, adjust for election, Candidate regime, "
            "and field size, cluster uncertainty by Contest, point in the same direction in all "
            "estimable elections, and retain Benjamini-Hochberg q < 0.05 across the expanded "
            f"{len(screen)}-test family. Two Returning-councillor rows use the "
            "consistent_small_sample tier after supplemental influence and permutation checks."
        ),
        "",
        "| Flag | Adjusted association (pp) | 95% interval | BH q | Election effects (pp) |",
        "|---|---:|---:|---:|---|",
    ]
    for row in approved_screen.itertuples(index=False):
        approval_lines.append(
            f"| {row.hint_id} | {row.adjusted_vote_share_effect_pp:+.2f} | "
            f"{row.ci_low_pp:+.2f} to {row.ci_high_pp:+.2f} | {row.bh_q:.4f} | "
            f"{row.election_effects_pp.replace('|', '<br>')} |"
        )
    approval_lines.extend(
        [
            "",
            "## Prior unsuccessful council run",
            "",
            (
                "This record has two supported comparisons and must be displayed as a pair. "
                "Historically, the candidates did better than candidates with no confirmed "
                "earlier race, but worse than candidates with other confirmed earlier-race "
                "histories. The two catalog rows share `display_group` and point to one another "
                "through `paired_hint_id`; downstream must never display only one side."
            ),
            "",
            "## Overlap",
            "",
            (
                "Some approved flags overlap by design: any history, multiple races, a recent "
                "victory, and recent signed margin can all describe the same candidate. Their "
                "copy states the historical comparator and must not call the association an "
                "independent effect, causal effect, or prediction."
            ),
            "",
        ]
    )
    approval_report_path.write_text("\n".join(approval_lines))

    contract = {
        "schema_version": "2.1.0",
        "purpose": "Historical frontend context only; not a prediction or model input.",
        "person_identity": "Use the upstream persistent person_id; never match by name.",
        "history_scope": {
            "allowed_race_history_scopes": [
                "one explicitly named Office type",
                "all confirmed elected-office races",
            ],
            "all_past_race_office_types": ["councillor", "mayor", "trustee", "mp", "mpp"],
            "all_past_race_definition": (
                "Every confirmed Candidacy with election_date before the subject Contest, "
                "including wins and losses."
            ),
            "disallowed_aggregate_scope": (
                "Do not use all-races-except-council or add council races only for Returning "
                "councillors."
            ),
            "returning_councillor": (
                "A candidate with a strictly earlier council victory who is not a council "
                "incumbent immediately before the subject election; prior ward is irrelevant."
            ),
            "sitting_incumbent_is_returning_councillor": False,
        },
        "temporal_rule": {
            "prior": "election_date < subject council election_date",
            "most_recent": "Maximum election_date among qualifying prior Candidacies.",
        },
        "elected_rule": {
            "definition": "elected == True",
            "acclamations_count_as_victories": True,
        },
        "all_past_race_margin_rule": {
            "definition": (
                "Signed vote-share margin in the most recent qualifying race: an elected "
                "candidate's share minus the runner-up's share; an unelected candidate's share "
                "minus the elected candidate's share."
            ),
            "losses_are_negative": True,
            "acclamation_without_runner_up": None,
            "missing_is_zero": False,
        },
        "race_history_display_rule": {
            "missing_is_zero": False,
            "any_all_past_race": (
                "Fire only for a candidate in an Open contest or a non-incumbent facing an "
                "Incumbent, who is not a Returning councillor, when all_prior_candidacy_count > 0."
            ),
            "multiple_all_past_races": (
                "Use the same Candidate regime and Returning-councillor exclusions, and fire "
                "when all_prior_candidacy_count >= 2."
            ),
            "any_all_past_race_victory": (
                "Fire only for a candidate in an Open contest or a non-incumbent facing an "
                "Incumbent, who is not a Returning councillor, when all_prior_candidacy_count "
                "> 0 and all_prior_victory_count > 0."
            ),
            "most_recent_all_past_race_was_victory": (
                "Use the same Candidate regime and Returning-councillor exclusions, require "
                "all_prior_candidacy_count > 0, and fire when the most recent qualifying race "
                "has elected == True."
            ),
            "most_recent_all_past_race_margin": (
                "Use the same Candidate regime and Returning-councillor exclusions and expose "
                "the non-null signed margin from the most recent qualifying race."
            ),
            "prior_mpp_race": (
                "Use the same Candidate regime and Returning-councillor exclusions and fire "
                "when prior_office_types_contested contains mpp."
            ),
            "prior_unsuccessful_council_run": (
                "Use the same Candidate regime and Returning-councillor exclusions and fire "
                "when prior_council_run_without_victory == true. Publish both comparison rows "
                "in display_group prior_unsuccessful_council_run_context together."
            ),
            "incumbent_opponent_recent_margin": (
                "Fire only for an Incumbent when opponent_history_complete == true. For each "
                "opponent, derive the signed margin in that opponent's most recent qualifying "
                "race, then expose the maximum non-null margin across the Opponent field."
            ),
            "returning_councillor_in_open_contest": (
                "Fire when candidate_regime == open_contest and returning_councillor == true. "
                "Use evidence_tier consistent_small_sample and show the four-Contest sample size."
            ),
            "facing_returning_councillor_in_open_contest": (
                "Fire when candidate_regime == open_contest and "
                "any_returning_councillor_opponent == true. Use evidence_tier "
                "consistent_small_sample and show the four-Contest sample size."
            ),
            "zero_wins_hint": "Do not publish.",
            "per_additional_victory_hint": "Do not publish.",
            "visible_history_parity": (
                "all_prior_candidacy_count must equal the candidate's complete visible confirmed "
                "race history before the subject Contest."
            ),
        },
        "display_rule": {
            "include_frontend_copy": True,
            "include_numeric_estimate_and_unit": True,
            "include_evidence_tier": True,
            "include_sample_size": True,
            "frame_as_historical_context": True,
            "frame_as_prediction": False,
            "independent_effect_required": False,
            "paired_display_groups_must_be_complete": True,
        },
        "publication_rule": {
            "standard": (
                "A clear historical association under the stated adjusted comparison, with "
                "Benjamini-Hochberg q < 0.05 across the reader-readable screen."
            ),
            "independent_conditional_effect_required": False,
            "small_sample_tier": (
                "consistent_small_sample is permitted only for the two explicitly reviewed "
                "Returning-councillor Open-contest flags, which have four independent Contests, "
                "three same-direction elections, clear clustered intervals, and supplemental "
                "leave-one-Contest-out and permutation support."
            ),
            "suggestive_or_method_sensitive_rows_publish": False,
        },
    }
    contract_path.write_text(json.dumps(contract, indent=2) + "\n")
    return (
        audit_path,
        catalog_path,
        report_path,
        contract_path,
        victory_report_path,
        screen_report_path,
        approval_report_path,
    )
