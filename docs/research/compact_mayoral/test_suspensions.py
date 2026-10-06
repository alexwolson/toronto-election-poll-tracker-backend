"""Suspended Campaign signal (backend issue 43, 2026-10-06): table, kept fraction, model hook.

Run from the backend root:

    uv run python -m pytest docs/research/compact_mayoral/test_suspensions.py -q
"""

from datetime import timedelta

import jax
import numpy as np
import pytest
from numpyro.handlers import seed, substitute, trace

from .hyperpriors import population_hyperpriors
from .model import build_model
from .readings import historical_campaigns
from .suspensions import (
    check_no_post_suspension_offer,
    keep_distribution,
    kept_fraction,
    known_suspensions,
    load_suspensions,
    suspend,
)

jax.config.update("jax_enable_x64", True)


# --------------------------------------------------------------------------- arithmetic


def test_suspend_scales_the_suspended_share_and_keeps_the_others_ratios():
    out = np.asarray(suspend(np.array([0.5, 0.3, 0.2]), (2,), 0.1))
    assert np.allclose(out, [0.6125, 0.3675, 0.02])
    assert np.isclose(out.sum(), 1.0)
    assert np.isclose(out[0] / out[1], 0.5 / 0.3)


def test_suspend_handles_two_candidates_and_a_keep_fraction_per_draw():
    shares = np.array([[0.4, 0.3, 0.2, 0.1], [0.4, 0.3, 0.2, 0.1]])
    out = np.asarray(suspend(shares, (2, 3), np.array([[1.0], [0.5]])))
    assert np.allclose(out[0], shares[0])  # keeping everything changes nothing
    assert np.allclose(out[1, 2:], [0.1, 0.05])
    assert np.allclose(out.sum(axis=1), 1.0)
    assert np.isclose(out[1, 0] / out[1, 1], 0.4 / 0.3)


def test_suspend_without_a_suspended_candidate_is_the_identity():
    shares = np.array([0.6, 0.4])
    assert np.allclose(suspend(shares, (), 0.2), shares)


# --------------------------------------------------------------------------- table


def test_table_holds_the_ten_recorded_cases_with_sources():
    rows = load_suspensions()
    assert len(rows) == 10 and len({r["case_id"] for r in rows}) == 10
    for r in rows:
        assert r["source_announcement"].startswith("https://")
        assert r["source_final"].startswith("https://")
        assert r["announcement_date"] < r["election_date"]


def test_kept_fraction_is_the_final_share_over_the_last_poll_share():
    by_id = {r["case_id"]: r for r in load_suspensions()}
    assert kept_fraction(by_id["toronto-2010-thomson"]) == pytest.approx(0.2313 / 7)
    assert kept_fraction(by_id["montreal-2017-fortier"]) == pytest.approx(1.26 / 5)
    # A last share of 0, or no poll at all, gives no ratio.
    for case in ("toronto-2023-davis", "toronto-2023-mammoliti", "sudbury-2022-bigger"):
        assert kept_fraction(by_id[case]) is None


def test_keep_distribution_is_the_log_mean_and_sample_sd_of_usable_cases():
    rows = load_suspensions()
    mu, sigma = keep_distribution(rows, exclude_cities=("Toronto",))
    logs = np.log([0.4273 / 1.9, 0.3841 / 1.8, 0.2807 / 1.2, 1.0764 / 6, 1.26 / 5])
    assert mu == pytest.approx(logs.mean())
    assert sigma == pytest.approx(logs.std(ddof=1))
    # Thomson and Rossi kept less than the other cities' cases.
    assert keep_distribution(rows)[0] < mu
    # Toronto 2023's rows give no ratio, so leaving out 2010 leaves the other cities.
    assert keep_distribution(rows, exclude_cycles=("toronto_2010",)) == pytest.approx((mu, sigma))


# --------------------------------------------------------------------------- campaigns


def test_known_suspensions_follow_the_forecast_cutoff():
    campaigns = historical_campaigns()
    rows = load_suspensions()
    c2010 = campaigns["toronto_2010"]
    index = {name: i for i, name in enumerate(c2010.names)}
    both = tuple(sorted((index["Sarah Thomson"], index["Rocco Rossi"])))
    assert known_suspensions(c2010, rows, c2010.election_date) == both
    eday = c2010.election_date
    assert known_suspensions(c2010, rows, eday - timedelta(days=14)) == (index["Sarah Thomson"],)
    assert known_suspensions(c2010, rows, eday - timedelta(days=39)) == ()
    c2023 = campaigns["toronto_2023"]
    assert len(known_suspensions(c2023, rows, c2023.election_date)) == 2
    c2014 = campaigns["toronto_2014"]
    assert known_suspensions(c2014, rows, c2014.election_date) == ()


def test_the_corpus_has_no_modelled_post_suspension_reading_naming_the_candidate():
    rows = load_suspensions()
    for c in historical_campaigns().values():
        check_no_post_suspension_offer(c, rows)  # raises if one existed


def test_post_suspension_guard_raises_when_a_selected_reading_names_the_candidate():
    c = historical_campaigns()["toronto_2010"]
    thomson = c.names.index("Sarah Thomson")
    late = [p for p in c.polls if p.days_before_election < 27]
    assert late and all(thomson not in p.offered for p in late)
    named = late[0].__class__(**{**late[0].__dict__, "offered": (*late[0].offered, thomson)})
    forged = c.__class__(**{**c.__dict__, "polls": (*c.polls, named)})
    with pytest.raises(ValueError, match="Sarah Thomson"):
        check_no_post_suspension_offer(forged, load_suspensions())


# --------------------------------------------------------------------------- model


def _trace(model, values):
    with seed(rng_seed=0):
        return trace(substitute(model, data=values)).get_trace()


def test_joint_signal_scales_the_suspended_election_support_before_the_reading():
    c = historical_campaigns()["toronto_2010"]
    suspended = known_suspensions(c, load_suspensions(), c.election_date)
    model = build_model(
        (c,),
        population_hyperpriors(),
        variant="dirichlet",
        suspensions={c.key: suspended},
        keep_prior=(-1.5, 0.1),
    )
    tr = _trace(model, {"log_keep_fraction": np.log(0.2)})
    support = np.asarray(tr["toronto_2010/election_support"]["value"])
    scaled = np.asarray(tr["toronto_2010/election_support_suspended"]["value"])
    assert np.allclose(scaled, suspend(support, suspended, 0.2))
    assert np.isclose(float(tr["keep_fraction"]["value"]), 0.2)


def test_no_signal_sites_without_suspensions_and_a_prior_is_required_with_them():
    c = historical_campaigns()["toronto_2014"]
    tr = _trace(build_model((c,), population_hyperpriors(), variant="dirichlet"), {})
    assert "keep_fraction" not in tr and "log_keep_fraction" not in tr
    with pytest.raises(ValueError):
        build_model((c,), population_hyperpriors(), variant="dirichlet", suspensions={c.key: (0,)})
    with pytest.raises(ValueError):
        build_model(
            (c,),
            population_hyperpriors(),
            variant="isotropic",
            suspensions={c.key: (0,)},
            keep_prior=(-1.5, 0.1),
        )
