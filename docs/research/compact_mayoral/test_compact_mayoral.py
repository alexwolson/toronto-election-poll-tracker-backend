"""Compact mayoral model: adapter, model shapes, hyperprior provenance, recovery.

Run from the backend root with the research dependencies supplied explicitly:

    uv run --no-project --with numpyro --with jax --with pytest \
        python -m pytest docs/research/compact_mayoral -q \
        --import-mode=importlib -o consider_namespace_packages=true
"""

from datetime import date

import jax
import numpy as np
import pytest
from numpyro.handlers import seed, substitute, trace
from numpyro.infer import MCMC, NUTS

from .hyperpriors import (
    borrowed_hyperpriors,
    population_hyperpriors,
    prior_distribution,
    summarize_globals,
)
from .model import build_model, support_scale
from .readings import (
    EXTRA_2026,
    CampaignPolls,
    Poll,
    current_campaign,
    historical_campaigns,
    with_horizon,
)

jax.config.update("jax_enable_x64", True)

ELECTION_2026 = date(2026, 10, 26)


# --------------------------------------------------------------------------- adapter


def _by_name(campaign, name):
    return campaign.names.index(name)


def test_historical_2014_reference_is_polled_final_ballot_candidates():
    camps = historical_campaigns()
    c = camps["toronto_2014"]
    # Heavy-model rule: individually polled in an ordinary reading AND on the final ballot.
    # Rob Ford, Stintz, Soknacki withdrew; Goldkind only appears in a hypothetical.
    assert set(c.names) == {"John Tory", "Doug Ford", "Olivia Chow"}
    assert c.election_date == date(2014, 10, 27)
    shares = dict(zip(c.names, c.outcome_shares))
    # Official shares .403/.337/.231 renormalized among the three.
    assert shares["John Tory"] == pytest.approx(0.403 / 0.971, abs=0.003)
    assert shares["Olivia Chow"] == pytest.approx(0.231 / 0.971, abs=0.003)
    assert sum(c.outcome_shares) == pytest.approx(1.0, abs=1e-9)
    assert c.outcome_tail == pytest.approx(1 - 0.971, abs=0.003)
    # Leaders are the top two by the latest polls, not by the outcome.
    assert {c.names[i] for i in c.leaders} == {"John Tory", "Doug Ford"}


def test_historical_polls_are_one_per_sample_and_conditional_compositions():
    camps = historical_campaigns()
    assert set(camps) == {
        "toronto_2003",
        "toronto_2006",
        "toronto_2010",
        "toronto_2014",
        "toronto_2018",
        "toronto_2022",
        "toronto_2023",
    }
    # 97 same-sample dependence groups carry ordinary citywide readings in the register.
    assert sum(len(c.polls) for c in camps.values()) == 98
    for c in camps.values():
        groups = [p.group for p in c.polls]
        assert len(groups) == len(set(groups)), "one canonical reading per sample"
        for p in c.polls:
            assert len(p.offered) >= 2
            assert set(p.offered) <= set(range(len(c.candidates)))
            assert len(p.shares) == len(p.offered)
            assert sum(p.shares) == pytest.approx(1.0, abs=1e-9)
            assert p.n_eff > 0
            assert 0 <= p.days_before_election <= 800
    # Ipsos, fieldwork 2014-09-12..16, decided voters: Tory 43 / Chow 29 / Doug Ford 28.
    c = camps["toronto_2014"]
    ipsos = [p for p in c.polls if p.group == "ipsos_city_2014_09_12_16_n596"]
    assert len(ipsos) == 1
    p = ipsos[0]
    got = {c.names[i]: s for i, s in zip(p.offered, p.shares)}
    assert got["John Tory"] == pytest.approx(0.43, abs=0.01)
    assert got["Olivia Chow"] == pytest.approx(0.29, abs=0.01)
    assert got["Doug Ford"] == pytest.approx(0.28, abs=0.01)
    assert p.days_before_election == (date(2014, 10, 27) - date(2014, 9, 14)).days
    assert p.firm == "Ipsos Reid"
    assert 500 < p.n_eff <= 596


def test_current_2026_uses_only_full_field_polls_from_the_release():
    c = current_campaign(election_date=ELECTION_2026)
    assert c.key == "toronto-2026"
    assert c.names == ("Olivia Chow", "Brad Bradford", "Chris Alexander")
    assert c.outcome_shares is None and c.outcome_tail is None
    # Chronological order (earliest first); the release file lists newest first.
    assert [p.reading_id for p in c.polls] == [
        "forum-2026-07-29",
        "liaison-2026-08-05",
        "liaison-2026-08-16",
        "pallas-2026-08-21",
        "liaison-2026-09-05",
        "mainstreet-2026-09-14",
    ]
    ms = c.polls[-1]
    assert ms.offered == (0, 1, 2)
    named = 0.458 + 0.377 + 0.096
    assert ms.shares == pytest.approx((0.458 / named, 0.377 / named, 0.096 / named), abs=1e-6)
    assert ms.n_eff == pytest.approx(1000 * named, abs=1e-6)
    assert ms.days_before_election == (ELECTION_2026 - date(2026, 9, 17)).days
    assert ms.firm == "Mainstreet Research"
    assert {c.names[i] for i in c.leaders} == {"Olivia Chow", "Brad Bradford"}


def test_current_2026_can_name_minor_candidates_reported_by_some_polls():
    c = current_campaign(election_date=ELECTION_2026, extra_named=EXTRA_2026)
    assert c.names == (
        "Olivia Chow",
        "Brad Bradford",
        "Chris Alexander",
        "Sarah McVie",
        "Odessa Paloma Parker",
    )
    assert len(c.polls) == 6  # the certified-field rule still applies to the base three
    by_id = {p.reading_id: p for p in c.polls}
    ms = by_id["mainstreet-2026-09-14"]
    assert ms.offered == (0, 1, 2, 3, 4)
    named = 0.458 + 0.377 + 0.096 + 0.025 + 0.019
    assert ms.shares[3] == pytest.approx(0.025 / named, abs=1e-6)
    assert ms.shares[4] == pytest.approx(0.019 / named, abs=1e-6)
    assert ms.n_eff == pytest.approx(1000 * named, abs=1e-6)
    liaison = by_id["liaison-2026-09-05"]
    assert liaison.offered == (0, 1, 2)  # conditional composition over the names it reported
    assert liaison.n_eff == pytest.approx(1000 * (0.50 + 0.39 + 0.10), abs=1e-6)
    assert {c.names[i] for i in c.leaders} == {"Olivia Chow", "Brad Bradford"}


def test_with_horizon_drops_late_polls_and_recomputes_leaders():
    c = _synthetic("h", outcome=(0.30, 0.60, 0.10), tail=0.02, n_polls=6)  # polls at 60..10 days
    # Make the latest poll favour candidate 1 so leaders depend on which polls remain.
    late = Poll("h-late", "h-late", "A", 5, 900.0, (0, 1, 2), (0.2, 0.7, 0.1))
    c = CampaignPolls(**{**c.__dict__, "polls": (*c.polls, late)})
    assert with_horizon(c, 0).leaders == (1, 0)
    h = with_horizon(c, 39)
    assert [p.days_before_election for p in h.polls] == [60, 50, 40]
    assert h.leaders == (0, 1)  # from the remaining polls only
    assert h.outcome_shares == c.outcome_shares  # nulling the result is the fit's job
    with pytest.raises(ValueError):
        with_horizon(c, 61)


# --------------------------------------------------------------------------- model


def _synthetic(key="synthetic", outcome=None, tail=None, n_polls=6):
    polls = tuple(
        Poll(
            reading_id=f"{key}-{i}",
            group=f"{key}-{i}",
            firm=("A", "B")[i % 2],
            days_before_election=60 - 10 * i,
            n_eff=900.0,
            offered=(0, 1, 2),
            shares=(0.5, 0.4, 0.1),
        )
        for i in range(n_polls)
    )
    return CampaignPolls(
        key=key,
        candidates=("c0", "c1", "c2"),
        names=("Zero", "One", "Two"),
        election_date=date(2030, 1, 1),
        polls=polls,
        outcome_shares=outcome,
        outcome_tail=tail,
        leaders=(0, 1),
    )


def _sites(model):
    with seed(rng_seed=0):
        tr = trace(model).get_trace()
    return {k: v for k, v in tr.items() if v["type"] in {"sample", "deterministic"}}


def test_model_sites_and_shapes_for_prediction_and_observed_campaigns():
    pred = _synthetic("pred")
    obs = _synthetic("obs", outcome=(0.48, 0.42, 0.10), tail=0.03, n_polls=4)
    sites = _sites(build_model((pred, obs), population_hyperpriors(), variant="isotropic"))
    # Global scales shared by every campaign.
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
        assert name in sites and sites[name]["value"].shape == ()
    assert "tau_lead" not in sites and "tau_rest" not in sites
    assert "gamma_election" not in sites
    # Latent contrasts sit on the campaign's distinct poll dates plus election day.
    assert sites["pred/contrasts"]["value"].shape == (6 + 1, 2)
    assert sites["obs/contrasts"]["value"].shape == (4 + 1, 2)
    assert sites["pred/firm"]["value"].shape == (2, 2)
    assert sites["pred/named_result"]["value"].shape == (3,)
    assert sites["pred/current"]["value"].shape == (3,)
    assert sites["pred/full_ballot"]["value"].shape == (3,)
    assert np.isclose(sites["pred/named_result"]["value"].sum(), 1.0)
    # Observed campaigns condition on their result; predicted ones draw it
    # non-centered (standard-normal shock scaled by the discrepancy covariance),
    # so a small discrepancy scale cannot create a funnel.
    assert sites["obs/election"]["is_observed"] is True
    assert sites["obs/logit_tail"]["is_observed"] is True
    assert "obs/election_z" not in sites
    assert sites["pred/election_z"]["type"] == "sample"
    assert sites["pred/election_z"]["value"].shape == (2,)
    assert sites["pred/election"]["type"] == "deterministic"
    assert sites["pred/logit_tail"]["is_observed"] is False
    # Every poll is an observed Dirichlet composition.
    assert sum(1 for k, v in sites.items() if k.endswith("/poll") and v["is_observed"]) == 2
    assert sites["pred/poll"]["value"].shape == (6, 3)


def test_student_t_innovations_add_one_mixing_value_per_step_and_per_firm():
    gaussian = _sites(build_model((_synthetic(),), population_hyperpriors()))
    assert "synthetic/step_mixing" not in gaussian and "synthetic/firm_mixing" not in gaussian
    heavy_tailed = _sites(
        build_model((_synthetic(),), population_hyperpriors(), innovations="student_t")
    )
    # Variance-normalized t(5): mix = 3 / Chi2(5) per random-walk step and per firm,
    # as the heavy model's daily_chi2 / firm_chi2 construction.
    assert heavy_tailed["synthetic/step_mixing"]["value"].shape == (6,)  # 7 dates -> 6 steps
    assert heavy_tailed["synthetic/firm_mixing"]["value"].shape == (2,)
    assert np.all(np.asarray(heavy_tailed["synthetic/step_mixing"]["value"]) > 0)
    with pytest.raises(ValueError):
        build_model((_synthetic(),), population_hyperpriors(), innovations="cauchy")


def test_leaders_variant_splits_the_election_discrepancy_scale():
    sites = _sites(build_model((_synthetic(),), population_hyperpriors(), variant="leaders"))
    assert "tau_lead" in sites and "tau_rest" in sites and "tau_election" not in sites
    assert "gamma_election" not in sites


def _sites_with(model, values):
    with seed(rng_seed=0):
        tr = trace(substitute(model, data=values)).get_trace()
    return {k: v for k, v in tr.items() if v["type"] in {"sample", "deterministic"}}


def test_support_scale_is_one_at_even_support_and_symmetric():
    p = np.array([0.5, 0.1, 0.9, 0.01])
    assert np.allclose(support_scale(p, 0.0), 1.0)
    full = np.asarray(support_scale(p, 1.0))
    assert np.isclose(full[0], 1.0)
    assert np.isclose(full[1], 0.25 / 0.09) and np.isclose(full[1], full[2])
    # gamma = 0.5 is the binomial-like case: the square root of the gamma = 1 factor.
    assert np.allclose(support_scale(p, 0.5), np.sqrt(full))
    # Support is clipped, so a vanishing candidate cannot blow the scale up without bound.
    edge = np.asarray(support_scale(np.array([0.0, 1.0]), 1.0))
    assert np.all(np.isfinite(edge)) and np.allclose(edge, 0.25 / (1e-3 * (1 - 1e-3)))


def test_support_scaled_variant_reduces_to_the_isotropic_model_at_gamma_zero():
    model = build_model((_synthetic(),), population_hyperpriors(), variant="support_scaled")
    sites = _sites_with(model, {"gamma_election": np.float64(0.0), "tau_election": np.float64(0.4)})
    assert sites["gamma_election"]["type"] == "sample"
    assert "tau_lead" not in sites and "tau_rest" not in sites
    # Per-candidate log-share shock scale: tau / sqrt(2) for everyone, as in `isotropic`.
    assert np.allclose(sites["synthetic/discrepancy_scale"]["value"], 0.4 / np.sqrt(2.0))
    isotropic = build_model((_synthetic(),), population_hyperpriors(), variant="isotropic")
    iso_sites = _sites_with(isotropic, {"tau_election": np.float64(0.4)})
    assert np.allclose(
        iso_sites["synthetic/discrepancy_scale"]["value"],
        sites["synthetic/discrepancy_scale"]["value"],
    )


def test_support_scaled_variant_scales_each_candidate_by_its_election_day_support():
    model = build_model((_synthetic(),), population_hyperpriors(), variant="support_scaled")
    sites = _sites_with(model, {"gamma_election": np.float64(1.0), "tau_election": np.float64(0.4)})
    support = np.asarray(sites["synthetic/election_support"]["value"])
    assert support.shape == (3,) and np.isclose(support.sum(), 1.0)
    expected = 0.4 / np.sqrt(2.0) * np.asarray(support_scale(support, 1.0))
    assert np.allclose(sites["synthetic/discrepancy_scale"]["value"], expected)
    # Smaller support, larger log-odds scale.
    order = np.argsort(support)
    scale = np.asarray(sites["synthetic/discrepancy_scale"]["value"])
    assert np.all(np.diff(scale[order]) <= 1e-12)


def test_evaluation_crps_and_ks_match_closed_forms():
    from .evaluate import crps, ks_to_uniform

    # A point mass at x scores |x - y|.
    assert crps(np.full(500, 0.3), 0.1) == pytest.approx(0.2)
    # Standard normal against y = 0: 2 phi(0) - 1 / sqrt(pi).
    rng = np.random.default_rng(3)
    sample = rng.standard_normal(200_000)
    expected = 2 / np.sqrt(2 * np.pi) - 1 / np.sqrt(np.pi)
    assert crps(sample, 0.0) == pytest.approx(expected, abs=0.003)
    # Perfectly spread PITs are ~1/n from uniform; a degenerate set is maximally far.
    assert ks_to_uniform((np.arange(10) + 0.5) / 10) == pytest.approx(0.05)
    assert ks_to_uniform(np.zeros(4)) == pytest.approx(1.0)


def test_population_hyperpriors_carry_the_support_scaling_exponent_prior():
    s = population_hyperpriors()["sites"]
    assert s["gamma_election"] == {"dist": "Beta", "concentration1": 2.0, "concentration0": 2.0}
    d = prior_distribution(s["gamma_election"])
    assert float(d.mean) == pytest.approx(0.5)


def test_population_hyperpriors_are_the_heavy_model_priors():
    hp = population_hyperpriors()
    assert hp["mode"] == "population"
    s = hp["sites"]
    assert s["m_move"] == {"dist": "HalfNormal", "scale": 0.10}
    assert s["omega_move"] == {"dist": "HalfNormal", "scale": 0.35}
    assert s["tau_firm"] == {"dist": "HalfNormal", "scale": 0.15}
    assert s["tau_election"] == {"dist": "HalfNormal", "scale": 0.30}
    assert s["tau_reference"] == {"dist": "HalfNormal", "scale": 0.05}
    assert s["sigma_tail"] == {"dist": "HalfNormal", "scale": 1.0}
    assert s["kappa"] == {"dist": "LogNormal", "mu": pytest.approx(np.log(1.5)), "sigma": 0.5}
    assert s["mu_tail"] == {
        "dist": "Normal",
        "loc": pytest.approx(np.log(0.08 / 0.92)),
        "scale": 1.0,
    }


# --------------------------------------------------------------------------- hyperpriors


def test_borrowed_hyperpriors_reproduce_the_saved_draws(tmp_path):
    rng = np.random.default_rng(1)
    run = tmp_path / "run"
    truth = {}
    for chain in range(2):
        d = run / f"chain-{chain}"
        d.mkdir(parents=True)
        for chunk in range(2):
            draws = {
                "m_move": rng.lognormal(np.log(0.1), 0.3, 250),
                "tau_election": rng.lognormal(np.log(0.8), 0.2, 250),
                "mu_tail": rng.normal(-2.9, 0.3, 250),
                "toronto-2026/daily_z": rng.normal(size=(250, 5)),  # must be ignored
            }
            for k, v in draws.items():
                truth.setdefault(k, []).append(v)
            np.savez_compressed(d / f"draws-{chunk:05d}.npz", **draws)
    summary = summarize_globals(run)
    assert set(summary) == {"m_move", "tau_election", "mu_tail"}
    for name, parts in truth.items():
        if name in summary:
            x = np.concatenate(parts)
            assert summary[name]["n"] == 1000
            assert summary[name]["mean"] == pytest.approx(x.mean())
            assert summary[name]["sd"] == pytest.approx(x.std())
    hp = borrowed_hyperpriors(summary)
    assert hp["mode"] == "borrowed"
    # Positive scales become LogNormal matched on log-moments; a location becomes Normal.
    s = hp["sites"]["m_move"]
    x = np.concatenate(truth["m_move"])
    assert s["dist"] == "LogNormal"
    assert s["mu"] == pytest.approx(np.log(x).mean())
    assert s["sigma"] == pytest.approx(np.log(x).std())
    assert np.exp(s["mu"] + s["sigma"] ** 2 / 2) == pytest.approx(x.mean(), rel=0.02)
    assert hp["sites"]["mu_tail"] == {
        "dist": "Normal",
        "loc": pytest.approx(np.concatenate(truth["mu_tail"]).mean()),
        "scale": pytest.approx(np.concatenate(truth["mu_tail"]).std()),
    }


# --------------------------------------------------------------------------- recovery


@pytest.mark.parametrize("innovations", ["gaussian", "student_t"])
def test_synthetic_recovery_of_a_stable_race(innovations):
    """Ten precise polls of a race sitting at 50/40/10 should recover that composition."""
    rng = np.random.default_rng(7)
    truth = np.array([0.5, 0.4, 0.1])
    polls = []
    for i in range(10):
        n = 1200
        y = rng.multinomial(n, truth) / n
        polls.append(
            Poll(
                reading_id=f"s{i}",
                group=f"s{i}",
                firm=("A", "B", "C")[i % 3],
                days_before_election=70 - 6 * i,
                n_eff=float(n),
                offered=(0, 1, 2),
                shares=tuple(y),
            )
        )
    campaign = CampaignPolls(
        key="s",
        candidates=("c0", "c1", "c2"),
        names=("Zero", "One", "Two"),
        election_date=date(2030, 1, 1),
        polls=tuple(polls),
        outcome_shares=None,
        outcome_tail=None,
        leaders=(0, 1),
    )
    model = build_model(
        (campaign,), population_hyperpriors(), variant="isotropic", innovations=innovations
    )
    mcmc = MCMC(
        NUTS(model, target_accept_prob=0.9), num_warmup=300, num_samples=300, progress_bar=False
    )
    mcmc.run(jax.random.key(0))
    current = np.asarray(mcmc.get_samples()["s/current"])
    assert current.shape == (300, 3)
    assert np.abs(current.mean(0) - truth).max() < 0.03
    lo, hi = np.quantile(current, [0.1, 0.9], axis=0)
    assert np.all(lo <= truth) and np.all(truth <= hi)
    # Election-day uncertainty must exceed current-support uncertainty (movement + discrepancy).
    result = np.asarray(mcmc.get_samples()["s/named_result"])
    assert result[:, 0].std() > current[:, 0].std()


# --------------------------------------------------------------------------- dirichlet variant


def test_dirichlet_variant_draws_election_day_as_a_dirichlet_around_latent_support():
    pred = _synthetic("pred")
    obs = _synthetic("obs", outcome=(0.48, 0.42, 0.10), tail=0.03, n_polls=4)
    model = build_model((pred, obs), population_hyperpriors(), variant="dirichlet")
    values = {
        "phi_election": np.float64(40.0),
        "pred/election_mixing": np.float64(1.0),
        "obs/election_mixing": np.float64(2.0),
    }
    with seed(rng_seed=0):
        tr = trace(substitute(model, data=values)).get_trace()
    assert "phi_election" in tr
    for absent in ("tau_election", "tau_lead", "tau_rest", "gamma_election"):
        assert absent not in tr
    assert "pred/election_z" not in tr and "pred/discrepancy_scale" not in tr
    # Predicted campaign: a latent Dirichlet draw with concentration phi_c * support.
    site = tr["pred/election_result"]
    assert site["type"] == "sample" and not site["is_observed"]
    support = np.asarray(tr["pred/election_support"]["value"])
    assert np.allclose(np.asarray(site["fn"].concentration), 40.0 * support)
    assert np.allclose(tr["pred/named_result"]["value"], site["value"])
    assert np.isclose(np.asarray(site["value"]).sum(), 1.0)
    assert np.allclose(tr["pred/election_precision"]["value"], 40.0)
    # Observed campaign: the actual named shares are the observation; precision phi * mixing.
    seen = tr["obs/election_result"]
    assert seen["is_observed"] and np.allclose(seen["value"], (0.48, 0.42, 0.10))
    assert np.isclose(float(np.asarray(seen["fn"].concentration).sum()), 80.0)
    assert "obs/election" not in tr


def test_dirichlet_precision_prior_is_the_pre_registered_lognormal():
    s = population_hyperpriors()["sites"]
    assert s["phi_election"] == {
        "dist": "LogNormal",
        "mu": pytest.approx(np.log(40.0)),
        "sigma": 1.5,
    }

