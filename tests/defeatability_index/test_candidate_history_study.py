"""End-to-end candidate-history study artifacts."""

from pathlib import Path

import pandas as pd
import pytest

from defeatability_index.candidate_history_study import StudyInputs, run_candidate_history_study
from defeatability_index.paths import results_dir


@pytest.mark.skipif(
    not (results_dir() / "data" / "out" / "election_results.csv").exists(),
    reason="source election-results dataset not available",
)
def test_study_writes_auditable_candidate_level_artifacts(tmp_path: Path):
    inputs = StudyInputs(
        results_root=results_dir(),
        external_candidacies=Path("data/reference/external_candidacies.csv"),
        external_tenures=Path("data/reference/external_office_tenures.csv"),
    )

    artifacts = run_candidate_history_study(
        inputs, tmp_path, n_permutations=9, n_bootstrap=20, seed=7
    )

    for path in artifacts.paths():
        assert path.exists(), path
    frame = pd.read_csv(artifacts.candidate_frame)
    audit = pd.read_csv(artifacts.identity_audit)
    assert len(frame) == 1_646
    assert len(audit) == 1_646
    assert int(audit["potential_prior_win_unresolved"].sum()) == 0
    report = artifacts.evidence_report.read_text().casefold()
    assert "conclusion:" in report
    assert "not estimable" not in report.splitlines()[2]
    assert "prior-officeholder identity gate is closed" in report
    assert "prior unsuccessful candidates remain not estimable" in report
    hint_audit = pd.read_csv(artifacts.historical_hint_audit)
    assert {
        "hint_id",
        "trigger_field",
        "adjusted_vote_share_effect_pp",
        "evidence_status",
        "frontend_copy",
    }.issubset(hint_audit.columns)
