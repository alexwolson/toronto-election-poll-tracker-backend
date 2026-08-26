"""Pre-specified evidence test and full candidate-history exploration."""

import pandas as pd

from defeatability_index.candidate_history_analysis import evaluate_candidate_history


def _clear_signal_frame():
    rows = []
    for year in (2006, 2010, 2014, 2022):
        for contest_number in (1, 2):
            contest_id = f"{year}-{contest_number}"
            shares = (0.50, 0.25, 0.15, 0.10)
            for candidate_number, share in enumerate(shares):
                officeholder = candidate_number == 0
                rows.append(
                    {
                        "candidacy_id": f"{contest_id}-{candidate_number}",
                        "contest_id": contest_id,
                        "election_year": year,
                        "election_type": "general",
                        "vote_share": share,
                        "elected": officeholder,
                        "n_candidates": 4,
                        "candidate_regime": "open_contest",
                        "history_status": "confirmed",
                        "career_record": "prior_officeholder"
                        if officeholder
                        else "no_observed_prior_office_record",
                        "most_recent_prior_margin": 0.20 if officeholder else None,
                        "any_prior_officeholder_opponent": not officeholder,
                        "strongest_opponent_prior_margin": None if officeholder else 0.20,
                        "prior_candidacy_count": 2 if officeholder else 0,
                        "victory_count": 2 if officeholder else 0,
                        "prior_loss_count": 0,
                        "office_breadth": 1 if officeholder else 0,
                        "best_prior_margin": 0.25 if officeholder else None,
                        "mean_prior_win_margin": 0.20 if officeholder else None,
                        "years_since_last_run": 2.0 if officeholder else None,
                        "years_since_last_win": 2.0 if officeholder else None,
                        "current_other_officeholder": False,
                        "prior_office_types_contested": "trustee" if officeholder else "",
                        "prior_office_types_won": "trustee" if officeholder else "",
                        "prior_officeholder_opponent_count": 0 if officeholder else 1,
                        "prior_officeholder_opponent_share": 0 if officeholder else 1 / 3,
                        "opponent_office_types": "" if officeholder else "trustee",
                        "max_opponent_victory_count": 0 if officeholder else 2,
                        "total_opponent_victory_count": 0 if officeholder else 2,
                        "any_current_other_officeholder_opponent": False,
                        "any_incumbent_opponent": False,
                    }
                )
    return pd.DataFrame(rows)


def test_evidence_test_detects_stable_candidate_history_signal():
    results = evaluate_candidate_history(
        _clear_signal_frame(), n_permutations=99, n_bootstrap=200, seed=7
    )

    performance = results.model_performance.set_index("model")
    assert set(performance.index) == {
        "baseline",
        "simple_history",
        "full_history",
        "flexible_history",
    }
    assert {"cv_rmse", "cv_r2", "cv_brier", "cv_log_loss", "cv_auc"}.issubset(performance.columns)
    assert performance.loc["simple_history", "cv_rmse"] < performance.loc["baseline", "cv_rmse"]
    assert results.simple_evidence["delta_rmse"] > 0
    assert results.simple_evidence["permutation_p"] <= 0.05
    assert results.simple_evidence["delta_rmse_ci_low"] > 0
    assert results.simple_evidence["direction_stable"]
    assert results.simple_evidence["status"] == "supported_signal"
    assert set(results.oof_predictions["election_year"]) == {2010, 2014, 2022}
    assert set(results.sensitivity_performance["scope"]) == {
        "primary_2010_plus_stable_boundary",
        "stable_boundary_including_2006",
        "all_general_including_2006_2018",
    }
    assert results.feature_effects["feature"].str.contains("most_recent_prior_margin").any()
    assert "most_recent_prior_margin" in set(results.flexible_importance["feature"])
