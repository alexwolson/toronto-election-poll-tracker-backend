"""Repeat-firm house-effect anchor (pre-registered 2026-10-13, research/repeat-firm-anchor)."""

from datetime import date

import jax
import numpy as np
import pytest
from numpyro.handlers import seed, substitute, trace

from backend.model.compact_mayoral.hyperpriors import population_hyperpriors
from backend.model.compact_mayoral.model import build_model, prepare
from backend.model.compact_mayoral.readings import CampaignPolls, Poll

jax.config.update("jax_enable_x64", True)


def campaign(firms, key="k", online=()):
    polls = tuple(
        Poll(
            f"{key}-{i}",
            f"{key}-{i}",
            firm,
            60 - 5 * i,
            900.0,
            (0, 1, 2),
            (0.5, 0.4, 0.1),
            online_only=i in online,
        )
        for i, firm in enumerate(firms)
    )
    return CampaignPolls(
        key, ("c0", "c1", "c2"), ("Zero", "One", "Two"), date(2030, 1, 1), polls, None, None, (0, 1)
    )


def traced(model, firm_z):
    with seed(rng_seed=0):
        tr = trace(substitute(model, data=firm_z)).get_trace()
    return tr


# Firms sort as A, B, C: A has three polls, B two, C one.
THREE_FIRMS = ("A", "B", "A", "C", "B", "A")
FIRM_Z = np.array([[0.7, -0.2], [-1.1, 0.4], [1.5, 0.9]])


def test_prepare_marks_firms_with_two_or_more_polls() -> None:
    assert prepare(campaign(THREE_FIRMS)).repeat_firms.tolist() == [True, True, False]
    assert prepare(campaign(("A", "B", "C"))).repeat_firms.tolist() == [False, False, False]


def test_repeat_firm_anchor_centres_house_effects_on_repeat_firms() -> None:
    model = build_model(
        (campaign(THREE_FIRMS),), population_hyperpriors(), house_anchor="repeat_firms"
    )
    tr = traced(model, {"k/firm_z": FIRM_Z})
    tau = float(tr["tau_firm"]["value"])
    raw = FIRM_Z * tau / np.sqrt(2.0)
    firm = np.asarray(tr["k/firm"]["value"])
    np.testing.assert_allclose(firm, raw - raw[:2].mean(axis=0))
    np.testing.assert_allclose(firm[:2].sum(axis=0), 0.0, atol=1e-12)


@pytest.mark.parametrize("firms", [("A", "B", "C"), ("A", "A", "B", "C")])
def test_fewer_than_two_repeat_firms_leaves_house_effects_unchanged(firms) -> None:
    c = campaign(firms)
    z = FIRM_Z[: prepare(c).firm_count]
    anchored = traced(
        build_model((c,), population_hyperpriors(), house_anchor="repeat_firms"), {"k/firm_z": z}
    )
    prior = traced(build_model((c,), population_hyperpriors()), {"k/firm_z": z})
    np.testing.assert_array_equal(anchored["k/firm"]["value"], prior["k/firm"]["value"])


def test_default_anchor_is_the_published_prior_frame() -> None:
    c = campaign(THREE_FIRMS)
    default = traced(build_model((c,), population_hyperpriors()), {"k/firm_z": FIRM_Z})
    explicit = traced(
        build_model((c,), population_hyperpriors(), house_anchor="prior"), {"k/firm_z": FIRM_Z}
    )
    tau = float(default["tau_firm"]["value"])
    np.testing.assert_allclose(default["k/firm"]["value"], FIRM_Z * tau / np.sqrt(2.0))
    np.testing.assert_array_equal(default["k/firm"]["value"], explicit["k/firm"]["value"])


def test_unknown_anchor_is_rejected() -> None:
    with pytest.raises(ValueError, match="house_anchor"):
        build_model((campaign(THREE_FIRMS),), population_hyperpriors(), house_anchor="median")


def test_repeat_firm_anchor_compiles_and_samples() -> None:
    from backend.model.compact_mayoral.sampling import FitSettings, fit_joint

    fast = FitSettings(warmup=20, draws=20, chains=1, seed=1, target_accept=0.9)
    result = fit_joint(
        (campaign(THREE_FIRMS),),
        population_hyperpriors(),
        settings=fast,
        house_anchor="repeat_firms",
    )
    firm = np.asarray(result.draws["k/firm"])
    np.testing.assert_allclose(firm[:, :2].sum(axis=1), 0.0, atol=1e-9)


# Firms sort as A, B, C. B's only poll is online; C has one online and one telephone poll.
MIXED_MODES = ("A", "B", "A", "C", "C")
ONLINE_POLLS = (1, 3)


def test_prepare_marks_firms_whose_polls_are_all_online_only() -> None:
    c = campaign(MIXED_MODES, online=ONLINE_POLLS)
    assert prepare(c).online_firms.tolist() == [False, True, False]
    assert prepare(campaign(MIXED_MODES)).online_firms.tolist() == [False, False, False]


def test_non_online_anchor_centres_house_effects_on_firms_that_are_not_online_only() -> None:
    model = build_model(
        (campaign(MIXED_MODES, online=ONLINE_POLLS),),
        population_hyperpriors(),
        house_anchor="non_online",
    )
    tr = traced(model, {"k/firm_z": FIRM_Z})
    raw = FIRM_Z * float(tr["tau_firm"]["value"]) / np.sqrt(2.0)
    firm = np.asarray(tr["k/firm"]["value"])
    np.testing.assert_allclose(firm, raw - raw[[0, 2]].mean(axis=0))
    np.testing.assert_allclose(firm[[0, 2]].sum(axis=0), 0.0, atol=1e-12)


@pytest.mark.parametrize("online", [(), (0, 1, 2, 3, 4)])
def test_non_online_anchor_changes_nothing_without_both_kinds_of_firm(online) -> None:
    c = campaign(MIXED_MODES, online=online)
    anchored = traced(
        build_model((c,), population_hyperpriors(), house_anchor="non_online"), {"k/firm_z": FIRM_Z}
    )
    prior = traced(build_model((c,), population_hyperpriors()), {"k/firm_z": FIRM_Z})
    np.testing.assert_array_equal(anchored["k/firm"]["value"], prior["k/firm"]["value"])


def test_non_online_anchor_compiles_and_samples() -> None:
    from backend.model.compact_mayoral.sampling import FitSettings, fit_joint

    fast = FitSettings(warmup=20, draws=20, chains=1, seed=1, target_accept=0.9)
    result = fit_joint(
        (campaign(MIXED_MODES, online=ONLINE_POLLS),),
        population_hyperpriors(),
        settings=fast,
        house_anchor="non_online",
    )
    firm = np.asarray(result.draws["k/firm"])
    np.testing.assert_allclose(firm[:, [0, 2]].sum(axis=1), 0.0, atol=1e-9)


def test_production_fits_anchor_house_effects_on_non_online_firms() -> None:
    from backend.model.compact_mayoral.sampling import (
        PRODUCTION_HOUSE_ANCHOR,
        FitSettings,
        fit_joint,
    )

    assert PRODUCTION_HOUSE_ANCHOR == "non_online"  # ADR 0064
    fast = FitSettings(warmup=20, draws=20, chains=1, seed=1, target_accept=0.9)
    result = fit_joint(
        (campaign(MIXED_MODES, online=ONLINE_POLLS),), population_hyperpriors(), settings=fast
    )
    firm = np.asarray(result.draws["k/firm"])
    np.testing.assert_allclose(firm[:, [0, 2]].sum(axis=1), 0.0, atol=1e-9)
