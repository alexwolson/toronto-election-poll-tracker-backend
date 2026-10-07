"""Rule logic for the reactive versions C2/C3 (backend issue 51, phase 1).

Run from the backend root:

    uv run python -m pytest docs/research/compact_mayoral/test_reactive.py -q
"""

import dataclasses
from datetime import date, timedelta

import jax
import numpy as np
from numpyro.handlers import seed, substitute, trace

from .hyperpriors import population_hyperpriors
from .model import build_model, helmert_basis
from .reactive import (
    SHIFT_SCALE,
    ExitSpec,
    exit_transform,
    set_aside_after_exits,
    target_exits,
)
from .readings import historical_campaigns, with_horizon
from .suspensions import load_suspensions, suspend

jax.config.update("jax_enable_x64", True)

S = np.array([[0.50, 0.30, 0.20], [0.48, 0.32, 0.20], [0.45, 0.35, 0.20]])
POST = np.array([False, True, True])


def test_proportional_allocation_at_the_exit_is_s2():
    centre = S[1, :2] / S[1, :2].sum()
    out = np.asarray(exit_transform(S, POST, 2, [0, 1], 0.15, centre))
    assert np.allclose(out[1], suspend(S[1], (2,), 0.15))
    assert np.allclose(out[0], S[0])  # pre-exit untouched
    assert np.allclose(out.sum(axis=1), 1.0)
    assert np.allclose(out[1:, 2], 0.15 * S[1:, 2])


def test_allocation_moves_the_freed_share_only():
    out = np.asarray(exit_transform(S, POST, 2, [0, 1], 0.0, np.array([0.0, 1.0])))
    assert np.allclose(out[2], [0.45, 0.55, 0.0])  # all of the freed share to candidate 1


def test_shift_changes_the_remaining_composition_but_not_the_totals():
    shift = helmert_basis(2) @ np.array([0.3])
    base = np.asarray(exit_transform(S, POST, 2, [0, 1], 0.2, np.array([0.5, 0.5])))
    out = np.asarray(exit_transform(S, POST, 2, [0, 1], 0.2, np.array([0.5, 0.5]), shift))
    assert np.allclose(out[1:, :2].sum(axis=1), base[1:, :2].sum(axis=1))
    assert np.allclose(out[1:, 2], base[1:, 2])
    ratio = (out[1, 0] / out[1, 1]) / (base[1, 0] / base[1, 1])
    assert np.isclose(np.log(ratio), shift[0] - shift[1])


def test_shift_scale_is_eight_points_of_two_way_share_at_even_support():
    assert np.isclose(0.25 * np.sqrt(2.0) * SHIFT_SCALE, 0.08)


def test_target_exits_follow_the_cutoff_and_date_order():
    rows = load_suspensions()
    c = historical_campaigns()["toronto_2010"]
    e14 = target_exits(c, rows, c.election_date - timedelta(days=14), (-1.8, 0.7))
    assert [(e.name, e.day) for e in e14] == [("Sarah Thomson", 27)]
    e7 = target_exits(c, rows, c.election_date - timedelta(days=7), (-1.8, 0.7))
    assert [(e.name, e.day) for e in e7] == [("Sarah Thomson", 27), ("Rocco Rossi", 12)]
    c23 = historical_campaigns()["toronto_2023"]
    assert target_exits(c23, rows, c23.election_date - timedelta(days=7), (-1.8, 0.7)) == ()


def test_set_aside_drops_the_departed_from_post_exit_readings_only():
    c = with_horizon(historical_campaigns()["toronto_2010"], 14)
    t = c.names.index("Sarah Thomson")
    exits = (ExitSpec(t, "Sarah Thomson", 35, -1.8, 0.7),)  # forged early exit
    out = set_aside_after_exits(c, exits)
    for before, after in zip(c.polls, out.polls):
        if before.days_before_election <= 35:
            assert t not in after.offered
            assert np.isclose(sum(after.shares), 1.0)
        else:
            assert after == before


def test_model_reads_election_day_from_the_post_exit_latent():
    rows = load_suspensions()
    c = with_horizon(historical_campaigns()["toronto_2010"], 14)
    c = dataclasses.replace(c, outcome_shares=None, outcome_tail=None)
    exits = target_exits(c, rows, c.election_date - timedelta(days=14), (-1.8, 0.7))
    model = build_model(
        (c,),
        population_hyperpriors(),
        variant="dirichlet",
        reactive={c.key: exits},
        shift_scale=SHIFT_SCALE,
    )
    with seed(rng_seed=0):
        tr = trace(substitute(model, data={"toronto_2010/log_keep_0": np.log(0.2)})).get_trace()
    latent = np.asarray(tr["toronto_2010/post_exit_support"]["value"])
    support = np.asarray(tr["toronto_2010/election_support"]["value"])
    assert np.allclose(support, latent[-1])
    assert np.isclose(float(tr["toronto_2010/keep_fraction_0"]["value"]), 0.2)
    for site in ("allocation_0", "shift_sigma_0", "shift_z_0", "shift_0"):
        assert f"toronto_2010/{site}" in tr
    plain = build_model((c,), population_hyperpriors(), variant="dirichlet")
    with seed(rng_seed=0):
        tr0 = trace(plain).get_trace()
    assert not any("allocation" in k or "post_exit" in k for k in tr0)
    assert date(2010, 9, 28) == c.election_date - timedelta(days=exits[0].day)
