from pathlib import Path

import pytest

from backend.analysis.consolidation import calculate_consolidation, compare_pools
from backend.analysis.endorsement_scenarios import build_analysis

BASELINE = {"chow": 50.0, "bradford": 39.0, "alexander": 8.0, "residual": 3.0}


def test_same_fraction_of_rival_support_produces_different_gains():
    bradford = calculate_consolidation(BASELINE, "bradford", 0.5)
    alexander = calculate_consolidation(BASELINE, "alexander", 0.5)

    assert bradford["gain_pp"] == 4
    assert alexander["gain_pp"] == 19.5
    assert bradford["shares"]["bradford"] == 43
    assert alexander["shares"]["alexander"] == 27.5
    assert alexander["rival_fraction_to_tie_pair"] == pytest.approx(15.5 / 39)
    assert bradford["rival_fraction_to_tie_pair"] == 0
    for row in (bradford, alexander):
        assert sum(row["shares"].values()) == pytest.approx(100)
        assert row["shares"]["chow"] == 50
        assert row["shares"]["residual"] == 3
        assert row["pool_share_pp"] == 47
        assert row["recipient_pool_fraction_after"] > row["recipient_pool_fraction_before"]


def test_full_consolidation_has_a_common_ceiling_and_outside_pool_requirement():
    for recipient in ("bradford", "alexander"):
        row = calculate_consolidation(BASELINE, recipient, 1)
        assert row["shares"][recipient] == 47
        assert row["recipient_margin_pp"] == -3
        assert row["full_consolidation_margin_pp"] == -3
        assert row["tie_reachable"] is False
        assert row["chow_transfer_to_tie_after_full_pp"] == 1.5
        assert row["chow_transfer_to_tie_pp"] == 1.5


def test_lead_threshold_checks_the_other_challenger_too():
    base = {"chow": 20, "bradford": 60, "alexander": 10, "residual": 10}
    row = calculate_consolidation(base, "alexander", 0)
    assert row["rival_fraction_to_tie"] == pytest.approx(25 / 60)
    assert row["chow_transfer_to_tie_pp"] is None  # Chow cannot supply the 50 needed.
    at_tie = calculate_consolidation(base, "alexander", row["rival_fraction_to_tie"])
    assert at_tie["recipient_margin_pp"] == pytest.approx(0)


@pytest.mark.parametrize("fraction", [-0.1, 1.1, float("nan"), float("inf")])
def test_invalid_fraction_is_rejected(fraction):
    with pytest.raises(ValueError):
        calculate_consolidation(BASELINE, "bradford", fraction)


def test_empty_rival_pool_is_explicit_and_needs_no_division_by_zero():
    base = {"chow": 60, "bradford": 0, "alexander": 0, "residual": 40}
    row = calculate_consolidation(base, "bradford", 1)
    assert row["gain_pp"] == 0
    assert row["recipient_pool_fraction_before"] is None
    assert row["rival_fraction_to_tie"] is None
    assert not row["tie_reachable"]


def test_pool_growth_does_not_imply_individual_transfers_from_the_rival_pool():
    row = compare_pools(
        {"bailao": 12, "saunders": 16, "furey": 10, "bradford": 4},
        {"bailao": 17, "saunders": 16, "furey": 11, "bradford": 4},
    )
    assert row["recipient_change_pp"] == 5
    assert row["rival_change_pp"] == 1
    assert row["pool_change_pp"] == 6
    assert row["gap_closed_fraction"] == pytest.approx(0.09583333333)
    assert row["rival_net_decline_fraction"] == pytest.approx(-1 / 30)
    assert row["concentration_component_pp"] + row["pool_growth_component_pp"] == (
        pytest.approx(5)
    )


def test_historical_transcriptions_and_dated_2026_ceiling_are_reproduced():
    report = build_analysis(Path(__file__).resolve().parents[2])
    analysis = report["consolidation"]
    forum, liaison, last = analysis["historical_comparisons"]
    assert forum["gap_closed_fraction"] == pytest.approx(0.16772959184)
    assert liaison["gap_closed_fraction"] == pytest.approx(0.09583333333)
    assert last["gap_closed_fraction"] == pytest.approx(0.22857142857)
    assert forum["rival_change_pp"] == -3
    assert analysis["historical_result"]["recipient_pool_fraction"] == pytest.approx(
        235175 / 342495
    )
    trends = analysis["concentration_pretrends"]
    assert trends[0]["n_polls"] == 2
    assert trends[0]["projected_pool_fraction"] == pytest.approx(0.3277777778)
    assert trends[1]["n_polls"] == 3
    assert len(analysis["scenarios"]) == 404
    full = [r for r in analysis["scenarios"] if r["rival_fraction"] == 1]
    assert len(full) == 4
    for row in full:
        if row["baseline_id"] == "pallas-2026-08-21":
            assert row["recipient_margin_pp"] == pytest.approx(-2.6973026973)
            assert not row["tie_reachable"]
        else:
            assert row["recipient_margin_pp"] == pytest.approx(0)
            assert row["rival_fraction_to_tie"] == pytest.approx(1)
    assert len(analysis["input_sha256"]) == 64
