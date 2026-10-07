"""C2, the learned exit allocation for a Suspended Campaign in the forecast campaign.

Pre-registered at 9a1ddef (``docs/research/reactive-allocation-2026-10-07.md``) and
adopted as the only forecast model (backend issue 49).
"""

import dataclasses
from datetime import date, timedelta

import jax
import numpy as np
import pytest
from numpyro.handlers import seed, substitute, trace
from numpyro.infer.util import log_density

from backend.model.compact_mayoral.exits import (
    ALLOCATION_CONCENTRATION,
    Exit,
    exit_transform,
    kept_fraction,
    kept_fraction_prior,
    load_cases,
)
from backend.model.compact_mayoral.hyperpriors import population_hyperpriors
from backend.model.compact_mayoral.model import build_model, prepare
from backend.model.compact_mayoral.readings import CampaignPolls, Poll

jax.config.update("jax_enable_x64", True)

S = np.array([[0.50, 0.30, 0.20], [0.48, 0.32, 0.20], [0.45, 0.35, 0.20]])
POST = np.array([False, True, True])


def s2_suspend(shares, indices, keep):
    """S2's ``suspend`` (research/suspension-signal, suspensions.py), kept here as the
    reference only: the suspended shares times ``keep``, the others rescaled to sum to 1."""
    mask = np.zeros(shares.shape[-1])
    mask[list(indices)] = 1.0
    suspended = (shares * mask).sum(axis=-1, keepdims=True)
    others = (1.0 - keep * suspended) / (1.0 - suspended)
    return shares * mask * keep + shares * (1.0 - mask) * others


def test_proportional_allocation_at_the_exit_equals_s2() -> None:
    centre = S[1, :2] / S[1, :2].sum()
    out = np.asarray(exit_transform(S, POST, 2, [0, 1], 0.15, centre))
    assert np.allclose(out[1], s2_suspend(S[1], (2,), 0.15))
    assert np.allclose(out[0], S[0])  # pre-exit dates untouched
    assert np.allclose(out.sum(axis=1), 1.0)
    assert np.allclose(out[1:, 2], 0.15 * S[1:, 2])


def test_allocation_moves_the_freed_share_only() -> None:
    out = np.asarray(exit_transform(S, POST, 2, [0, 1], 0.0, np.array([0.0, 1.0])))
    assert np.allclose(out[2], [0.45, 0.55, 0.0])  # the whole freed share to candidate 1
    assert np.allclose(out[0], S[0])


def test_the_ten_case_table_gives_the_kept_fraction_prior() -> None:
    rows = load_cases()
    assert len(rows) == 10 and len({r["case_id"] for r in rows}) == 10
    for row in rows:
        assert row["source_announcement"].startswith("http")
        assert row["source_final"].startswith("http")
    used = [r for r in rows if kept_fraction(r) is not None]
    assert len(used) == 7
    assert {r["case_id"] for r in rows if kept_fraction(r) is None} == {
        "sudbury-2022-bigger",  # no public poll
        "toronto-2023-davis",  # last poll share 0
        "toronto-2023-mammoliti",
    }
    thomson = next(r for r in rows if r["case_id"] == "toronto-2010-thomson")
    assert kept_fraction(thomson) == pytest.approx(0.2313 / 7)
    mu, sigma = kept_fraction_prior(rows)
    assert mu == pytest.approx(-1.8382, abs=5e-5) and sigma == pytest.approx(0.7132, abs=5e-5)
    assert ALLOCATION_CONCENTRATION == 4.0


def synthetic(key="s", outcome=None, tail=None, exits=()):
    polls = tuple(
        Poll(
            f"{key}-{i}",
            f"{key}-{i}",
            ("A", "B")[i % 2],
            60 - 9 * i,
            900.0,
            (0, 1, 2),
            (0.5 - 0.01 * i, 0.4 + 0.005 * i, 0.1 + 0.005 * i),
        )
        for i in range(5)
    )
    return CampaignPolls(
        key,
        ("c0", "c1", "c2"),
        ("Zero", "One", "Two"),
        date(2030, 1, 1),
        polls,
        outcome,
        tail,
        (0, 1),
        exits,
    )


def _exit(day=20, keep=(-1.8, 0.7)):
    return Exit(
        candidate=2,
        suspended_on=date(2030, 1, 1) - timedelta(days=day),
        day=day,
        keep_mu=keep[0],
        keep_sigma=keep[1],
    )


def _with_post_exit_poll(campaign: CampaignPolls) -> CampaignPolls:
    """Add a Post-Suspension Reading 15 days out over the two remaining candidates."""
    post = Poll("post", "post", "A", 15, 800.0, (0, 1), (0.52, 0.48))
    return dataclasses.replace(campaign, polls=(*campaign.polls, post))


@pytest.mark.parametrize(
    ("variant", "expected_lp", "expected_full"),
    [
        (
            "dirichlet",
            -4595.5385595239595,
            (5.910127917871473e-06, 0.9571333339751301, 3.437665075797347e-08),
        ),
        (
            "isotropic",
            -4617.858245965683,
            (0.11042419287397819, 0.3499185669084573, 0.4967965186972632),
        ),
    ],
)
def test_without_an_exit_the_model_is_todays_production_model(
    variant, expected_lp, expected_full
) -> None:
    # Golden values computed with the production model before C2 was added
    # (origin/main d056248), at the same seeded prior point: with no Suspended
    # Campaign before the cutoff, the log density and the draws are unchanged.
    model = build_model(
        (synthetic("obs", (0.48, 0.42, 0.10), 0.03), synthetic("pred")),
        population_hyperpriors(),
        variant=variant,
    )
    with seed(rng_seed=11):
        tr = trace(model).get_trace()
    params = {
        k: v["value"] for k, v in tr.items() if v["type"] == "sample" and not v["is_observed"]
    }
    lp, _ = log_density(model, (), {}, params)
    assert float(lp) == pytest.approx(expected_lp, rel=1e-10)
    assert np.allclose(np.asarray(tr["pred/full_ballot"]["value"]), expected_full, rtol=1e-8)
    assert not any("allocation" in k or "keep" in k or "post_exit" in k for k in tr)


def test_the_exit_adds_a_latent_date_without_adding_readings() -> None:
    plain = prepare(synthetic())
    exited = prepare(synthetic(exits=(_exit(day=20),)))
    assert 20 not in plain.dates and 20 in exited.dates
    assert len(exited.dates) == len(plain.dates) + 1
    assert exited.poll_time.shape == plain.poll_time.shape
    assert np.array_equal(plain.composition, exited.composition)


def test_post_exit_readings_and_election_day_read_the_transformed_latent() -> None:
    campaign = _with_post_exit_poll(synthetic("fc", exits=(_exit(day=20),)))
    model = build_model(
        (synthetic("obs", (0.48, 0.42, 0.10), 0.03), campaign),
        population_hyperpriors(),
        variant="dirichlet",
    )
    with seed(rng_seed=0):
        tr = trace(substitute(model, data={"fc/log_keep_0": np.log(0.2)})).get_trace()
    latent = np.asarray(tr["fc/post_exit_support"]["value"])
    P = prepare(campaign)
    contrasts = np.asarray(tr["fc/contrasts"]["value"])
    raw = np.exp(contrasts @ P.basis.T)
    raw = raw / raw.sum(axis=1, keepdims=True)
    pre = P.dates > 20
    assert np.allclose(latent[pre], raw[pre])  # pre-exit dates untouched
    node = int(np.flatnonzero(P.dates == 20)[0])
    allocation = np.asarray(tr["fc/allocation_0"]["value"])
    centre = raw[node, :2] / raw[node, :2].sum()
    # The allocation prior is Dirichlet(4 x the proportional split at the exit node).
    assert np.allclose(np.asarray(tr["fc/allocation_0"]["fn"].concentration), 4.0 * centre)
    expected = np.asarray(exit_transform(raw, ~pre, 2, [0, 1], 0.2, allocation))
    assert np.allclose(latent, expected)
    assert np.isclose(float(tr["fc/keep_fraction_0"]["value"]), 0.2)
    # Election day and today's estimate read the transformed latent.
    assert np.allclose(tr["fc/election_support"]["value"], latent[-1])
    assert np.allclose(tr["fc/current"]["value"], latent[P.current_time])
    # The post-exit reading's mean is the transformed latent (house effect A), offered
    # over the two remaining candidates only.
    poll = tr["fc/poll"]
    firm = np.asarray(tr["fc/firm"]["value"]) @ P.basis.T
    i = len(campaign.polls) - 1
    logits = np.log(latent[P.poll_time[i]]) + firm[P.poll_firm[i]]
    p = np.exp(logits[:2]) / np.exp(logits[:2]).sum()
    concentration = np.asarray(poll["fn"].concentration)[i]
    assert np.allclose(concentration[:2] / concentration[:2].sum(), p)
    assert not P.mask[i, 2]
    # Training campaigns are fitted exactly as before: no exit sites.
    assert not any(k.startswith("obs/") and ("allocation" in k or "keep" in k) for k in tr)


def test_isotropic_refit_centres_election_day_on_the_transformed_latent() -> None:
    campaign = synthetic("fc", exits=(_exit(day=20),))
    model = build_model((campaign,), population_hyperpriors(), variant="isotropic")
    zero = {"fc/election_z": np.zeros(2), "fc/log_keep_0": np.log(0.3)}
    with seed(rng_seed=0):
        tr = trace(substitute(model, data=zero)).get_trace()
    latent = np.asarray(tr["fc/post_exit_support"]["value"])
    # With a zero election-day shock the named result is the transformed latent.
    assert np.allclose(tr["fc/named_result"]["value"], latent[-1])


def test_the_kept_fraction_prior_and_cap_follow_the_exit() -> None:
    campaign = synthetic("fc", exits=(_exit(day=20, keep=(-1.5, 0.3)),))
    model = build_model((campaign,), population_hyperpriors(), variant="dirichlet")
    with seed(rng_seed=0):
        tr = trace(substitute(model, data={"fc/log_keep_0": np.log(1.7)})).get_trace()
    prior = tr["fc/log_keep_0"]["fn"]
    assert float(prior.loc) == -1.5 and float(prior.scale) == 0.3
    assert float(tr["fc/keep_fraction_0"]["value"]) == 1.0  # capped inside the support
