"""Per-Endorser electoral-success association study."""

from pathlib import Path

import pandas as pd

from defeatability_index.endorsement_analysis import (
    build_endorsement_observations,
    evaluate_endorsers,
    write_endorsement_report,
)


def _fixtures() -> tuple[pd.DataFrame, ...]:
    result_rows = []
    endorsement_rows = []
    assertion_rows = []
    coverage_rows = []
    for contest_number in range(12):
        year = 2010 if contest_number < 6 else 2014
        contest_id = f"contest-{contest_number}"
        for candidate_number, (share, elected, incumbent) in enumerate(
            [(0.50, True, False), (0.20, False, False), (0.30, False, True)]
        ):
            candidacy_id = f"candidate-{contest_number}-{candidate_number}"
            result_rows.append(
                {
                    "candidacy_id": candidacy_id,
                    "contest_id": contest_id,
                    "person_id": f"person-{contest_number}-{candidate_number}",
                    "candidate_name": candidacy_id,
                    "election_date": f"{year}-10-25",
                    "election_year": year,
                    "election_type": "general",
                    "result_status": "final",
                    "office_type": "councillor",
                    "elected": elected,
                    "vote_share": share,
                    "vote_rank": 1 if elected else candidate_number + 1,
                    "incumbent": incumbent,
                    "n_candidates": 3,
                }
            )
        endorsement_id = f"endorsement-strong-{contest_number}"
        endorsement_rows.append(
            {
                "endorsement_id": endorsement_id,
                "endorser_id": "strong",
                "contest_id": contest_id,
                "candidacy_id": f"candidate-{contest_number}-0",
            }
        )
        assertion_rows.append(
            {
                "endorsement_id": endorsement_id,
                "review_state": "confirmed",
                "announcement_date": f"{year}-10-15",
                "endorsement_kind": "endorsement",
                "source_type": "first_party",
            }
        )
        coverage_rows.append(
            {
                "endorser_id": "strong",
                "contest_id": contest_id,
                "coverage_state": "comprehensive_source_found",
            }
        )

    for contest_number in range(3):
        endorsement_id = f"endorsement-sparse-{contest_number}"
        endorsement_rows.append(
            {
                "endorsement_id": endorsement_id,
                "endorser_id": "sparse",
                "contest_id": f"contest-{contest_number}",
                "candidacy_id": f"candidate-{contest_number}-0",
            }
        )
        assertion_rows.append(
            {
                "endorsement_id": endorsement_id,
                "review_state": "confirmed",
                "announcement_date": "2010-10-15",
                "endorsement_kind": "endorsement",
                "source_type": "first_party",
            }
        )
        coverage_rows.append(
            {
                "endorser_id": "sparse",
                "contest_id": f"contest-{contest_number}",
                "coverage_state": (
                    "comprehensive_source_found" if contest_number < 2 else "partially_searched"
                ),
            }
        )

    endorsers = pd.DataFrame(
        [
            {
                "endorser_id": "strong",
                "canonical_name": "Strong Endorser",
                "endorser_type": "organization",
                "is_panel_endorser": True,
            },
            {
                "endorser_id": "sparse",
                "canonical_name": "Sparse Endorser",
                "endorser_type": "person",
                "is_panel_endorser": True,
            },
            {
                "endorser_id": "empty",
                "canonical_name": "Empty Endorser",
                "endorser_type": "editorial_board",
                "is_panel_endorser": True,
            },
        ]
    )
    return (
        pd.DataFrame(result_rows),
        pd.DataFrame(endorsement_rows),
        endorsers,
        pd.DataFrame(assertion_rows),
        pd.DataFrame(coverage_rows),
    )


def test_endorser_analysis_uses_comprehensive_cells_and_matches_incumbency(tmp_path: Path):
    results, endorsements, endorsers, assertions, coverage = _fixtures()
    observations = build_endorsement_observations(
        results, endorsements, endorsers, assertions, coverage
    )

    sparse = observations[observations["endorser_id"].eq("sparse")]
    assert len(sparse) == 3
    assert sparse["analysis_eligible"].sum() == 2
    assert observations["role_pool_candidates"].eq(2).all()

    associations = evaluate_endorsers(
        observations,
        results,
        endorsers,
        n_permutations=999,
        n_bootstrap=200,
        seed=7,
    ).set_index("endorser_id")
    assert associations.loc["strong", "evidence_status"] == ("clear_incumbency_matched_association")
    assert associations.loc["strong", "role_win_lift_pp"] == 50
    assert associations.loc["sparse", "confirmed_facts"] == 3
    assert associations.loc["sparse", "endorsements"] == 2
    assert associations.loc["sparse", "evidence_status"] == "insufficient_data"
    assert associations.loc["empty", "evidence_status"] == ("no_comprehensive_source_endorsements")

    report = tmp_path / "report.md"
    write_endorsement_report(associations.reset_index(), report)
    text = report.read_text()
    assert "not estimates of an endorsement's causal effect" in text
    assert "comprehensive source" in text
