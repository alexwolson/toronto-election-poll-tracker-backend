"""Evaluate whether each exact Endorser's positive edges track electoral success."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

MIN_CLEAR_CONTESTS = 10
MIN_CLEAR_ELECTIONS = 2


@dataclass(frozen=True)
class EndorsementArtifacts:
    """Files written by the endorsement association study."""

    observations: Path
    associations: Path
    report: Path

    def paths(self) -> tuple[Path, ...]:
        return self.observations, self.associations, self.report


def _incumbency_class(series: pd.Series) -> pd.Series:
    values = series.astype("boolean")
    return pd.Series(
        np.select(
            [values.eq(True).fillna(False), values.eq(False).fillna(False)],
            ["incumbent", "not_incumbent"],
            default="unknown",
        ),
        index=series.index,
        dtype="string",
    )


def build_endorsement_observations(
    results: pd.DataFrame,
    endorsements: pd.DataFrame,
    endorsers: pd.DataFrame,
    assertions: pd.DataFrame,
    coverage: pd.DataFrame,
) -> pd.DataFrame:
    """Join every confirmed Endorsement to its result and within-Contest baselines."""
    results = results.copy()
    results["incumbency_class"] = _incumbency_class(results["incumbent"])
    final = results[
        results["result_status"].eq("final")
        & results["vote_share"].notna()
        & results["elected"].notna()
    ].copy()
    final["elected"] = final["elected"].astype(bool)

    confirmed = assertions[assertions["review_state"].eq("confirmed")].copy()
    confirmed["announcement_date"] = pd.to_datetime(confirmed["announcement_date"], errors="coerce")
    assertion_summary = (
        confirmed.groupby("endorsement_id", as_index=False)
        .agg(
            announcement_date=("announcement_date", "min"),
            endorsement_kind=("endorsement_kind", lambda values: "|".join(sorted(set(values)))),
            source_type=("source_type", lambda values: "|".join(sorted(set(values)))),
        )
        .reset_index(drop=True)
    )

    edge = (
        endorsements.merge(
            endorsers[["endorser_id", "canonical_name", "endorser_type", "is_panel_endorser"]],
            on="endorser_id",
            how="left",
            validate="many_to_one",
        )
        .merge(
            final,
            on=["contest_id", "candidacy_id"],
            how="inner",
            validate="many_to_one",
        )
        .merge(assertion_summary, on="endorsement_id", how="left", validate="one_to_one")
        .merge(
            coverage[["endorser_id", "contest_id", "coverage_state"]],
            on=["endorser_id", "contest_id"],
            how="left",
            validate="many_to_one",
        )
    )
    edge["election_date"] = pd.to_datetime(edge["election_date"])
    edge["days_before_election"] = (edge["election_date"] - edge["announcement_date"]).dt.days
    edge["analysis_eligible"] = edge["coverage_state"].eq("comprehensive_source_found")

    if edge.empty:
        return edge

    field = final[final["contest_id"].isin(edge["contest_id"])].copy()
    field_summary = (
        field.groupby("contest_id", as_index=False)
        .agg(
            field_candidates=("candidacy_id", "size"),
            field_expected_win=("elected", "mean"),
            field_expected_vote_share=("vote_share", "mean"),
        )
        .reset_index(drop=True)
    )
    role_summary = (
        field.groupby(["contest_id", "incumbency_class"], as_index=False)
        .agg(
            role_pool_candidates=("candidacy_id", "size"),
            role_expected_win=("elected", "mean"),
            role_expected_vote_share=("vote_share", "mean"),
        )
        .reset_index(drop=True)
    )
    edge = edge.merge(field_summary, on="contest_id", how="left", validate="many_to_one")
    edge = edge.merge(
        role_summary,
        on=["contest_id", "incumbency_class"],
        how="left",
        validate="many_to_one",
    )

    endorsement_counts = (
        edge.groupby(["endorser_id", "contest_id"], as_index=False)
        .agg(field_endorsed_count=("candidacy_id", "size"))
        .reset_index(drop=True)
    )
    role_endorsement_counts = (
        edge.groupby(["endorser_id", "contest_id", "incumbency_class"], as_index=False)
        .agg(role_endorsed_count=("candidacy_id", "size"))
        .reset_index(drop=True)
    )
    edge = edge.merge(
        endorsement_counts,
        on=["endorser_id", "contest_id"],
        how="left",
        validate="many_to_one",
    ).merge(
        role_endorsement_counts,
        on=["endorser_id", "contest_id", "incumbency_class"],
        how="left",
        validate="many_to_one",
    )
    edge["field_informative"] = edge["field_candidates"].gt(edge["field_endorsed_count"])
    edge["role_informative"] = edge["role_pool_candidates"].gt(edge["role_endorsed_count"])
    edge["field_win_lift"] = edge["elected"].astype(float) - edge["field_expected_win"]
    edge["field_vote_share_lift"] = edge["vote_share"] - edge["field_expected_vote_share"]
    edge["role_win_lift"] = edge["elected"].astype(float) - edge["role_expected_win"]
    edge["role_vote_share_lift"] = edge["vote_share"] - edge["role_expected_vote_share"]

    coendorsements = endorsements.groupby("candidacy_id").size()
    edge["panel_endorsements_for_candidate"] = edge["candidacy_id"].map(coendorsements).astype(int)
    edge["endorsed_person_key"] = edge["person_id"].fillna(edge["candidacy_id"])

    other_max = (
        field[["contest_id", "candidacy_id", "vote_share"]]
        .merge(
            edge[["endorsement_id", "contest_id", "candidacy_id"]].rename(
                columns={"candidacy_id": "endorsed_candidacy_id"}
            ),
            on="contest_id",
            how="inner",
        )
        .loc[lambda data: ~data["candidacy_id"].eq(data["endorsed_candidacy_id"])]
        .groupby("endorsement_id")["vote_share"]
        .max()
    )
    edge["strongest_other_vote_share"] = edge["endorsement_id"].map(other_max)
    edge["signed_margin_over_strongest_other"] = (
        edge["vote_share"] - edge["strongest_other_vote_share"]
    )

    columns = [
        "endorsement_id",
        "endorser_id",
        "canonical_name",
        "endorser_type",
        "is_panel_endorser",
        "coverage_state",
        "analysis_eligible",
        "contest_id",
        "candidacy_id",
        "person_id",
        "candidate_name",
        "election_date",
        "election_year",
        "election_type",
        "office_type",
        "incumbency_class",
        "elected",
        "vote_share",
        "vote_rank",
        "n_candidates",
        "field_candidates",
        "field_endorsed_count",
        "field_informative",
        "field_expected_win",
        "field_win_lift",
        "field_expected_vote_share",
        "field_vote_share_lift",
        "role_pool_candidates",
        "role_endorsed_count",
        "role_informative",
        "role_expected_win",
        "role_win_lift",
        "role_expected_vote_share",
        "role_vote_share_lift",
        "strongest_other_vote_share",
        "signed_margin_over_strongest_other",
        "panel_endorsements_for_candidate",
        "endorsed_person_key",
        "endorsement_kind",
        "source_type",
        "announcement_date",
        "days_before_election",
    ]
    return (
        edge[columns]
        .sort_values(["canonical_name", "election_date", "contest_id"], kind="stable")
        .reset_index(drop=True)
    )


def _clustered_lift_interval(
    frame: pd.DataFrame,
    lift_column: str,
    *,
    n_bootstrap: int,
    rng: np.random.Generator,
) -> tuple[float, float]:
    if frame.empty:
        return np.nan, np.nan
    contests = [group for _, group in frame.groupby("contest_id", sort=False)]
    estimates = []
    for _ in range(n_bootstrap):
        sampled = rng.integers(0, len(contests), len(contests))
        boot = pd.concat([contests[index] for index in sampled], ignore_index=True)
        estimates.append(float(boot[lift_column].mean() * 100))
    return tuple(float(value) for value in np.percentile(estimates, [2.5, 97.5]))


def _pool_values(
    field: pd.DataFrame,
    contest_id: str,
    incumbency_class: str | None,
    outcome: str,
) -> np.ndarray:
    pool = field[field["contest_id"].eq(contest_id)]
    if incumbency_class is not None:
        pool = pool[pool["incumbency_class"].eq(incumbency_class)]
    return pool[outcome].to_numpy(dtype=float)


def _randomization_p(
    observations: pd.DataFrame,
    field: pd.DataFrame,
    *,
    outcome: str,
    matched: bool,
    n_permutations: int,
    rng: np.random.Generator,
) -> float:
    informative = observations[
        observations["role_informative" if matched else "field_informative"]
    ].copy()
    if informative.empty:
        return np.nan
    blocks = ["contest_id", "incumbency_class"] if matched else ["contest_id"]
    grouped = list(informative.groupby(blocks, sort=False))
    observed = informative[outcome].astype(float).mean()
    expected_sum = 0.0
    null_sum = np.zeros(n_permutations, dtype=float)
    total_edges = 0
    for key, group in grouped:
        if not isinstance(key, tuple):
            key = (key,)
        contest_id = key[0]
        role = key[1] if matched else None
        pool = _pool_values(field, contest_id, role, outcome)
        count = len(group)
        expected_sum += count * float(pool.mean())
        total_edges += count
        if count == 1:
            null_sum += rng.choice(pool, size=n_permutations, replace=True)
        else:
            for index in range(n_permutations):
                null_sum[index] += rng.choice(pool, size=count, replace=False).sum()
    expected = expected_sum / total_edges
    null = null_sum / total_edges
    distance = abs(observed - expected)
    return float((np.sum(np.abs(null - expected) >= distance - 1e-12) + 1) / (len(null) + 1))


def _year_effects(frame: pd.DataFrame, column: str) -> str:
    values = []
    for year, group in frame.groupby("election_year"):
        values.append(f"{int(year)}:{group[column].mean() * 100:+.2f}")
    return "|".join(values)


def _leave_one_group_range(
    frame: pd.DataFrame, lift_column: str, group_column: str
) -> tuple[float, float]:
    groups = frame[group_column].dropna().unique()
    if len(groups) < 2:
        return np.nan, np.nan
    estimates = [
        frame.loc[~frame[group_column].eq(group), lift_column].mean() * 100 for group in groups
    ]
    return float(np.min(estimates)), float(np.max(estimates))


def _benjamini_hochberg(values: pd.Series) -> pd.Series:
    p_values = values.fillna(1.0).to_numpy(dtype=float)
    order = np.argsort(p_values)
    ranked = p_values[order]
    adjusted = ranked * len(ranked) / np.arange(1, len(ranked) + 1)
    adjusted = np.minimum.accumulate(adjusted[::-1])[::-1]
    result = np.empty(len(adjusted))
    result[order] = np.minimum(adjusted, 1.0)
    return pd.Series(result, index=values.index)


def evaluate_endorsers(
    observations: pd.DataFrame,
    results: pd.DataFrame,
    endorsers: pd.DataFrame,
    *,
    n_permutations: int = 9_999,
    n_bootstrap: int = 2_000,
    seed: int = 20260822,
) -> pd.DataFrame:
    """Return per-Endorser field and incumbency-matched success associations."""
    field = results[
        results["result_status"].eq("final")
        & results["vote_share"].notna()
        & results["elected"].notna()
        & results["contest_id"].isin(
            observations.loc[observations["analysis_eligible"], "contest_id"]
        )
    ].copy()
    field["incumbency_class"] = _incumbency_class(field["incumbent"])
    field["elected"] = field["elected"].astype(bool)

    rows = []
    for endorser_index, endorser in endorsers.sort_values("canonical_name").iterrows():
        all_group = observations[observations["endorser_id"].eq(endorser["endorser_id"])].copy()
        group = all_group[all_group["analysis_eligible"]].copy()
        role = group[group["role_informative"]].copy()
        field_group = group[group["field_informative"]].copy()
        role_win_loo_year = _leave_one_group_range(role, "role_win_lift", "election_year")
        role_share_loo_year = _leave_one_group_range(role, "role_vote_share_lift", "election_year")
        role_win_loo_person = _leave_one_group_range(role, "role_win_lift", "endorsed_person_key")
        role_share_loo_person = _leave_one_group_range(
            role, "role_vote_share_lift", "endorsed_person_key"
        )
        row = {
            "endorser_id": endorser["endorser_id"],
            "canonical_name": endorser["canonical_name"],
            "endorser_type": endorser["endorser_type"],
            "confirmed_facts": len(all_group),
            "endorsements": len(group),
            "facts_excluded_for_incomplete_coverage": len(all_group) - len(group),
            "contests": group["contest_id"].nunique(),
            "elections": group["election_year"].nunique(),
            "election_years": "|".join(map(str, sorted(group["election_year"].unique()))),
            "unique_endorsed_people": group["endorsed_person_key"].nunique(),
            "max_endorsements_for_one_person": (
                group.groupby("endorsed_person_key").size().max() if len(group) else 0
            ),
            "councillor_endorsements": int(group["office_type"].eq("councillor").sum()),
            "mayor_endorsements": int(group["office_type"].eq("mayor").sum()),
            "incumbent_endorsements": int(group["incumbency_class"].eq("incumbent").sum()),
            "endorsed_wins": int(group["elected"].sum()),
            "endorsed_win_rate": group["elected"].mean(),
            "mean_endorsed_vote_share": group["vote_share"].mean(),
            "mean_signed_margin_over_strongest_other": group[
                "signed_margin_over_strongest_other"
            ].mean(),
            "median_days_before_election": group["days_before_election"].median(),
            "unknown_announcement_dates": int(group["announcement_date"].isna().sum()),
            "source_types": "|".join(
                sorted(
                    {
                        source
                        for values in group["source_type"].dropna().str.split("|")
                        for source in values
                    }
                )
            ),
            "field_informative_contests": field_group["contest_id"].nunique(),
            "field_win_lift_pp": field_group["field_win_lift"].mean() * 100,
            "field_vote_share_lift_pp": field_group["field_vote_share_lift"].mean() * 100,
            "field_win_election_effects_pp": _year_effects(field_group, "field_win_lift"),
            "field_vote_share_election_effects_pp": _year_effects(
                field_group, "field_vote_share_lift"
            ),
            "role_informative_endorsements": len(role),
            "role_informative_contests": role["contest_id"].nunique(),
            "role_informative_elections": role["election_year"].nunique(),
            "role_win_lift_pp": role["role_win_lift"].mean() * 100,
            "role_vote_share_lift_pp": role["role_vote_share_lift"].mean() * 100,
            "role_win_election_effects_pp": _year_effects(role, "role_win_lift"),
            "role_vote_share_election_effects_pp": _year_effects(role, "role_vote_share_lift"),
            "role_win_loo_election_min_pp": role_win_loo_year[0],
            "role_win_loo_election_max_pp": role_win_loo_year[1],
            "role_vote_share_loo_election_min_pp": role_share_loo_year[0],
            "role_vote_share_loo_election_max_pp": role_share_loo_year[1],
            "role_win_loo_person_min_pp": role_win_loo_person[0],
            "role_win_loo_person_max_pp": role_win_loo_person[1],
            "role_vote_share_loo_person_min_pp": role_share_loo_person[0],
            "role_vote_share_loo_person_max_pp": role_share_loo_person[1],
        }
        for prefix, data, win_column, share_column in [
            ("field", field_group, "field_win_lift", "field_vote_share_lift"),
            ("role", role, "role_win_lift", "role_vote_share_lift"),
        ]:
            for outcome_name, column in [("win", win_column), ("vote_share", share_column)]:
                low, high = _clustered_lift_interval(
                    data,
                    column,
                    n_bootstrap=n_bootstrap,
                    rng=np.random.default_rng(seed + endorser_index * 17 + len(rows)),
                )
                row[f"{prefix}_{outcome_name}_ci_low_pp"] = low
                row[f"{prefix}_{outcome_name}_ci_high_pp"] = high
        for prefix, matched in [("field", False), ("role", True)]:
            row[f"{prefix}_win_randomization_p"] = _randomization_p(
                group,
                field,
                outcome="elected",
                matched=matched,
                n_permutations=n_permutations,
                rng=np.random.default_rng(seed + endorser_index * 101 + int(matched)),
            )
            row[f"{prefix}_vote_share_randomization_p"] = _randomization_p(
                group,
                field,
                outcome="vote_share",
                matched=matched,
                n_permutations=n_permutations,
                rng=np.random.default_rng(seed + endorser_index * 101 + int(matched) + 2),
            )
        rows.append(row)

    result = pd.DataFrame(rows)
    for prefix in ("field", "role"):
        family_columns = [
            f"{prefix}_win_randomization_p",
            f"{prefix}_vote_share_randomization_p",
        ]
        stacked = result[family_columns].fillna(1.0).stack()
        adjusted = _benjamini_hochberg(stacked)
        for column in family_columns:
            q_column = column.replace("_p", "_q")
            result[q_column] = (
                adjusted.xs(column, level=1).reindex(result.index).where(result[column].notna())
            )

    enough_field = result["field_informative_contests"].ge(MIN_CLEAR_CONTESTS) & result[
        "elections"
    ].ge(MIN_CLEAR_ELECTIONS)
    enough_role = result["role_informative_contests"].ge(MIN_CLEAR_CONTESTS) & result[
        "role_informative_elections"
    ].ge(MIN_CLEAR_ELECTIONS)
    clear_field = (
        result[["field_win_randomization_q", "field_vote_share_randomization_q"]]
        .min(axis=1)
        .lt(0.05)
    )
    clear_role = (
        result[["role_win_randomization_q", "role_vote_share_randomization_q"]].min(axis=1).lt(0.05)
    )
    result["evidence_status"] = np.select(
        [
            result["endorsements"].eq(0),
            enough_role & clear_role,
            enough_field & clear_field,
            result["contests"].lt(MIN_CLEAR_CONTESTS),
        ],
        [
            "no_comprehensive_source_endorsements",
            "clear_incumbency_matched_association",
            "clear_field_association_only",
            "insufficient_data",
        ],
        default="no_clear_association",
    )
    return result.sort_values(["evidence_status", "canonical_name"], kind="stable").reset_index(
        drop=True
    )


def _format_number(value: float, digits: int = 2) -> str:
    return "—" if pd.isna(value) else f"{value:+.{digits}f}"


def write_endorsement_report(associations: pd.DataFrame, output_path: Path) -> None:
    """Write a human-readable per-Endorser association report."""
    clear = associations[associations["evidence_status"].eq("clear_incumbency_matched_association")]
    field_only = associations[associations["evidence_status"].eq("clear_field_association_only")]
    lines = [
        "# Endorsement associations with electoral success",
        "",
        "These are selection associations, not estimates of an endorsement's causal effect.",
        "",
        (
            "The primary analysis uses only confirmed Endorsements in Endorser–Contest cells "
            "with a comprehensive source. The field comparison asks how the recorded endorsed "
            "result differs from a random candidate in those exact Contests. The stricter "
            "comparison randomly selects among candidates in "
            "the same Contest with the same incumbent, non-incumbent, or unknown-incumbency "
            "status as the endorsed candidate. Election, Office, field size, and Contest are "
            "therefore held fixed by construction."
        ),
        "",
        (
            "Winner status is the primary outcome and Vote-share lift is the continuous secondary "
            "outcome. Randomization p-values are two-sided and Benjamini-Hochberg q-values correct "
            "the 18 Endorser-by-outcome tests in each comparison family. A clear label requires "
            f"at least {MIN_CLEAR_CONTESTS} informative Contests across "
            f"{MIN_CLEAR_ELECTIONS} elections."
        ),
        "",
        f"Clear after incumbency matching: {len(clear)} Endorsers.",
        f"Clear only against the full candidate field: {len(field_only)} Endorsers.",
        "",
        "| Endorser | Type | Facts | Primary facts | Wins | Win rate | Incumbents endorsed | Matched Contests | Matched win lift | Win q | Matched share lift | Share q | Status |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in associations.itertuples(index=False):
        lines.append(
            f"| {row.canonical_name} | {row.endorser_type} | {row.confirmed_facts} | "
            f"{row.endorsements} | {row.endorsed_wins} | "
            f"{'—' if pd.isna(row.endorsed_win_rate) else f'{row.endorsed_win_rate:.1%}'} | "
            f"{row.incumbent_endorsements} | {row.role_informative_contests} | "
            f"{_format_number(row.role_win_lift_pp)} pp | "
            f"{'—' if pd.isna(row.role_win_randomization_q) else f'{row.role_win_randomization_q:.4f}'} | "
            f"{_format_number(row.role_vote_share_lift_pp)} pp | "
            f"{'—' if pd.isna(row.role_vote_share_randomization_q) else f'{row.role_vote_share_randomization_q:.4f}'} | "
            f"{row.evidence_status} |"
        )
    lines.extend(
        [
            "",
            "## Per-Endorser detail",
            "",
        ]
    )
    for row in associations.sort_values("canonical_name").itertuples(index=False):
        lines.extend(
            [
                f"### {row.canonical_name}",
                "",
                (
                    f"{row.endorsements} comprehensive-source Endorsements in "
                    f"{row.contests} Contests "
                    f"({row.election_years or 'none'}): {row.endorsed_wins} endorsed winners; "
                    f"mean Vote share "
                    f"{'—' if pd.isna(row.mean_endorsed_vote_share) else f'{row.mean_endorsed_vote_share:.1%}'}. "
                    f"The broader positive table contains {row.confirmed_facts} facts; "
                    f"{row.facts_excluded_for_incomplete_coverage} are excluded from the primary "
                    "comparison for incomplete coverage."
                ),
                "",
                (
                    f"Against the full field: Winner lift {_format_number(row.field_win_lift_pp)} "
                    f"points ({_format_number(row.field_win_ci_low_pp)} to "
                    f"{_format_number(row.field_win_ci_high_pp)}), q="
                    f"{'—' if pd.isna(row.field_win_randomization_q) else f'{row.field_win_randomization_q:.4f}'}; "
                    f"Vote-share lift {_format_number(row.field_vote_share_lift_pp)} points "
                    f"({_format_number(row.field_vote_share_ci_low_pp)} to "
                    f"{_format_number(row.field_vote_share_ci_high_pp)}), q="
                    f"{'—' if pd.isna(row.field_vote_share_randomization_q) else f'{row.field_vote_share_randomization_q:.4f}'}."
                ),
                "",
                (
                    f"After incumbency matching ({row.role_informative_contests} informative "
                    f"Contests): Winner lift {_format_number(row.role_win_lift_pp)} points "
                    f"({_format_number(row.role_win_ci_low_pp)} to "
                    f"{_format_number(row.role_win_ci_high_pp)}), q="
                    f"{'—' if pd.isna(row.role_win_randomization_q) else f'{row.role_win_randomization_q:.4f}'}; "
                    f"Vote-share lift {_format_number(row.role_vote_share_lift_pp)} points "
                    f"({_format_number(row.role_vote_share_ci_low_pp)} to "
                    f"{_format_number(row.role_vote_share_ci_high_pp)}), q="
                    f"{'—' if pd.isna(row.role_vote_share_randomization_q) else f'{row.role_vote_share_randomization_q:.4f}'}."
                ),
                "",
                (
                    f"Election-level matched Winner lifts: "
                    f"{row.role_win_election_effects_pp or 'not estimable'}. Vote-share lifts: "
                    f"{row.role_vote_share_election_effects_pp or 'not estimable'}."
                ),
                "",
                (
                    "Leave-one-election-out matched ranges: Winner "
                    f"{_format_number(row.role_win_loo_election_min_pp)} to "
                    f"{_format_number(row.role_win_loo_election_max_pp)} points; Vote share "
                    f"{_format_number(row.role_vote_share_loo_election_min_pp)} to "
                    f"{_format_number(row.role_vote_share_loo_election_max_pp)} points. "
                    f"The primary facts cover {row.unique_endorsed_people} endorsed people, with "
                    f"at most {row.max_endorsements_for_one_person} facts for one Person."
                ),
                "",
            ]
        )
    lines.extend(
        [
            "## Interpretation limits",
            "",
            (
                "The release records positive facts, not candidate-level negatives. This study "
                "therefore never interprets silence as rejection; it compares choices only inside "
                "Contests where the Endorser made at least one confirmed selection."
            ),
            "",
            (
                "Incumbency matching removes the simplest structural explanation but cannot "
                "remove strategic selection on polling, fundraising, campaign quality, ideology, "
                "or private information. The associations describe how well an Endorser selected, "
                "not how many votes the Endorsement caused."
            ),
            "",
            (
                "Historical coverage is uneven and some Endorsers have only three or four primary "
                "facts. David Miller and Olivia Chow have no comprehensive-source historical "
                "Endorsements in this release. "
                "Those rows are retained as explicit insufficient-data results."
            ),
            "",
        ]
    )
    output_path.write_text("\n".join(lines))


def run_endorsement_analysis(
    results_root: Path,
    output_dir: Path,
    *,
    n_permutations: int = 9_999,
    n_bootstrap: int = 2_000,
    seed: int = 20260822,
) -> EndorsementArtifacts:
    """Load upstream artifacts, evaluate Endorsers, and write downstream outputs."""
    results_root = Path(results_root)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    results = pd.read_parquet(results_root / "data" / "out" / "election_results.parquet")
    endorsements = pd.read_parquet(results_root / "data" / "out" / "endorsements.parquet")
    endorsers = pd.read_parquet(results_root / "data" / "out" / "endorsers.parquet")
    assertions = pd.read_parquet(results_root / "data" / "out" / "endorsement_assertions.parquet")
    coverage = pd.read_parquet(results_root / "data" / "out" / "endorsement_coverage.parquet")
    observations = build_endorsement_observations(
        results, endorsements, endorsers, assertions, coverage
    )
    associations = evaluate_endorsers(
        observations,
        results,
        endorsers,
        n_permutations=n_permutations,
        n_bootstrap=n_bootstrap,
        seed=seed,
    )
    artifacts = EndorsementArtifacts(
        observations=output_dir / "endorsement_observations.csv",
        associations=output_dir / "endorser_associations.csv",
        report=output_dir / "endorsement-analysis-report.md",
    )
    observations.to_csv(artifacts.observations, index=False)
    associations.to_csv(artifacts.associations, index=False)
    write_endorsement_report(associations, artifacts.report)
    return artifacts


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    results_root = Path(__file__).resolve().parents[4] / "toronto-election-results"
    output_dir = project_root / "data" / "out" / "endorsements"
    artifacts = run_endorsement_analysis(results_root, output_dir)
    print(f"wrote {len(artifacts.paths())} endorsement artifacts to {output_dir}")


if __name__ == "__main__":
    main()
