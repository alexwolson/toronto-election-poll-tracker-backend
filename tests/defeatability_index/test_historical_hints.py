"""Candidate-facing historical hint catalog."""

import json
from pathlib import Path

import pandas as pd

from defeatability_index.historical_hints import (
    SCREEN_HINT_IDS,
    evaluate_historical_hints,
    write_historical_hint_catalog,
)


def _frame() -> pd.DataFrame:
    rows = []
    for year in (2010, 2014, 2022):
        for contest_number in range(7):
            contest = f"{year}-{contest_number}"
            for candidate_number in range(4):
                officeholder = candidate_number == 0
                rows.append(
                    {
                        "candidacy_id": f"{contest}-{candidate_number}",
                        "person_id": f"person-{year}-{contest_number}-{candidate_number}",
                        "contest_id": contest,
                        "election_year": year,
                        "election_type": "general",
                        "vote_share": 0.55 if officeholder else 0.15,
                        "elected": officeholder,
                        "n_candidates": 4,
                        "candidate_regime": "open_contest",
                        "history_status": "confirmed",
                        "career_record": (
                            "prior_officeholder"
                            if officeholder
                            else "no_observed_prior_office_record"
                        ),
                        "current_other_officeholder": False,
                        "any_prior_officeholder_opponent": not officeholder,
                        "any_current_other_officeholder_opponent": False,
                        "prior_office_types_won": "trustee" if officeholder else "",
                        "prior_office_types_contested": "trustee" if officeholder else "",
                        "most_recent_prior_margin": 0.20 if officeholder else None,
                        "strongest_opponent_prior_margin": None if officeholder else 0.20,
                        "prior_candidacy_count": 2 if officeholder else 0,
                        "victory_count": 1 if officeholder else 0,
                        "office_breadth": 1 if officeholder else 0,
                        "max_opponent_victory_count": 0 if officeholder else 1,
                        "returning_councillor": False,
                        "any_returning_councillor_opponent": False,
                        "has_prior_elected_office": officeholder,
                        "any_prior_elected_office_opponent": not officeholder,
                        "prior_elected_candidacy_count": 2 if officeholder else 0,
                        "prior_elected_victory_count": 1 if officeholder else 0,
                        "all_prior_candidacy_count": 2 if officeholder else 1,
                        "all_prior_victory_count": 1 if officeholder else 0,
                        "has_all_prior_victory": officeholder,
                        "most_recent_all_prior_margin": 0.20 if officeholder else -0.10,
                        "most_recent_all_prior_was_victory": officeholder,
                        "prior_council_run_without_victory": not officeholder,
                        "multiple_prior_council_runs_without_victory": False,
                        "opponent_history_complete": True,
                        "any_opponent_all_prior_victory": not officeholder,
                        "any_opponent_prior_council_run_without_victory": True,
                        "strongest_opponent_most_recent_all_prior_margin": (
                            -0.10 if officeholder else 0.20
                        ),
                        "any_opponent_prior_trustee_victory": not officeholder,
                        "sole_candidate_with_all_prior_race": False,
                        "sole_candidate_with_all_prior_victory": officeholder,
                        "most_recent_prior_elected_margin": 0.20 if officeholder else None,
                        "strongest_opponent_prior_elected_margin": (None if officeholder else 0.20),
                    }
                )
    return pd.DataFrame(rows)


def test_catalog_supports_clear_candidate_facing_patterns_and_withholds_sparse_ones(tmp_path: Path):
    frame = _frame()

    audit = evaluate_historical_hints(frame, n_bootstrap=100, seed=7).set_index("hint_id")

    broad = "own_any_all_past_race_victory__non_incumbent_non_returning"
    assert audit.loc[broad, "evidence_status"] == "supported"
    assert audit.loc["own_prior_win_type__trustee", "evidence_status"] == "supported"
    assert "own_prior_officeholder__open_contest" not in audit.index
    assert "own_prior_elected_victory_count" not in audit.index
    assert "own_most_recent_prior_margin" not in audit.index
    assert "own_most_recent_prior_elected_margin" not in audit.index
    assert (
        not audit["trigger_operator"]
        .isin(["continuous_history_only", "continuous_prior_elected_history_only"])
        .any()
    )
    assert set(SCREEN_HINT_IDS).issubset(audit.index)
    eligible_screen = {
        "own_returning_councillor__open_contest",
        "opponent_returning_councillor__open_contest",
        "own_any_all_past_race__non_incumbent_non_returning",
        "own_multiple_all_past_races__non_incumbent_non_returning",
        ("own_prior_council_run_without_victory_vs_no_history__non_incumbent_non_returning"),
        ("own_prior_council_run_without_victory_vs_other_history__non_incumbent_non_returning"),
        "own_most_recent_all_past_race_margin__non_incumbent_non_returning",
        "own_most_recent_all_past_race_was_victory__non_incumbent_non_returning",
        "own_prior_mpp_race__non_incumbent_non_returning",
        "opponent_strongest_most_recent_all_past_race_margin__incumbent",
    }
    assert (
        set(
            audit.loc[
                list(SCREEN_HINT_IDS),
                "catalog_eligible",
            ][lambda values: values].index
        )
        == eligible_screen
    )

    paths = write_historical_hint_catalog(frame, tmp_path, n_bootstrap=100, seed=7)
    assert all(path.exists() for path in paths)
    supported = pd.read_csv(tmp_path / "supported_historical_hints.csv")
    assert supported["frontend_copy"].str.contains("Historically").all()
    assert broad in set(supported["hint_id"])
    assert "own_prior_elected_victory_count" not in set(supported["hint_id"])
    assert supported["trigger_definition"].notna().all()
    paired = {
        "own_prior_council_run_without_victory_vs_no_history__non_incumbent_non_returning",
        "own_prior_council_run_without_victory_vs_other_history__non_incumbent_non_returning",
    }
    assert set(supported["hint_id"]) & paired in (set(), paired)
    contract = json.loads((tmp_path / "historical_hint_contract.json").read_text())
    assert contract["schema_version"] == "2.1.0"
    assert contract["history_scope"]["sitting_incumbent_is_returning_councillor"] is False
    assert (
        "all confirmed elected-office races"
        in contract["history_scope"]["allowed_race_history_scopes"]
    )
    assert contract["elected_rule"]["acclamations_count_as_victories"] is True
    assert contract["race_history_display_rule"]["missing_is_zero"] is False
    assert contract["race_history_display_rule"]["zero_wins_hint"] == "Do not publish."
    assert contract["all_past_race_margin_rule"]["losses_are_negative"] is True
    assert contract["display_rule"]["paired_display_groups_must_be_complete"] is True
    assert contract["publication_rule"]["independent_conditional_effect_required"] is False
    assert (tmp_path / "all-past-races-victory-count-report.md").exists()
    assert (tmp_path / "candidate-history-flag-screen-report.md").exists()
    assert (tmp_path / "candidate-history-flag-approval-report.md").exists()


def test_prior_unsuccessful_council_comparisons_share_a_required_display_group():
    audit = evaluate_historical_hints(_frame(), n_bootstrap=100, seed=7).set_index("hint_id")
    positive = "own_prior_council_run_without_victory_vs_no_history__non_incumbent_non_returning"
    negative = "own_prior_council_run_without_victory_vs_other_history__non_incumbent_non_returning"

    assert audit.loc[positive, "display_group"] == "prior_unsuccessful_council_run_context"
    assert audit.loc[negative, "display_group"] == "prior_unsuccessful_council_run_context"
    assert audit.loc[positive, "paired_hint_id"] == negative
    assert audit.loc[negative, "paired_hint_id"] == positive
