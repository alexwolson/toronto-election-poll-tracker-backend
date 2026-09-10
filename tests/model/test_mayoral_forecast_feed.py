from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from backend.model.mayoral_evaluation import FullBallotShareDraws
from backend.model.mayoral_forecast_feed import (
    _select_live_final_field_readings,
    _variant_predictors,
    build_mayoral_forecast_feed,
    forecast_quantities,
)
from backend.model.poll_sources import load_poll_source_bundle
from backend.model.publication_manifest import load_live_cycle

ROOT = Path(__file__).resolve().parents[2]

CANDS = ("chow", "bradford", "alexander")
DRAWS = FullBallotShareDraws(
    candidate_ids=CANDS,
    draws=(
        (0.50, 0.30, 0.20),  # chow wins, margin 0.20 (not close)
        (0.45, 0.40, 0.15),  # chow wins, margin 0.05 (close)
        (0.40, 0.45, 0.15),  # bradford wins, margin 0.05 (close)
        (0.50, 0.25, 0.25),  # chow wins, margin 0.25 (not close)
    ),
)


def test_candidate_win_probabilities_are_draw_fractions_summing_to_one() -> None:
    q = forecast_quantities(DRAWS, incumbent_candidate_id="chow")
    assert q.candidate_win["chow"].probability == 0.75
    assert q.candidate_win["bradford"].probability == 0.25
    assert q.candidate_win["alexander"].probability == 0.0
    total = sum(e.probability for e in q.candidate_win.values())
    assert abs(total - 1.0) < 1e-9


def test_close_result_probability_counts_within_threshold_margins() -> None:
    q = forecast_quantities(DRAWS, incumbent_candidate_id="chow")
    assert q.close_result.probability == 0.5  # two of four draws within 0.05


def test_margin_distribution_is_a_normalized_nonnegative_density() -> None:
    # The winning-margin distribution feeds the homepage density panel: a smoothed
    # (reflected-KDE) curve over the winner-minus-runner-up share gap.
    dist = forecast_quantities(DRAWS, incumbent_candidate_id="chow").margin_distribution
    xs = np.asarray(dist.x, dtype=float)
    dens = np.asarray(dist.density, dtype=float)
    assert len(xs) == len(dens) >= 50  # a smooth curve, not a handful of points
    assert xs[0] == 0.0  # margins are bounded below at 0
    assert np.all(np.diff(xs) > 0)  # strictly increasing grid
    assert np.all(dens >= 0.0)  # a density is non-negative everywhere
    # Reflected at the 0 boundary, so no mass leaks negative and it integrates ~1.
    assert abs(float(np.trapezoid(dens, xs)) - 1.0) < 0.05


def test_winner_margin_densities_are_joint_subsets_of_the_aggregate() -> None:
    q = forecast_quantities(DRAWS, incumbent_candidate_id="chow")
    dist = q.margin_distribution
    assert set(dist.by_winner) == {"chow", "bradford"}
    assert dist.by_winner["chow"].draw_weight == 3.0
    assert dist.by_winner["bradford"].draw_weight == 1.0

    combined = sum(
        (np.asarray(component.density) for component in dist.by_winner.values()),
        start=np.zeros(len(dist.x)),
    )
    assert np.allclose(combined, np.asarray(dist.density), rtol=1e-12, atol=1e-12)

    chow_mass = float(np.trapezoid(dist.by_winner["chow"].density, dist.x))
    bradford_mass = float(np.trapezoid(dist.by_winner["bradford"].density, dist.x))
    assert abs(chow_mass - 0.75) < 0.05
    assert abs(bradford_mass - 0.25) < 0.05


def test_margin_feed_omits_zero_winners_and_groups_non_public_winners_as_other() -> None:
    draws = FullBallotShareDraws(
        candidate_ids=("chow", "bradford", "alexander", "outsider"),
        draws=(
            (0.50, 0.30, 0.15, 0.05),
            (0.30, 0.45, 0.15, 0.10),
            (0.25, 0.20, 0.15, 0.40),
        ),
    )
    dist = forecast_quantities(draws, incumbent_candidate_id="chow").margin_distribution
    feed = dist.to_feed(
        0.05,
        public_candidate_ids=("chow", "bradford", "alexander"),
    )

    assert set(feed["by_winner"]) == {"chow", "bradford", "other"}
    assert feed["by_winner"]["other"]["draw_weight"] == 1.0
    assert "alexander" not in feed["by_winner"]
    combined = sum(
        (np.asarray(component["density"]) for component in feed["by_winner"].values()),
        start=np.zeros(len(feed["x"])),
    )
    assert np.allclose(combined, np.asarray(feed["density"]), rtol=1e-12, atol=1e-12)


def test_incumbent_defeat_is_one_minus_incumbent_win() -> None:
    q = forecast_quantities(DRAWS, incumbent_candidate_id="chow")
    assert q.incumbent_defeat.probability == 0.25
    assert forecast_quantities(DRAWS, incumbent_candidate_id=None).incumbent_defeat is None


def test_error_intervals_contain_the_estimate_and_stay_in_unit_interval() -> None:
    q = forecast_quantities(DRAWS, incumbent_candidate_id="chow")
    for e in [*q.candidate_win.values(), q.close_result, q.incumbent_defeat]:
        assert 0.0 <= e.interval_lower <= e.probability <= e.interval_upper <= 1.0


def test_a_tied_top_share_splits_the_winner_weight() -> None:
    tied = FullBallotShareDraws(candidate_ids=("a", "b"), draws=((0.5, 0.5), (0.5, 0.5)))
    q = forecast_quantities(tied, incumbent_candidate_id=None)
    assert q.candidate_win["a"].probability == 0.5
    assert q.candidate_win["b"].probability == 0.5
    assert q.margin_distribution.by_winner["a"].draw_weight == 1.0
    assert q.margin_distribution.by_winner["b"].draw_weight == 1.0
    assert np.allclose(
        q.margin_distribution.by_winner["a"].density,
        np.asarray(q.margin_distribution.density) / 2.0,
    )


def _stub(pollsters):
    return SimpleNamespace(
        final_field_sample_ids=("s1", "s2", "s3"),
        final_field_pollsters=tuple(pollsters),
    )


def test_leave_one_pollster_out_is_not_applicable_below_three_pollsters() -> None:
    # ADR 0048: with < 3 pollsters, dropping one leaves too little to refit, so
    # the variant is omitted rather than failing the gate.
    two = {label for label, _ in _variant_predictors(_stub(("Forum", "Liaison")), ROOT)}
    assert not any(label.startswith("leave-out-pollster:") for label in two)
    # the rest of the mandatory suite is still present
    assert {
        "bridge-base",
        "comparator-baseline",
        "tail-low",
        "tail-high",
        "incumbency-prior",
    } <= two

    three = {
        label for label, _ in _variant_predictors(_stub(("Forum", "Liaison", "Mainstreet")), ROOT)
    }
    assert sum(label.startswith("leave-out-pollster:") for label in three) == 3


def test_uncertified_forecast_is_unavailable_at_tier_m1() -> None:
    # Before the field is certified the tier is M1 and every predictive quantity is
    # tier-gated Unavailable (no variant suite is run).
    live_cycle = {
        **load_live_cycle(ROOT / "data/raw/elections/live_cycle.json"),
        "field_certified": False,
        # This unit test runs against the repository's legacy poll fixture. The
        # production refresh hydrates these as canonical Person IDs first.
        "viable_field": ["chow", "bradford", "alexander"],
        "incumbent_candidate_id": "chow",
    }
    feed = build_mayoral_forecast_feed(ROOT, live_cycle, polls_dir=ROOT / "data/raw/polls")
    assert feed["evidence_tier"] == "M1 — Pre-Final Polling"
    assert feed["close_result"]["availability"] == "Forecast Unavailable"
    assert all(
        card["availability"] == "Forecast Unavailable" for card in feed["candidate_win"].values()
    )
    # Respect the gate: when the close-result summary is withheld, we do not leak
    # the margin distribution's shape either.
    assert feed["margin_distribution"] is None
    assert len(feed["final_field_readings"]) == len(feed["final_field_samples"])
    assert "forum_20260729_mayor_alexander" in feed["final_field_readings"]


def test_live_selection_isolates_an_exact_field_from_dependent_alternates() -> None:
    bundle = load_poll_source_bundle(ROOT / "data/raw/polls")
    sample_id = "forum-2026-07-29"
    sample = next(row for row in bundle.poll_samples if row.poll_sample_id == sample_id)
    head_to_head = next(
        row for row in bundle.poll_readings if row.poll_reading_id == "forum_20260729_mayor_primary"
    )
    exact = next(
        row
        for row in bundle.poll_readings
        if row.poll_reading_id == "forum_20260729_mayor_alexander"
    )
    source_responses = tuple(
        row for row in bundle.poll_responses if row.poll_reading_id == exact.poll_reading_id
    )
    viable = frozenset(
        row.candidate_id
        for row in source_responses
        if row.response_kind == "candidate" and row.candidate_id is not None
    )
    broader = replace(exact, poll_reading_id="forum_20260729_mayor_hypothetical_broader")
    broader_responses = tuple(
        replace(row, poll_reading_id=broader.poll_reading_id) for row in source_responses
    )
    template = next(row for row in source_responses if row.response_kind == "candidate")
    extra = replace(
        template,
        poll_reading_id=broader.poll_reading_id,
        response_option_id="hypothetical-extra",
        candidate_id="hypothetical-extra",
        candidate_name="Hypothetical Extra",
        response_label="Hypothetical Extra",
        option_order=99,
        reported_value="10",
        share=Decimal("0.10"),
    )
    reading_ids = {head_to_head.poll_reading_id, exact.poll_reading_id}
    test_bundle = replace(
        bundle,
        poll_samples=(sample,),
        poll_readings=(head_to_head, exact, broader),
        poll_responses=(
            *(row for row in bundle.poll_responses if row.poll_reading_id in reading_ids),
            *broader_responses,
            extra,
        ),
    )

    selected = _select_live_final_field_readings(
        test_bundle,
        (sample,),
        viable,
        endpoint_cycle="toronto_2026",
    )

    assert [row.poll_reading_id for row in selected] == [exact.poll_reading_id]
    assert selected[0].candidate_field == tuple(sorted(viable))
