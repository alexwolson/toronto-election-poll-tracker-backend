"""End-to-end candidate-history study orchestration and artifact writing."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .candidate_history import build_candidate_history_frame
from .candidate_history_analysis import StudyResults, evaluate_candidate_history
from .historical_hints import write_historical_hint_catalog


@dataclass(frozen=True)
class StudyInputs:
    results_root: Path
    external_candidacies: Path
    external_tenures: Path


@dataclass(frozen=True)
class StudyArtifacts:
    candidate_frame: Path
    identity_audit: Path
    model_performance: Path
    sensitivity_performance: Path
    feature_effects: Path
    flexible_importance: Path
    oof_predictions: Path
    career_summary: Path
    evidence_report: Path
    exploration_report: Path
    vote_share_figure: Path
    model_figure: Path
    historical_hint_audit: Path
    supported_historical_hints: Path
    historical_hints_report: Path
    historical_hint_contract: Path
    all_past_races_victory_count_report: Path
    candidate_history_flag_screen_report: Path
    candidate_history_flag_approval_report: Path

    def paths(self) -> tuple[Path, ...]:
        return tuple(getattr(self, field) for field in self.__dataclass_fields__)


def _read_optional(path: Path, columns: list[str]) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=columns)
    frame = pd.read_csv(path)
    missing = set(columns) - set(frame.columns)
    if missing:
        raise ValueError(f"{path} missing columns: {sorted(missing)}")
    return frame


def _identity_audit(results: pd.DataFrame, links: pd.DataFrame) -> pd.DataFrame:
    results = results.copy()
    results["election_date"] = pd.to_datetime(results["election_date"])
    active = links[
        links["valid_to_release"].isna()
        & links["link_status"].eq("unresolved")
        & links["person_id"].notna()
    ][["candidacy_id", "person_id", "method", "evidence"]].rename(
        columns={"person_id": "retained_target_person_id"}
    )
    council = results[results["office_type"].eq("councillor")][
        [
            "candidacy_id",
            "person_id",
            "candidate_name",
            "contest_id",
            "election_date",
            "election_year",
            "election_type",
            "elected",
        ]
    ].copy()
    council = council.merge(active, on="candidacy_id", how="left", validate="one_to_one")

    rows = []
    for candidate in council.itertuples(index=False):
        unresolved = pd.isna(candidate.person_id)
        target = candidate.retained_target_person_id if unresolved else candidate.person_id
        prior = results[
            results["person_id"].eq(target)
            & ~results["office_type"].eq("councillor")
            & results["election_date"].lt(candidate.election_date)
        ]
        rows.append(
            {
                "candidacy_id": candidate.candidacy_id,
                "candidate_name": candidate.candidate_name,
                "contest_id": candidate.contest_id,
                "election_date": candidate.election_date.date().isoformat(),
                "election_year": candidate.election_year,
                "election_type": candidate.election_type,
                "elected": candidate.elected,
                "history_status": "identity_unresolved" if unresolved else "confirmed",
                "retained_target_person_id": candidate.retained_target_person_id,
                "potential_prior_run_unresolved": bool(unresolved and not prior.empty),
                "potential_prior_win_unresolved": bool(
                    unresolved and not prior.empty and prior["elected"].astype(bool).any()
                ),
                "potential_prior_office_types": "|".join(sorted(prior["office_type"].unique()))
                if unresolved and not prior.empty
                else "",
                "review_method": candidate.method,
                "review_evidence": candidate.evidence,
            }
        )
    return pd.DataFrame(rows)


def _markdown_table(frame: pd.DataFrame, *, digits: int = 4) -> str:
    shown = frame.copy()
    for column in shown.select_dtypes(include=["float"]).columns:
        shown[column] = shown[column].map(lambda value: f"{value:.{digits}f}")
    headers = [str(column) for column in shown.columns]
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in shown.itertuples(index=False, name=None):
        values = ["" if pd.isna(value) else str(value).replace("|", r"\|") for value in row]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def _yearly_performance(study: StudyResults) -> pd.DataFrame:
    rows = []
    for year, group in study.oof_predictions.groupby("election_year"):
        actual = group["vote_share"].to_numpy()
        baseline = group["baseline_prediction"].to_numpy()
        history = group["simple_history_prediction"].to_numpy()
        baseline_rmse = float(np.sqrt(np.mean((actual - baseline) ** 2)))
        history_rmse = float(np.sqrt(np.mean((actual - history) ** 2)))
        rows.append(
            {
                "election_year": year,
                "baseline_rmse": baseline_rmse,
                "simple_history_rmse": history_rmse,
                "delta_rmse": baseline_rmse - history_rmse,
            }
        )
    return pd.DataFrame(rows)


def _history_coverage(frame: pd.DataFrame) -> pd.DataFrame:
    general = frame[
        frame["election_type"].eq("general") & frame["election_year"].isin([2006, 2010, 2014, 2022])
    ].copy()
    general["observed_prior_run"] = general["prior_candidacy_count"].fillna(0).gt(0)
    general["observed_prior_win"] = general["victory_count"].fillna(0).gt(0)
    return (
        general.groupby("election_year")
        .agg(
            candidacies=("candidacy_id", "size"),
            observed_prior_run=("observed_prior_run", "sum"),
            observed_prior_win=("observed_prior_win", "sum"),
        )
        .reset_index()
    )


def _write_reports(
    frame: pd.DataFrame,
    audit: pd.DataFrame,
    study: StudyResults,
    evidence_path: Path,
    exploration_path: Path,
) -> None:
    unresolved_wins = int(audit["potential_prior_win_unresolved"].sum())
    unresolved_runs = int(audit["potential_prior_run_unresolved"].sum())
    confirmed = int((audit["history_status"] == "confirmed").sum())
    status = (
        "not estimable" if unresolved_wins else study.simple_evidence["status"].replace("_", " ")
    )
    if status == "supported signal":
        status = "supported signal under the revised protocol"
    evidence = study.simple_evidence
    performance = study.model_performance
    baseline = performance.set_index("model").loc["baseline"]
    simple = performance.set_index("model").loc["simple_history"]
    yearly = _yearly_performance(study)
    coverage = _history_coverage(frame)
    strict_prior = frame[
        frame["career_record"].isin(["prior_officeholder", "mixed_prior_office_record"])
    ]
    strict_wins = int(strict_prior["elected"].astype(bool).sum())
    sensitivity_n = len(strict_prior) + unresolved_wins

    if unresolved_wins:
        identity_summary = (
            f"The current release confirms {confirmed:,} of {len(audit):,} council Candidacies. "
            f"It retains {unresolved_runs} unresolved identity targets with an earlier other-office "
            f"run, including {unresolved_wins} with an earlier certified win. Because those cases "
            "can change the Prior-officeholder group materially, the agreed identity-audit gate "
            "remains open."
        )
        identity_sensitivity = (
            f"Identity sensitivity is large: the strict observed cohort has {len(strict_prior)} "
            f"Prior-officeholder appearances and {strict_wins} council wins. If every retained "
            f"target with a prior win were the same Person, the cohort would contain "
            f"{sensitivity_n} appearances but still only {strict_wins} wins. This is a diagnostic "
            "bound, not an identity assertion."
        )
    else:
        identity_summary = (
            f"The current release confirms {confirmed:,} of {len(audit):,} council Candidacies. "
            f"The Prior-officeholder identity gate is closed: none of the {unresolved_runs} "
            "unresolved identity targets with an earlier other-office run has an earlier certified "
            "win. Those remaining cases can still change the Prior-unsuccessful-candidate group, so "
            "effects for prior unsuccessful candidates remain not estimable."
        )
        identity_sensitivity = (
            f"The strict observed cohort has {len(strict_prior)} Prior-officeholder appearances and "
            f"{strict_wins} council wins. There are no unresolved retained targets that would add "
            "another Prior-officeholder appearance."
        )

    evidence_path.write_text(
        "\n".join(
            [
                "# Candidate-history evidence test",
                "",
                f"**Conclusion: {status}.**",
                "",
                identity_summary,
                "",
                identity_sensitivity,
                "",
                "## Revised primary stable-boundary test",
                "",
                (
                    "The primary evaluation begins in 2010. This is a documented protocol revision: "
                    "because source coverage begins in 2003, the 2006 Candidacies have only a "
                    "three-year observable career window. The 2006 election remains a sensitivity "
                    "rather than an equal-weight veto on the career-history hypothesis."
                ),
                "",
                _markdown_table(coverage, digits=0),
                "",
                (
                    f"Adding the simple history features changes held-out Vote-share RMSE from "
                    f"{baseline.cv_rmse:.4f} to {simple.cv_rmse:.4f} (improvement "
                    f"{evidence['delta_rmse']:.4f}; contest-clustered 95% interval "
                    f"[{evidence['delta_rmse_ci_low']:.4f}, {evidence['delta_rmse_ci_high']:.4f}]). "
                    f"The contest-aware permutation p-value is {evidence['permutation_p']:.4f}. "
                    f"Direction is {'stable' if evidence['direction_stable'] else 'not stable'} across "
                    "the primary held-out elections; election-level direction is reported as a "
                    "heterogeneity diagnostic, not an automatic veto."
                ),
                "",
                _markdown_table(performance),
                "",
                "## 2006, 2018, and By-election sensitivity",
                "",
                _markdown_table(study.sensitivity_performance),
                "",
                "## Election stability",
                "",
                _markdown_table(yearly),
                "",
                "The statistical patterns are associations useful for prediction, not causal effects of holding office.",
                "",
            ]
        )
    )

    display_frame = frame.copy()
    display_frame["career_record"] = display_frame["career_record"].fillna("identity_unresolved")
    regime = (
        display_frame.groupby(["candidate_regime", "career_record"], dropna=False)
        .agg(
            candidacies=("candidacy_id", "size"),
            mean_vote_share=("vote_share", "mean"),
            elected_rate=("elected", "mean"),
        )
        .reset_index()
    )
    office = (
        display_frame[display_frame["prior_candidacy_count"].fillna(0).gt(0)]
        .groupby("prior_office_types_contested", dropna=False)
        .agg(
            candidacies=("candidacy_id", "size"),
            people=("person_id", "nunique"),
            mean_vote_share=("vote_share", "mean"),
            elected_rate=("elected", "mean"),
        )
        .reset_index()
    )
    exploration_path.write_text(
        "\n".join(
            [
                "# Candidate-history exploration",
                "",
                "This exploratory layer maps possible sources of signal. It does not override the revised evidence gate.",
                "",
                "## Career-record outcomes",
                "",
                _markdown_table(study.career_summary),
                "",
                "## Candidate regimes",
                "",
                _markdown_table(regime),
                "",
                "## Prior Office types contested",
                "",
                _markdown_table(office),
                "",
                "## Model ladder",
                "",
                _markdown_table(study.model_performance),
                "",
                "## Regularized feature effects",
                "",
                "Coefficients are exploratory and standardized for numeric features. Direction stability is the share of election holdouts with the same sign.",
                "",
                _markdown_table(study.feature_effects.head(30)),
                "",
                "## Flexible-model held-out importance",
                "",
                _markdown_table(study.flexible_importance.head(30)),
                "",
            ]
        )
    )


def _write_figures(study: StudyResults, vote_share_path: Path, model_path: Path) -> None:
    summary = study.career_summary.sort_values("mean_vote_share")
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.barh(summary["career_record"].astype(str), summary["mean_vote_share"] * 100)
    ax.set_xlabel("Mean council Vote share (%)")
    ax.set_title("Council performance by observed prior-office record")
    fig.tight_layout()
    fig.savefig(vote_share_path, dpi=180)
    plt.close(fig)

    performance = study.model_performance.sort_values("cv_rmse", ascending=False)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.barh(performance["model"], performance["cv_rmse"] * 100)
    ax.set_xlabel("Held-out Vote-share RMSE (percentage points; lower is better)")
    ax.set_title("Candidate-history model ladder")
    fig.tight_layout()
    fig.savefig(model_path, dpi=180)
    plt.close(fig)


def run_candidate_history_study(
    inputs: StudyInputs,
    output_dir: Path,
    *,
    n_permutations: int = 999,
    n_bootstrap: int = 2_000,
    seed: int = 0,
) -> StudyArtifacts:
    """Build, evaluate, and write all auditable candidate-history study artifacts."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    out = inputs.results_root / "data" / "out"
    results = pd.read_csv(out / "election_results.csv")
    # The candidate-history study analyzes completed elections only. The current
    # cycle's candidacies carry result_status "pending" and a null `elected`
    # outcome; they must not enter the historical cohort (they would otherwise be
    # miscounted as losses). Older canonicals predate the column and are all final.
    if "result_status" in results.columns:
        results = results[results["result_status"] == "final"].reset_index(drop=True)
    upstream_tenures = pd.read_csv(out / "office_tenures.csv")
    links = pd.read_csv(out / "candidacy_person_links.csv")
    external_candidacies = _read_optional(
        inputs.external_candidacies,
        [
            "person_id",
            "election_date",
            "office_type",
            "elected",
            "vote_share",
            "prior_performance_margin",
            "source_detail",
        ],
    )
    external_tenures = _read_optional(
        inputs.external_tenures,
        ["person_id", "office_type", "started_on", "ended_on", "source_detail"],
    )
    tenures = pd.concat(
        [
            upstream_tenures[
                ["person_id", "office_type", "started_on", "ended_on", "source_detail"]
            ],
            external_tenures,
        ],
        ignore_index=True,
    )

    frame = build_candidate_history_frame(results, external_candidacies, tenures)
    audit = _identity_audit(results, links)
    study = evaluate_candidate_history(
        frame, n_permutations=n_permutations, n_bootstrap=n_bootstrap, seed=seed
    )

    artifacts = StudyArtifacts(
        candidate_frame=output_dir / "candidate_history_frame.csv",
        identity_audit=output_dir / "identity_audit.csv",
        model_performance=output_dir / "model_performance.csv",
        sensitivity_performance=output_dir / "sensitivity_performance.csv",
        feature_effects=output_dir / "feature_effects.csv",
        flexible_importance=output_dir / "flexible_importance.csv",
        oof_predictions=output_dir / "oof_predictions.csv",
        career_summary=output_dir / "career_summary.csv",
        evidence_report=output_dir / "evidence-report.md",
        exploration_report=output_dir / "exploration-report.md",
        vote_share_figure=output_dir / "career-record-vote-share.png",
        model_figure=output_dir / "model-performance.png",
        historical_hint_audit=output_dir / "historical_hint_audit.csv",
        supported_historical_hints=output_dir / "supported_historical_hints.csv",
        historical_hints_report=output_dir / "historical-hints-report.md",
        historical_hint_contract=output_dir / "historical_hint_contract.json",
        all_past_races_victory_count_report=(output_dir / "all-past-races-victory-count-report.md"),
        candidate_history_flag_screen_report=(
            output_dir / "candidate-history-flag-screen-report.md"
        ),
        candidate_history_flag_approval_report=(
            output_dir / "candidate-history-flag-approval-report.md"
        ),
    )
    frame.to_csv(artifacts.candidate_frame, index=False)
    audit.to_csv(artifacts.identity_audit, index=False)
    study.model_performance.to_csv(artifacts.model_performance, index=False)
    study.sensitivity_performance.to_csv(artifacts.sensitivity_performance, index=False)
    study.feature_effects.to_csv(artifacts.feature_effects, index=False)
    study.flexible_importance.to_csv(artifacts.flexible_importance, index=False)
    study.oof_predictions.to_csv(artifacts.oof_predictions, index=False)
    study.career_summary.to_csv(artifacts.career_summary, index=False)
    _write_reports(frame, audit, study, artifacts.evidence_report, artifacts.exploration_report)
    _write_figures(study, artifacts.vote_share_figure, artifacts.model_figure)
    write_historical_hint_catalog(
        frame,
        output_dir,
        n_bootstrap=min(n_bootstrap, 1_000),
        seed=seed,
    )
    return artifacts


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    inputs = StudyInputs(
        results_root=Path(__file__).resolve().parents[4] / "toronto-election-results",
        external_candidacies=project_root / "data" / "reference" / "external_candidacies.csv",
        external_tenures=project_root / "data" / "reference" / "external_office_tenures.csv",
    )
    destination = project_root / "data" / "out" / "candidate_history"
    artifacts = run_candidate_history_study(inputs, destination, seed=20260820)
    print(f"wrote {len(artifacts.paths())} candidate-history artifacts to {destination}")


if __name__ == "__main__":
    main()
