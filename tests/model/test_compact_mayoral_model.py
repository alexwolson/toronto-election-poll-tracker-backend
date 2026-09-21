"""Compact mayoral model: sites, shapes, innovation families, sampling and the gate."""

from datetime import date

import jax
import numpy as np
import pytest
from numpyro.handlers import seed, trace

from backend.model.compact_mayoral.hyperpriors import population_hyperpriors
from backend.model.compact_mayoral.model import build_model
from backend.model.compact_mayoral.qualification import (
    Diagnostics,
    QualificationError,
    qualify,
)
from backend.model.compact_mayoral.readings import CampaignPolls, Poll
from backend.model.compact_mayoral.sampling import FitSettings, fit_joint

jax.config.update("jax_enable_x64", True)
FAST = FitSettings(warmup=150, draws=150, chains=1, seed=1, target_accept=0.9)


def synthetic(key="s", outcome=None, tail=None, n_polls=6, rng=None, truth=(0.5, 0.4, 0.1)):
    polls = []
    for i in range(n_polls):
        shares = truth if rng is None else tuple(rng.multinomial(1200, truth) / 1200)
        polls.append(
            Poll(
                f"{key}-{i}", f"{key}-{i}", ("A", "B")[i % 2], 60 - 9 * i, 900.0, (0, 1, 2), shares
            )
        )
    return CampaignPolls(
        key,
        ("c0", "c1", "c2"),
        ("Zero", "One", "Two"),
        date(2030, 1, 1),
        tuple(polls),
        outcome,
        tail,
        (0, 1),
    )


def sites(model):
    with seed(rng_seed=0):
        tr = trace(model).get_trace()
    return {k: v for k, v in tr.items() if v["type"] in {"sample", "deterministic"}}


def test_model_sites_shapes_and_observation_status() -> None:
    pred, obs = (
        synthetic("pred"),
        synthetic("obs", outcome=(0.48, 0.42, 0.10), tail=0.03, n_polls=4),
    )
    s = sites(build_model((pred, obs), population_hyperpriors()))
    for name in (
        "m_move",
        "omega_move",
        "tau_firm",
        "tau_election",
        "kappa",
        "tau_reference",
        "mu_tail",
        "sigma_tail",
    ):
        assert s[name]["value"].shape == ()
    assert s["pred/contrasts"]["value"].shape == (7, 2)
    assert s["obs/contrasts"]["value"].shape == (5, 2)
    assert s["pred/firm"]["value"].shape == (2, 2)
    assert s["pred/named_result"]["value"].shape == (3,) and np.isclose(
        s["pred/named_result"]["value"].sum(), 1
    )
    assert s["pred/full_ballot"]["value"].shape == (3,) and s["pred/current"]["value"].shape == (3,)
    assert s["obs/election"]["is_observed"] and s["obs/logit_tail"]["is_observed"]
    assert (
        s["pred/election_z"]["type"] == "sample" and s["pred/election"]["type"] == "deterministic"
    )
    assert not s["pred/logit_tail"]["is_observed"]
    assert s["pred/poll"]["is_observed"] and s["pred/poll"]["value"].shape == (6, 3)
    assert "step_mixing" not in "".join(s)


def test_variants_and_innovations_expose_their_extra_sites() -> None:
    leaders = sites(build_model((synthetic(),), population_hyperpriors(), variant="leaders"))
    assert "tau_lead" in leaders and "tau_rest" in leaders and "tau_election" not in leaders
    heavy = sites(build_model((synthetic(),), population_hyperpriors(), innovations="student_t"))
    assert heavy["s/step_mixing"]["value"].shape == (6,) and heavy["s/firm_mixing"][
        "value"
    ].shape == (2,)
    with pytest.raises(ValueError):
        build_model((synthetic(),), population_hyperpriors(), variant="other")
    with pytest.raises(ValueError):
        build_model((synthetic(),), population_hyperpriors(), innovations="cauchy")


def test_population_hyperpriors_are_the_heavy_model_priors() -> None:
    s = population_hyperpriors()["sites"]
    assert s["m_move"] == {"dist": "HalfNormal", "scale": 0.10}
    assert s["tau_election"] == {"dist": "HalfNormal", "scale": 0.30}
    assert s["kappa"]["dist"] == "LogNormal" and s["kappa"]["mu"] == pytest.approx(np.log(1.5))
    assert s["mu_tail"]["loc"] == pytest.approx(np.log(0.08 / 0.92))


def test_fit_joint_recovers_a_stable_race_and_reports_diagnostics() -> None:
    campaign = synthetic("s", n_polls=10, rng=np.random.default_rng(7))
    result = fit_joint((campaign,), population_hyperpriors(), settings=FAST)
    current = result.draws["s/current"]
    assert current.shape == (150, 3)
    assert np.abs(current.mean(0) - np.array([0.5, 0.4, 0.1])).max() < 0.03
    assert result.draws["s/named_result"][:, 0].std() > current[:, 0].std()
    d = result.diagnostics
    assert d.draws == 150 and d.chains == 1 and d.divergences >= 0 and np.isfinite(d.worst_r_hat)
    assert d.min_ess > 0 and d.constant_coordinates_ignored >= 0
    assert result.elapsed_seconds > 0 and result.settings == FAST


def test_qualification_gate_fails_closed() -> None:
    clean = Diagnostics(
        draws=4000,
        chains=4,
        divergences=0,
        worst_r_hat=1.004,
        min_ess=900.0,
        coordinates_over_r_hat=0,
        mean_leapfrog_steps=200.0,
        constant_coordinates_ignored=3,
    )
    qualify(clean)
    for bad in (
        clean.__class__(**{**clean.__dict__, "divergences": 1}),
        clean.__class__(**{**clean.__dict__, "worst_r_hat": 1.02, "coordinates_over_r_hat": 2}),
        clean.__class__(**{**clean.__dict__, "min_ess": 120.0}),
        clean.__class__(**{**clean.__dict__, "worst_r_hat": float("nan")}),
    ):
        with pytest.raises(QualificationError):
            qualify(bad)
