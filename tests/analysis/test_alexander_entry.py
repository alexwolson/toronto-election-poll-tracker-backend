from pathlib import Path

import pytest

from backend.analysis.alexander_entry import apply_entry_profile
from backend.analysis.endorsement_scenarios import build_analysis

BASELINE = {"chow": 50.0, "bradford": 39.0, "alexander": 8.0, "residual": 3.0}
LIAISON_MIX = {"chow": 0.2, "bradford": 0.1, "residual": 0.7}


def test_entry_growth_can_draw_from_other_responses_without_changing_the_denominator():
    result = apply_entry_profile(BASELINE, 3, LIAISON_MIX)

    assert result["shares"] == pytest.approx(
        {"chow": 49.4, "bradford": 38.7, "alexander": 11, "residual": 0.9}
    )
    assert result["max_gain_pp"] == pytest.approx(3 / 0.7)
    assert result["limiting_source"] == "residual"
    assert BASELINE["residual"] == 3


def test_exhausted_other_response_pool_does_not_silently_reallocate_to_named_candidates():
    result = apply_entry_profile(BASELINE, 6, LIAISON_MIX)

    assert result["feasible"] is False
    assert result["shares"] is None
    assert "Someone else" in result["reason"]


@pytest.mark.parametrize(
    ("baseline", "gain", "weights"),
    [
        (BASELINE, -1, LIAISON_MIX),
        (BASELINE, float("nan"), LIAISON_MIX),
        (BASELINE, 3, {**LIAISON_MIX, "residual": 0.8}),
        (BASELINE, 3, {**LIAISON_MIX, "chow": -0.2, "bradford": 0.5}),
        ({**BASELINE, "chow": 49}, 3, LIAISON_MIX),
    ],
)
def test_invalid_growth_assumptions_are_rejected(baseline, gain, weights):
    with pytest.raises(ValueError):
        apply_entry_profile(baseline, gain, weights)


def test_entry_analysis_retains_field_changes_rounding_and_dependent_samples():
    report = build_analysis(Path(__file__).resolve().parents[2])["alexander_entry"]
    forum, liaison = report["profiles"]
    comparison = report["comparisons"][0]

    assert comparison["same_sample"] is True
    assert comparison["before"]["reported_shares"] == {
        "chow": 48,
        "bradford": 36,
        "residual": 17,
    }
    assert comparison["before"]["not_listed"] == ["alexander"]
    assert comparison["before"]["reported_total"] == 101
    assert comparison["after"]["reported_total"] == 100
    assert comparison["reported_deltas"]["residual"] == -7
    assert comparison["before"]["unweighted_base"] == 887
    assert comparison["after"]["unweighted_base"] == 889
    assert forum["weights"] == pytest.approx(
        {
            "chow": (4800 / 101 - 47) / 11,
            "bradford": (3600 / 101 - 32) / 11,
            "residual": (1700 / 101 - 10) / 11,
        }
    )
    assert liaison["weights"] == pytest.approx(LIAISON_MIX)
    assert report["comparisons"][1]["same_sample"] is False
    assert report["comparisons"][2]["before"]["reported_shares"]["undecided"] == 20
    assert report["comparisons"][2]["after"]["reported_shares"]["undecided"] == 20
    assert len(report["extensions"]) == 120
    assert all(len(c["before"]["source_sha256"]) == 64 for c in report["comparisons"])


def test_a_net_one_point_bradford_loss_does_not_identify_his_gross_loss_to_alexander():
    # Two candidate-choice transition matrices yield exactly the same Liaison margins.
    minimal = [[47, 0, 2, 0], [0, 40, 1, 0], [0, 0, 7, 3]]
    bradford_only_to_alexander = [[47, 2, 0, 0], [0, 31, 10, 0], [0, 7, 0, 3]]
    for matrix in (minimal, bradford_only_to_alexander):
        assert [sum(row) for row in matrix] == [49, 41, 10]
        assert [sum(column) for column in zip(*matrix, strict=True)] == [47, 40, 10, 3]
