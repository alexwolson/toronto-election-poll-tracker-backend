"""Candidate-level career history and Opponent-field history."""

import pandas as pd
import pytest

from defeatability_index.candidate_history import build_candidate_history_frame
from defeatability_index.paths import results_dir


def _result(
    candidacy_id,
    person_id,
    contest_id,
    election_date,
    office_type,
    vote_share,
    elected,
    *,
    election_type="general",
):
    return {
        "candidacy_id": candidacy_id,
        "person_id": person_id,
        "contest_id": contest_id,
        "election_date": election_date,
        "election_year": int(election_date[:4]),
        "election_type": election_type,
        "office_type": office_type,
        "candidate_name": candidacy_id,
        "vote_share": vote_share,
        "elected": elected,
        "incumbent": False,
        "n_candidates": 4 if office_type == "councillor" else 2,
    }


def test_candidate_history_frame_uses_only_prior_history_and_excludes_self_from_field():
    results = pd.DataFrame(
        [
            # p1 won trustee, then narrowly lost trustee before running for council.
            _result("p1-trustee-win", "p1", "trustee-2014", "2014-10-27", "trustee", 0.60, True),
            _result(
                "trustee-runner-up", "t2", "trustee-2014", "2014-10-27", "trustee", 0.40, False
            ),
            _result("p1-trustee-loss", "p1", "trustee-2018", "2018-10-22", "trustee", 0.45, False),
            _result("trustee-winner", "t3", "trustee-2018", "2018-10-22", "trustee", 0.55, True),
            # p2 ran unsuccessfully for MPP. Its later win must not leak backward.
            _result("p2-mpp-loss", "p2", "mpp-2018", "2018-06-07", "mpp", 0.48, False),
            _result("mpp-winner", "m2", "mpp-2018", "2018-06-07", "mpp", 0.52, True),
            _result("p2-future-win", "p2", "mpp-2025", "2025-02-27", "mpp", 0.60, True),
            _result("future-runner-up", "m3", "mpp-2025", "2025-02-27", "mpp", 0.40, False),
            # The 2022 Open contest being predicted.
            _result("p1-council", "p1", "council-2022", "2022-10-24", "councillor", 0.40, True),
            _result("p2-council", "p2", "council-2022", "2022-10-24", "councillor", 0.30, False),
            _result("p3-council", "p3", "council-2022", "2022-10-24", "councillor", 0.20, False),
            _result(
                "unknown-council", None, "council-2022", "2022-10-24", "councillor", 0.10, False
            ),
        ]
    )
    external_candidacies = pd.DataFrame(
        [
            {
                "person_id": "p1",
                "election_date": "2020-09-01",
                "office_type": "mp",
                "elected": True,
                "vote_share": 0.55,
                "prior_performance_margin": 0.10,
                "source_detail": "official fixture",
            }
        ]
    )
    career_tenures = pd.DataFrame(
        [
            {
                "person_id": "p1",
                "office_type": "trustee",
                "started_on": "2014-10-27",
                "ended_on": "2023-01-01",
                "source_detail": "official fixture",
            }
        ]
    )

    frame = build_candidate_history_frame(results, external_candidacies, career_tenures)

    assert list(frame["candidacy_id"]) == [
        "p1-council",
        "p2-council",
        "p3-council",
        "unknown-council",
    ]

    p1 = frame.set_index("candidacy_id").loc["p1-council"]
    assert p1["career_record"] == "mixed_prior_office_record"
    assert p1["prior_candidacy_count"] == 3
    assert p1["victory_count"] == 2
    assert p1["prior_loss_count"] == 1
    assert p1["office_breadth"] == 2
    assert p1["most_recent_prior_margin"] == 0.10
    assert p1["best_prior_margin"] == pytest.approx(0.20)
    assert p1["current_other_officeholder"]
    assert p1["candidate_regime"] == "open_contest"
    assert p1["most_recent_all_prior_margin"] == pytest.approx(0.10)
    assert p1["most_recent_all_prior_was_victory"]

    p2 = frame.set_index("candidacy_id").loc["p2-council"]
    assert p2["career_record"] == "prior_unsuccessful_candidate"
    assert p2["prior_candidacy_count"] == 1
    assert p2["victory_count"] == 0
    assert p2["most_recent_prior_margin"] == pytest.approx(-0.04)
    assert p2["most_recent_all_prior_margin"] == pytest.approx(-0.04)
    assert not p2["most_recent_all_prior_was_victory"]

    p3 = frame.set_index("candidacy_id").loc["p3-council"]
    assert p3["career_record"] == "no_observed_prior_office_record"
    assert p3["any_prior_officeholder_opponent"]
    assert p3["prior_officeholder_opponent_count"] == 1
    assert p3["strongest_opponent_prior_margin"] == pytest.approx(0.10)

    unresolved = frame.set_index("candidacy_id").loc["unknown-council"]
    assert unresolved["history_status"] == "identity_unresolved"
    assert pd.isna(unresolved["career_record"])


def test_former_councillor_returning_in_another_contest_is_separate_from_incumbency():
    results = pd.DataFrame(
        [
            _result("returner-win", "returner", "old-ward", "2010-10-25", "councillor", 0.60, True),
            _result("old-runner-up", "other", "old-ward", "2010-10-25", "councillor", 0.40, False),
            _result(
                "returner-new-ward", "returner", "new-ward", "2022-10-24", "councillor", 0.45, False
            ),
            _result(
                "new-opponent", "new-person", "new-ward", "2022-10-24", "councillor", 0.55, True
            ),
        ]
    )

    frame = build_candidate_history_frame(results, pd.DataFrame(), pd.DataFrame())
    current = frame.set_index("candidacy_id").loc["returner-new-ward"]
    opponent = frame.set_index("candidacy_id").loc["new-opponent"]

    assert current["candidate_regime"] == "open_contest"
    assert current["returning_councillor"]
    assert current["prior_council_victory_count"] == 1
    assert current["most_recent_prior_council_margin"] == pytest.approx(0.20)
    assert current["most_recent_prior_elected_margin"] == pytest.approx(0.20)
    assert current["prior_elected_victory_count"] == 1
    assert current["has_prior_elected_office"]
    assert opponent["any_returning_councillor_opponent"]
    assert opponent["any_prior_elected_office_opponent"]


def test_all_past_race_count_includes_unsuccessful_council_runs():
    results = pd.DataFrame(
        [
            _result(
                "candidate-council-loss",
                "candidate",
                "council-2014",
                "2014-10-27",
                "councillor",
                0.40,
                False,
            ),
            _result(
                "council-winner",
                "other",
                "council-2014",
                "2014-10-27",
                "councillor",
                0.60,
                True,
            ),
            _result(
                "candidate-trustee-loss",
                "candidate",
                "trustee-2018",
                "2018-10-22",
                "trustee",
                0.45,
                False,
            ),
            _result(
                "trustee-winner",
                "trustee-other",
                "trustee-2018",
                "2018-10-22",
                "trustee",
                0.55,
                True,
            ),
            _result(
                "candidate-council-2022",
                "candidate",
                "council-2022",
                "2022-10-24",
                "councillor",
                0.45,
                False,
            ),
            _result(
                "winner-2022",
                "new-winner",
                "council-2022",
                "2022-10-24",
                "councillor",
                0.55,
                True,
            ),
        ]
    )

    frame = build_candidate_history_frame(results, pd.DataFrame(), pd.DataFrame())
    current = frame.set_index("candidacy_id").loc["candidate-council-2022"]

    # The existing qualifying definition excludes a council loss for a non-returner.
    assert current["prior_elected_candidacy_count"] == 1
    # The visible-history definition includes every earlier confirmed race.
    assert current["all_prior_candidacy_count"] == 2
    assert current["all_prior_victory_count"] == 0
    assert not current["has_all_prior_victory"]
    assert current["most_recent_all_prior_margin"] == pytest.approx(-0.10)
    assert not current["most_recent_all_prior_was_victory"]
    assert current["prior_council_run_without_victory"]
    assert not current["multiple_prior_council_runs_without_victory"]
    assert current["sole_candidate_with_all_prior_race"]

    winner = frame.set_index("candidacy_id").loc["winner-2022"]
    assert winner["any_opponent_prior_council_run_without_victory"]
    assert not winner["sole_candidate_with_all_prior_race"]


@pytest.mark.skipif(
    not (results_dir() / "data" / "out" / "election_results.csv").exists(),
    reason="source election-results dataset not available",
)
def test_candidate_history_frame_reports_current_upstream_identity_coverage():
    out = results_dir() / "data" / "out"
    results = pd.read_csv(out / "election_results.csv")
    tenures = pd.read_csv(out / "office_tenures.csv")
    empty_external = pd.DataFrame(
        columns=[
            "person_id",
            "election_date",
            "office_type",
            "elected",
            "vote_share",
            "prior_performance_margin",
            "source_detail",
        ]
    )

    final_results = results[results["result_status"].eq("final")].copy()
    frame = build_candidate_history_frame(final_results, empty_external, tenures)

    assert len(frame) == 1_646
    assert frame["history_status"].value_counts().to_dict() == {
        "confirmed": 1_454,
        "identity_unresolved": 192,
    }
    confirmed = frame[frame.history_status == "confirmed"]
    assert int((confirmed.prior_candidacy_count > 0).sum()) == 80
    assert (
        int(confirmed.career_record.isin(["prior_officeholder", "mixed_prior_office_record"]).sum())
        == 45
    )
