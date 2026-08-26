"""Evaluate candidate-level own-history and Opponent-field history signal."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .analysis import auc

BASELINE_NUMERIC = ["election_year", "n_candidates"]
BASELINE_CATEGORICAL = ["candidate_regime"]
SIMPLE_NUMERIC = [
    *BASELINE_NUMERIC,
    "most_recent_prior_margin",
    "strongest_opponent_prior_margin",
]
SIMPLE_CATEGORICAL = [
    *BASELINE_CATEGORICAL,
    "career_record",
    "any_prior_officeholder_opponent",
]
FULL_NUMERIC = [
    *SIMPLE_NUMERIC,
    "prior_candidacy_count",
    "victory_count",
    "prior_loss_count",
    "office_breadth",
    "best_prior_margin",
    "mean_prior_win_margin",
    "years_since_last_run",
    "years_since_last_win",
    "prior_officeholder_opponent_count",
    "prior_officeholder_opponent_share",
    "max_opponent_victory_count",
    "total_opponent_victory_count",
]
FULL_CATEGORICAL = [
    *SIMPLE_CATEGORICAL,
    "current_other_officeholder",
    "prior_office_types_contested",
    "prior_office_types_won",
    "opponent_office_types",
    "any_current_other_officeholder_opponent",
    "any_incumbent_opponent",
]


@dataclass(frozen=True)
class StudyResults:
    """Structured outputs from the candidate-history study seam."""

    model_performance: pd.DataFrame
    simple_evidence: dict
    oof_predictions: pd.DataFrame
    career_summary: pd.DataFrame
    sensitivity_performance: pd.DataFrame
    feature_effects: pd.DataFrame
    flexible_importance: pd.DataFrame


def _transform(numeric: list[str], categorical: list[str], *, dense: bool = False):
    transform = ColumnTransformer(
        [
            (
                "numeric",
                make_pipeline(SimpleImputer(strategy="median"), StandardScaler()),
                numeric,
            ),
            (
                "categorical",
                make_pipeline(
                    SimpleImputer(strategy="most_frequent"),
                    OneHotEncoder(handle_unknown="ignore", sparse_output=not dense),
                ),
                categorical,
            ),
        ]
    )
    return transform


def _regressor(numeric: list[str], categorical: list[str], *, flexible: bool = False):
    if flexible:
        return make_pipeline(
            _transform(numeric, categorical, dense=True),
            HistGradientBoostingRegressor(
                max_iter=150, max_leaf_nodes=7, min_samples_leaf=5, l2_regularization=1.0
            ),
        )
    return make_pipeline(_transform(numeric, categorical), Ridge(alpha=1.0))


def _classifier(numeric: list[str], categorical: list[str], *, flexible: bool = False):
    if flexible:
        return make_pipeline(
            _transform(numeric, categorical, dense=True),
            HistGradientBoostingClassifier(
                max_iter=150, max_leaf_nodes=7, min_samples_leaf=5, l2_regularization=1.0
            ),
        )
    return make_pipeline(
        _transform(numeric, categorical), LogisticRegression(max_iter=1_000, C=1.0)
    )


def _oof_predict(
    frame: pd.DataFrame,
    numeric: list[str],
    categorical: list[str],
    *,
    flexible: bool = False,
) -> np.ndarray:
    predictions = np.full(len(frame), np.nan)
    years = frame["election_year"].to_numpy()
    y = frame["vote_share"].to_numpy(dtype=float)
    for held_out in sorted(frame["election_year"].unique()):
        test = years == held_out
        train = ~test
        model = _regressor(numeric, categorical, flexible=flexible)
        model.fit(frame.loc[train], y[train])
        predictions[test] = model.predict(frame.loc[test])
    return predictions


def _oof_probability(
    frame: pd.DataFrame,
    numeric: list[str],
    categorical: list[str],
    *,
    flexible: bool = False,
) -> np.ndarray:
    probabilities = np.full(len(frame), np.nan)
    years = frame["election_year"].to_numpy()
    y = frame["elected"].astype(bool).to_numpy(dtype=int)
    for held_out in sorted(frame["election_year"].unique()):
        test = years == held_out
        train = ~test
        if len(np.unique(y[train])) < 2:
            probabilities[test] = y[train].mean()
            continue
        model = _classifier(numeric, categorical, flexible=flexible)
        model.fit(frame.loc[train], y[train])
        probabilities[test] = model.predict_proba(frame.loc[test])[:, 1]
    return probabilities


def _rmse(actual, predicted) -> float:
    return float(np.sqrt(np.mean((np.asarray(actual) - np.asarray(predicted)) ** 2)))


def _r2(actual, predicted) -> float:
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    denominator = ((actual - actual.mean()) ** 2).sum()
    return float(1 - ((actual - predicted) ** 2).sum() / denominator)


def _binary_metrics(actual, probability) -> dict:
    actual = np.asarray(actual, dtype=int)
    probability = np.clip(np.asarray(probability, dtype=float), 1e-9, 1 - 1e-9)
    return {
        "cv_brier": float(np.mean((actual - probability) ** 2)),
        "cv_log_loss": float(
            -np.mean(actual * np.log(probability) + (1 - actual) * np.log(1 - probability))
        ),
        "cv_auc": auc(probability, actual),
    }


def _permuted_outcomes(predictions: pd.DataFrame, rng: np.random.Generator) -> np.ndarray:
    """Permute candidate Vote shares within each Contest, preserving every field total."""
    outcome = predictions["vote_share"].to_numpy(copy=True)
    for indices in predictions.groupby("contest_id", sort=False).indices.values():
        outcome[indices] = rng.permutation(outcome[indices])
    return outcome


def _clustered_delta_ci(
    predictions: pd.DataFrame, *, n_bootstrap: int, rng: np.random.Generator
) -> tuple[float, float]:
    contests = predictions["contest_id"].drop_duplicates().to_numpy()
    deltas = []
    for _ in range(n_bootstrap):
        sampled = rng.choice(contests, len(contests), replace=True)
        pieces = [predictions[predictions["contest_id"].eq(contest)] for contest in sampled]
        boot = pd.concat(pieces, ignore_index=True)
        deltas.append(
            _rmse(boot["vote_share"], boot["baseline_prediction"])
            - _rmse(boot["vote_share"], boot["simple_history_prediction"])
        )
    return tuple(float(x) for x in np.percentile(deltas, [2.5, 97.5]))


def _career_summary(frame: pd.DataFrame) -> pd.DataFrame:
    return (
        frame.groupby("career_record", dropna=False)
        .agg(
            candidacies=("candidacy_id", "size"),
            mean_vote_share=("vote_share", "mean"),
            elected_rate=("elected", "mean"),
        )
        .reset_index()
    )


def _scope_performance(frame: pd.DataFrame, scope: str) -> pd.DataFrame:
    if frame.empty or frame["election_year"].nunique() < 2:
        return pd.DataFrame()
    actual = frame["vote_share"].to_numpy(dtype=float)
    elected = frame["elected"].astype(bool).to_numpy(dtype=int)
    rows = []
    for name, numeric, categorical in [
        ("baseline", BASELINE_NUMERIC, BASELINE_CATEGORICAL),
        ("simple_history", SIMPLE_NUMERIC, SIMPLE_CATEGORICAL),
    ]:
        prediction = _oof_predict(frame, numeric, categorical)
        probability = _oof_probability(frame, numeric, categorical)
        rows.append(
            {
                "scope": scope,
                "model": name,
                "n": len(frame),
                "cv_rmse": _rmse(actual, prediction),
                "cv_r2": _r2(actual, prediction),
                **_binary_metrics(elected, probability),
            }
        )
    return pd.DataFrame(rows)


def _regularized_effects(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    years = frame["election_year"].to_numpy()
    y = frame["vote_share"].to_numpy(dtype=float)
    for held_out in sorted(frame["election_year"].unique()):
        train = years != held_out
        model = _regressor(FULL_NUMERIC, FULL_CATEGORICAL)
        model.fit(frame.loc[train], y[train])
        transform = model.named_steps["columntransformer"]
        fitted = model.named_steps["ridge"]
        for feature, coefficient in zip(transform.get_feature_names_out(), fitted.coef_):
            rows.append(
                {
                    "held_out_year": held_out,
                    "feature": feature,
                    "coefficient": float(coefficient),
                }
            )
    folds = pd.DataFrame(rows)
    summary = (
        folds.groupby("feature")
        .agg(
            mean_coefficient=("coefficient", "mean"),
            min_coefficient=("coefficient", "min"),
            max_coefficient=("coefficient", "max"),
            folds=("coefficient", "size"),
        )
        .reset_index()
    )
    signs = folds.merge(summary[["feature", "mean_coefficient"]], on="feature")
    signs["same_direction"] = np.sign(signs["coefficient"]) == np.sign(signs["mean_coefficient"])
    stability = signs.groupby("feature")["same_direction"].mean()
    summary["direction_stability"] = summary["feature"].map(stability)
    summary["absolute_mean_coefficient"] = summary["mean_coefficient"].abs()
    return summary.sort_values("absolute_mean_coefficient", ascending=False).reset_index(drop=True)


def _flexible_importance(frame: pd.DataFrame, *, seed: int) -> pd.DataFrame:
    features = list(dict.fromkeys([*FULL_NUMERIC, *FULL_CATEGORICAL]))
    years = frame["election_year"].to_numpy()
    y = frame["vote_share"].to_numpy(dtype=float)
    rows = []
    for held_out in sorted(frame["election_year"].unique()):
        test = years == held_out
        train = ~test
        model = _regressor(FULL_NUMERIC, FULL_CATEGORICAL, flexible=True)
        model.fit(frame.loc[train, features], y[train])
        importance = permutation_importance(
            model,
            frame.loc[test, features],
            y[test],
            scoring="neg_root_mean_squared_error",
            n_repeats=5,
            random_state=seed + int(held_out),
        )
        for feature, value in zip(features, importance.importances_mean):
            rows.append(
                {
                    "held_out_year": held_out,
                    "feature": feature,
                    "rmse_importance": float(value),
                }
            )
    folds = pd.DataFrame(rows)
    return (
        folds.groupby("feature")
        .agg(
            mean_rmse_importance=("rmse_importance", "mean"),
            min_rmse_importance=("rmse_importance", "min"),
            max_rmse_importance=("rmse_importance", "max"),
        )
        .reset_index()
        .sort_values("mean_rmse_importance", ascending=False)
        .reset_index(drop=True)
    )


def evaluate_candidate_history(
    frame: pd.DataFrame,
    *,
    n_permutations: int = 999,
    n_bootstrap: int = 2_000,
    seed: int = 0,
) -> StudyResults:
    """Run the pre-specified, stable-boundary candidate-history evidence test."""
    required = {
        "candidacy_id",
        "contest_id",
        "election_year",
        "election_type",
        "vote_share",
        "elected",
        *BASELINE_NUMERIC,
        *BASELINE_CATEGORICAL,
        *SIMPLE_NUMERIC,
        *SIMPLE_CATEGORICAL,
        *FULL_NUMERIC,
        *FULL_CATEGORICAL,
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"candidate-history frame missing columns: {sorted(missing)}")

    analysis_frame = frame[frame["vote_share"].notna()].copy()
    analysis_frame["career_record"] = analysis_frame["career_record"].fillna("identity_unresolved")
    analysis_frame["any_prior_officeholder_opponent"] = analysis_frame[
        "any_prior_officeholder_opponent"
    ].fillna(False)
    for column in FULL_NUMERIC:
        analysis_frame[column] = pd.to_numeric(analysis_frame[column], errors="coerce")
    for column in FULL_CATEGORICAL:
        analysis_frame[column] = (
            analysis_frame[column].astype("string").fillna("unknown").astype(str)
        )
    analysis_frame = analysis_frame.reset_index(drop=True)

    primary = analysis_frame[
        analysis_frame["election_type"].eq("general")
        & analysis_frame["election_year"].ge(2010)
        & ~analysis_frame["election_year"].eq(2018)
    ].reset_index(drop=True)
    if primary["election_year"].nunique() < 2:
        raise ValueError("candidate-history evidence test needs at least two election years")

    specifications = {
        "baseline": (BASELINE_NUMERIC, BASELINE_CATEGORICAL, False),
        "simple_history": (SIMPLE_NUMERIC, SIMPLE_CATEGORICAL, False),
        "full_history": (FULL_NUMERIC, FULL_CATEGORICAL, False),
        "flexible_history": (FULL_NUMERIC, FULL_CATEGORICAL, True),
    }
    regression_predictions = {
        name: _oof_predict(primary, numeric, categorical, flexible=flexible)
        for name, (numeric, categorical, flexible) in specifications.items()
    }
    probabilities = {
        name: _oof_probability(primary, numeric, categorical, flexible=flexible)
        for name, (numeric, categorical, flexible) in specifications.items()
    }
    baseline = regression_predictions["baseline"]
    simple = regression_predictions["simple_history"]
    actual = primary["vote_share"].to_numpy(dtype=float)
    baseline_rmse = _rmse(actual, baseline)
    simple_rmse = _rmse(actual, simple)
    observed_delta = baseline_rmse - simple_rmse

    predictions = primary[
        ["candidacy_id", "contest_id", "election_year", "vote_share", "elected"]
    ].copy()
    predictions["baseline_prediction"] = baseline
    predictions["simple_history_prediction"] = simple
    predictions["full_history_prediction"] = regression_predictions["full_history"]
    predictions["flexible_history_prediction"] = regression_predictions["flexible_history"]
    for name, probability in probabilities.items():
        predictions[f"{name}_elected_probability"] = probability

    rng = np.random.default_rng(seed)
    null_deltas = []
    for _ in range(n_permutations):
        permuted = _permuted_outcomes(predictions, rng)
        null_deltas.append(_rmse(permuted, baseline) - _rmse(permuted, simple))
    permutation_p = (1 + np.sum(np.asarray(null_deltas) >= observed_delta)) / (n_permutations + 1)

    ci_low, ci_high = _clustered_delta_ci(
        predictions, n_bootstrap=n_bootstrap, rng=np.random.default_rng(seed + 1)
    )
    yearly = predictions.groupby("election_year").apply(
        lambda part: (
            _rmse(part["vote_share"], part["baseline_prediction"])
            - _rmse(part["vote_share"], part["simple_history_prediction"])
        ),
        include_groups=False,
    )
    direction_stable = bool((yearly > 0).all())
    supported = observed_delta > 0 and permutation_p <= 0.05 and ci_low > 0

    elected = primary["elected"].astype(bool).to_numpy(dtype=int)
    performance = pd.DataFrame(
        [
            {
                "model": name,
                "n": len(primary),
                "cv_rmse": _rmse(actual, regression_predictions[name]),
                "cv_r2": _r2(actual, regression_predictions[name]),
                **_binary_metrics(elected, probabilities[name]),
            }
            for name in specifications
        ]
    )
    evidence = {
        "delta_rmse": observed_delta,
        "delta_rmse_ci_low": ci_low,
        "delta_rmse_ci_high": ci_high,
        "permutation_p": float(permutation_p),
        "direction_stable": direction_stable,
        "status": "supported_signal" if supported else "no_detected_signal",
    }
    sensitivity_parts = [
        _scope_performance(primary, "primary_2010_plus_stable_boundary"),
        _scope_performance(
            analysis_frame[
                analysis_frame["election_type"].eq("general")
                & analysis_frame["election_year"].ge(2006)
                & ~analysis_frame["election_year"].eq(2018)
            ].reset_index(drop=True),
            "stable_boundary_including_2006",
        ),
        _scope_performance(
            analysis_frame[
                analysis_frame["election_type"].eq("general")
                & analysis_frame["election_year"].ge(2006)
            ].reset_index(drop=True),
            "all_general_including_2006_2018",
        ),
        _scope_performance(
            analysis_frame[analysis_frame["election_type"].eq("by_election")].reset_index(
                drop=True
            ),
            "by_elections",
        ),
    ]
    sensitivity = pd.concat(
        [part for part in sensitivity_parts if not part.empty], ignore_index=True
    )
    return StudyResults(
        model_performance=performance,
        simple_evidence=evidence,
        oof_predictions=predictions,
        career_summary=_career_summary(primary),
        sensitivity_performance=sensitivity,
        feature_effects=_regularized_effects(primary),
        flexible_importance=_flexible_importance(primary, seed=seed),
    )
