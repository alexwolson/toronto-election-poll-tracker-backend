from decimal import Decimal

import pytest

from backend.model.mayoral_evidence_tier import (
    MayoralEvidenceTier,
    MayoralPollSampleEvidence,
    classify_mayoral_evidence_tier,
)
from backend.model.mayoral_publication import (
    Availability,
    compose_mayoral_quantity_publication,
)
from backend.model.mayoral_publication_gates import (
    CHALLENGER_WIN,
    CLOSE_RESULT,
    INCUMBENT_DEFEAT,
)
from backend.model.publication import (
    ErrorInterval,
    SensitivityVariant,
    unavailable_variant,
)

FINAL_FIELD = frozenset({"chow", "bradford", "alexander"})
D = Decimal


def _tier(samples):
    return classify_mayoral_evidence_tier(samples, final_field=FINAL_FIELD)


def _s(sid, pollster, measured=("chow", "bradford", "alexander")):
    return MayoralPollSampleEvidence(sid, pollster, frozenset(measured))


def _variant(label, p, lo, hi):
    return SensitivityVariant(
        label=label,
        probability=D(p),
        error_interval=ErrorInterval(lower=D(lo), upper=D(hi)),
    )


def _agreeing():
    return [
        _variant("base", "0.50", "0.47", "0.53"),
        _variant("tail-high", "0.51", "0.48", "0.54"),
    ]


def test_central_band_remains_available_across_boundaries_and_reports_full_range():
    pub = compose_mayoral_quantity_publication(
        CLOSE_RESULT,
        _tier([_s("a", "Forum")]),
        race_has_incumbent=True,
        central_variant_label="base",
        variants=[
            _variant("base", "0.869", "0.867", "0.871"),
            _variant("tail-high", "0.748", "0.745", "0.751"),
            _variant("incumbency", "0.904", "0.902", "0.906"),
        ],
    )
    assert pub.is_published
    assert pub.band.frequency_statement == "about 4 in 5"
    assert pub.sensitivity_range == (D("0.745"), D("0.906"))


@pytest.mark.parametrize("point", ["0", ".1", ".3", ".5", ".7", ".9", "1"])
def test_central_band_boundary_never_suppresses_a_valid_summary(point):
    pub = compose_mayoral_quantity_publication(
        CLOSE_RESULT,
        _tier([_s("a", "Forum")]),
        race_has_incumbent=True,
        central_variant_label="base",
        variants=[_variant("base", point, point, point), _variant("stress", ".49", ".48", ".50")],
    )
    assert pub.is_published


@pytest.mark.parametrize(
    "point,phrase", [(".01", "less than 1 in 10"), (".99", "more than 9 in 10")]
)
def test_central_summary_preserves_existing_rare_event_wording(point, phrase):
    pub = compose_mayoral_quantity_publication(
        CLOSE_RESULT,
        _tier([_s("a", "Forum")]),
        race_has_incumbent=True,
        central_variant_label="base",
        variants=[_variant("base", point, point, point)],
    )
    assert pub.band.frequency_statement == phrase


@pytest.mark.parametrize(
    "variants",
    [
        [_variant("stress", ".5", ".49", ".51")],
        [_variant("base", ".5", ".49", ".51"), unavailable_variant("stress")],
        [_variant("base", ".5", ".49", ".51"), _variant("base", ".6", ".59", ".61")],
    ],
)
def test_central_range_fails_closed_on_missing_or_ambiguous_computations(variants):
    pub = compose_mayoral_quantity_publication(
        CLOSE_RESULT,
        _tier([_s("a", "Forum")]),
        race_has_incumbent=True,
        central_variant_label="base",
        variants=variants,
    )
    assert not pub.is_published
    assert pub.sensitivity_range is None


def test_pre_final_close_result_is_unavailable_and_shows_m1() -> None:
    # The live 2026 case before nominations close: the field is not yet certified
    # (final_field is None), so no predictive quantity publishes.
    tier = classify_mayoral_evidence_tier([_s("a", "Forum")], final_field=None)
    pub = compose_mayoral_quantity_publication(
        CLOSE_RESULT, tier, race_has_incumbent=True, variants=_agreeing()
    )
    assert pub.availability is Availability.UNAVAILABLE
    assert pub.tier is MayoralEvidenceTier.M1_PRE_FINAL  # tier shown regardless
    assert pub.band is None


def test_open_seat_incumbent_defeat_is_not_applicable() -> None:
    tier = _tier([_s("a", "Forum")])  # M2
    pub = compose_mayoral_quantity_publication(
        INCUMBENT_DEFEAT, tier, race_has_incumbent=False, variants=_agreeing()
    )
    assert pub.availability is Availability.NOT_APPLICABLE
    assert pub.band is None


def test_m2_close_result_publishes_a_band_when_variants_agree() -> None:
    tier = _tier([_s("a", "Forum")])  # M2
    pub = compose_mayoral_quantity_publication(
        CLOSE_RESULT, tier, race_has_incumbent=True, variants=_agreeing()
    )
    assert pub.availability is Availability.AVAILABLE
    assert pub.tier is MayoralEvidenceTier.M2_POST_FINAL
    assert pub.band is not None
    assert pub.band.label == "45–<55%"


def test_m2_falls_back_to_the_coarse_band_when_variants_agree_only_there() -> None:
    # ADR 0049: 0.53/0.62 disagree on the out-of-ten band but both sit in the
    # out-of-five band 50–<70, so the quantity publishes at that coarser resolution.
    tier = _tier([_s("a", "Forum")])  # M2
    pub = compose_mayoral_quantity_publication(
        CLOSE_RESULT,
        tier,
        race_has_incumbent=True,
        variants=[
            _variant("base", "0.53", "0.51", "0.54"),
            _variant("tail-high", "0.62", "0.60", "0.64"),
        ],
    )
    assert pub.availability is Availability.AVAILABLE
    assert pub.band is not None
    assert pub.band.label == "50–<70%"
    assert pub.band.frequency_statement == "about 3 in 5"


def test_m2_unavailable_when_variants_disagree_on_both_grids() -> None:
    # 0.28/0.42 straddle the 0.30 out-of-five boundary, so neither grid can publish.
    tier = _tier([_s("a", "Forum")])  # M2
    pub = compose_mayoral_quantity_publication(
        CLOSE_RESULT,
        tier,
        race_has_incumbent=True,
        variants=[
            _variant("base", "0.28", "0.27", "0.29"),
            _variant("tail-high", "0.42", "0.41", "0.43"),  # different coarse band
        ],
    )
    assert pub.availability is Availability.UNAVAILABLE
    assert pub.band is None


def test_unlocked_but_no_variants_fails_closed() -> None:
    # ADR 0032: an unlocked quantity with no computable variants is unavailable.
    tier = _tier([_s("a", "Forum")])  # M2
    pub = compose_mayoral_quantity_publication(
        CLOSE_RESULT, tier, race_has_incumbent=True, variants=[]
    )
    assert pub.availability is Availability.UNAVAILABLE


def test_unlocked_but_a_variant_cannot_run_fails_closed() -> None:
    tier = _tier([_s("a", "Forum")])  # M2
    pub = compose_mayoral_quantity_publication(
        CLOSE_RESULT,
        tier,
        race_has_incumbent=True,
        variants=[
            _variant("base", "0.50", "0.47", "0.53"),
            unavailable_variant("leave-one-out"),
        ],
    )
    assert pub.availability is Availability.UNAVAILABLE
    assert "leave-one-out" in pub.reason


def test_m3_challenger_win_publishes_for_a_measured_challenger() -> None:
    # Two final-field samples plus a third measuring only chow+bradford: bradford
    # is measured in all three (two final-field), so its Win Probability is M3.
    samples = [
        _s("a", "Forum"),
        _s("b", "Liaison"),
        _s("c", "Mainstreet", ("chow", "bradford")),
    ]
    tier = _tier(samples)
    pub = compose_mayoral_quantity_publication(
        CHALLENGER_WIN,
        tier,
        race_has_incumbent=True,
        candidate_id="bradford",
        variants=_agreeing(),
    )
    assert pub.availability is Availability.AVAILABLE
    assert pub.tier is MayoralEvidenceTier.M3_REPLICATED_POST_FINAL
    assert pub.candidate_id == "bradford"


def test_m3_challenger_win_unavailable_for_an_undermeasured_challenger() -> None:
    samples = [
        _s("a", "Forum"),
        _s("b", "Liaison"),
        _s("c", "Mainstreet", ("chow", "bradford")),
    ]
    tier = _tier(samples)  # field-level M3, but alexander measured in only two
    pub = compose_mayoral_quantity_publication(
        CHALLENGER_WIN,
        tier,
        race_has_incumbent=True,
        candidate_id="alexander",
        variants=_agreeing(),
    )
    assert pub.availability is Availability.UNAVAILABLE
    assert pub.tier is MayoralEvidenceTier.M3_REPLICATED_POST_FINAL
