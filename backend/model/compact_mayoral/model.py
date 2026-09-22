"""Compact multi-campaign mayoral model.

Per campaign: named-candidate support as log-odds contrasts (orthonormal Helmert
basis) following a random walk (Gaussian, or the research model's
variance-normalized t(5) scale mixtures with ``innovations="student_t"``, which
then also applies to firm effects) evaluated at the distinct poll dates and
election day; one firm effect per firm; each poll a Dirichlet composition over
the reference candidates it offered, with the precision law
phi = 1 / (kappa / n_eff + tau_reference^2 / 4); an election-day discrepancy (a
Dirichlet reading of the latent support under the published ``dirichlet`` variant;
a Student-t(5) shock on the named contrasts, drawn non-centered for predicted
campaigns, under ``isotropic`` and ``leaders``); and a Student-t logit for the
ballot share outside the named reference. Shared scales are drawn from
``hyperpriors``.

``variant``:
* ``dirichlet``: the named result is one more composition reading of the latent
  support, ``Dirichlet(phi_election * election_mixing * p)``, so the discrepancy is
  mean-preserving with variance proportional to ``p (1 - p)`` (the published
  specification, ADR 0055; pre-registered and held-out tested 2026-09-22).
* ``isotropic``: one log-odds discrepancy scale ``tau_election`` for every
  candidate (the ADR 0054 specification, kept as a sensitivity refit).
* ``leaders``: ``tau_lead`` for the two candidates leading the latest polls and
  ``tau_rest`` for everyone else (a stress test; its scale is fragile).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

import jax
import jax.numpy as jnp
import numpy as np
import numpyro
import numpyro.distributions as dist
from numpyro.distributions import constraints

from .hyperpriors import prior_distribution
from .readings import CampaignPolls

T_DF = 5.0
# Student-t(5) scaled so that its variance equals the nominal scale squared.
T_UNIT = float(np.sqrt((T_DF - 2) / T_DF))


def helmert_basis(count: int) -> np.ndarray:
    """(count, count-1) matrix with orthonormal columns, each orthogonal to the ones vector."""
    basis = np.zeros((count, count - 1))
    for j in range(1, count):
        basis[:j, j - 1] = 1.0 / np.sqrt(j * (j + 1))
        basis[j, j - 1] = -j / np.sqrt(j * (j + 1))
    return basis


class ConditionalDirichlet(dist.Distribution):
    """Dirichlet over the offered categories only; unoffered entries are ignored."""

    arg_constraints: ClassVar[dict] = {}
    support = constraints.real_vector
    has_rsample = False

    def __init__(self, concentration, mask, *, validate_args=None):
        self.concentration = jnp.asarray(concentration)
        self.mask = jnp.asarray(mask, dtype=bool)
        super().__init__(
            batch_shape=self.concentration.shape[:-1],
            event_shape=self.concentration.shape[-1:],
            validate_args=validate_args,
        )

    def sample(self, key, sample_shape=()):
        raise NotImplementedError("observation-only distribution")

    def log_prob(self, value):
        alpha = jnp.where(self.mask, self.concentration, 1.0)
        safe = jnp.where(self.mask, value, 1.0)
        total = jnp.sum(jnp.where(self.mask, alpha, 0.0), axis=-1)
        terms = jnp.where(
            self.mask, (alpha - 1.0) * jnp.log(safe) - jax.scipy.special.gammaln(alpha), 0.0
        )
        return jax.scipy.special.gammaln(total) + jnp.sum(terms, axis=-1)


@dataclass(frozen=True)
class Prepared:
    key: str
    count: int
    basis: np.ndarray  # (K, K-1)
    gaps: np.ndarray  # (T-1,) days between consecutive latent dates
    poll_time: np.ndarray  # (n,) index into the latent dates
    poll_firm: np.ndarray  # (n,)
    firm_count: int
    mask: np.ndarray  # (n, K) offered
    composition: np.ndarray  # (n, K) floored, renormalized over offered; zero elsewhere
    n_eff: np.ndarray  # (n,)
    current_time: int  # latent index of the most recent poll date
    is_leader: np.ndarray  # (K,)
    outcome_contrasts: np.ndarray | None  # (K-1,) Helmert contrasts of log outcome shares
    outcome_shares: np.ndarray | None  # (K,) named result, floored and renormalized
    outcome_logit_tail: float | None


def prepare(campaign: CampaignPolls) -> Prepared:
    count = len(campaign.candidates)
    if count < 2:
        raise ValueError(f"{campaign.key}: need at least two reference candidates")
    dates = sorted({p.days_before_election for p in campaign.polls} | {0}, reverse=True)
    position = {day: i for i, day in enumerate(dates)}
    firms = sorted({p.firm for p in campaign.polls})
    firm_index = {firm: i for i, firm in enumerate(firms)}
    n = len(campaign.polls)
    mask = np.zeros((n, count), dtype=bool)
    composition = np.zeros((n, count))
    n_eff = np.zeros(n)
    poll_time = np.zeros(n, dtype=int)
    poll_firm = np.zeros(n, dtype=int)
    for i, poll in enumerate(campaign.polls):
        offered = np.asarray(poll.offered)
        floor = 0.5 / poll.n_eff
        shares = np.maximum(np.asarray(poll.shares), floor)
        mask[i, offered] = True
        composition[i, offered] = shares / shares.sum()
        n_eff[i] = poll.n_eff
        poll_time[i] = position[poll.days_before_election]
        poll_firm[i] = firm_index[poll.firm]
    basis = helmert_basis(count)
    is_leader = np.zeros(count, dtype=bool)
    is_leader[list(campaign.leaders)] = True
    outcome = None
    outcome_shares = None
    if campaign.outcome_shares is not None:
        outcome = np.log(np.asarray(campaign.outcome_shares)) @ basis
        floored = np.maximum(np.asarray(campaign.outcome_shares, dtype=float), 1e-4)
        outcome_shares = floored / floored.sum()
    tail = None
    if campaign.outcome_tail is not None:
        tail = float(np.log(campaign.outcome_tail / (1.0 - campaign.outcome_tail)))
    return Prepared(
        key=campaign.key,
        count=count,
        basis=basis,
        gaps=-np.diff(np.asarray(dates, dtype=float)),
        poll_time=poll_time,
        poll_firm=poll_firm,
        firm_count=len(firms),
        mask=mask,
        composition=composition,
        n_eff=n_eff,
        current_time=position[min(p.days_before_election for p in campaign.polls)],
        is_leader=is_leader,
        outcome_contrasts=outcome,
        outcome_shares=outcome_shares,
        outcome_logit_tail=tail,
    )


def build_model(
    campaigns: tuple[CampaignPolls, ...],
    hyperpriors: dict,
    *,
    variant: str = "isotropic",
    starting_pair_sd: float = 2.0,
    innovations: str = "gaussian",
):
    if variant not in {"isotropic", "leaders", "dirichlet"}:
        raise ValueError("variant must be 'isotropic', 'leaders' or 'dirichlet'")
    if innovations not in {"gaussian", "student_t"}:
        raise ValueError("innovations must be 'gaussian' or 'student_t'")
    heavy_tailed = innovations == "student_t"
    if len({c.key for c in campaigns}) != len(campaigns):
        raise ValueError("campaign keys must be unique")
    prepared = tuple(prepare(c) for c in campaigns)
    specs = hyperpriors["sites"]

    def shared(name, spec_name=None):
        return numpyro.sample(name, prior_distribution(specs[spec_name or name]))

    def model():
        m_move = shared("m_move")
        omega = shared("omega_move")
        tau_firm = shared("tau_firm")
        kappa = shared("kappa")
        tau_reference = shared("tau_reference")
        mu_tail = shared("mu_tail")
        sigma_tail = shared("sigma_tail")
        phi_election = None
        if variant == "dirichlet":
            phi_election = shared("phi_election")
            tau_lead = tau_rest = None
        elif variant == "isotropic":
            tau_lead = tau_rest = shared("tau_election")
        else:
            tau_lead = shared("tau_lead", "tau_election")
            tau_rest = shared("tau_rest", "tau_election")

        for P in prepared:
            prefix = P.key + "/"
            dims = P.count - 1
            basis = jnp.asarray(P.basis)

            move_z = numpyro.sample(prefix + "movement_z", dist.Normal(0.0, 1.0))
            weekly = numpyro.deterministic(
                prefix + "weekly_movement", m_move * jnp.exp(omega * move_z)
            )
            start = numpyro.sample(
                prefix + "start",
                dist.Normal(0.0, starting_pair_sd / jnp.sqrt(2.0)).expand((dims,)).to_event(1),
            )
            steps = numpyro.sample(
                prefix + "steps", dist.Normal(0.0, 1.0).expand((len(P.gaps), dims)).to_event(2)
            )
            step_scale = weekly * jnp.sqrt(jnp.asarray(P.gaps) / 7.0)
            if heavy_tailed:
                step_chi2 = numpyro.sample(
                    prefix + "step_chi2", dist.Chi2(T_DF).expand((len(P.gaps),)).to_event(1)
                )
                step_mixing = numpyro.deterministic(
                    prefix + "step_mixing", (T_DF - 2.0) / step_chi2
                )
                step_scale = step_scale * jnp.sqrt(step_mixing)
            increments = steps * step_scale[:, None]
            contrasts = numpyro.deterministic(
                prefix + "contrasts",
                jnp.concatenate([start[None, :], start[None, :] + jnp.cumsum(increments, axis=0)]),
            )
            firm_z = numpyro.sample(
                prefix + "firm_z", dist.Normal(0.0, 1.0).expand((P.firm_count, dims)).to_event(2)
            )
            firm_scale = tau_firm / jnp.sqrt(2.0)
            if heavy_tailed:
                firm_chi2 = numpyro.sample(
                    prefix + "firm_chi2", dist.Chi2(T_DF).expand((P.firm_count,)).to_event(1)
                )
                firm_mixing = numpyro.deterministic(
                    prefix + "firm_mixing", (T_DF - 2.0) / firm_chi2
                )
                firm_scale = firm_scale * jnp.sqrt(firm_mixing)[:, None]
            firm = numpyro.deterministic(prefix + "firm", firm_z * firm_scale)

            logits = (contrasts[P.poll_time] + firm[P.poll_firm]) @ basis.T
            mask = jnp.asarray(P.mask)
            probabilities = jax.nn.softmax(jnp.where(mask, logits, -jnp.inf), axis=1)
            phi = 1.0 / (kappa / jnp.asarray(P.n_eff) + tau_reference**2 / 4.0)
            numpyro.sample(
                prefix + "poll",
                ConditionalDirichlet(phi[:, None] * probabilities, mask),
                obs=jnp.asarray(P.composition),
            )

            numpyro.deterministic(
                prefix + "current", jax.nn.softmax(contrasts[P.current_time] @ basis.T)
            )

            # Election-day discrepancy: per-candidate log-share shocks with a shared
            # t(5) mixing variable, projected onto the contrasts. Isotropic scales give
            # a per-contrast variance of tau^2 / 2.
            # Latent named support at election day, before the discrepancy is applied.
            support = numpyro.deterministic(
                prefix + "election_support", jax.nn.softmax(contrasts[-1] @ basis.T)
            )
            mixing = numpyro.sample(prefix + "election_mixing", dist.Gamma(T_DF / 2.0, T_DF / 2.0))
            if phi_election is not None:
                # Dirichlet election day (ADR 0055): the result is one more composition
                # reading of the latent support with precision phi * mixing, so the shock
                # is mean-preserving and its variance scales with p (1 - p). Observed
                # campaigns condition on their named result.
                precision = numpyro.deterministic(
                    prefix + "election_precision", phi_election * mixing
                )
                concentration = precision * jnp.clip(support, 1e-6, None)
                named = numpyro.sample(
                    prefix + "election_result",
                    dist.Dirichlet(concentration),
                    obs=None if P.outcome_shares is None else jnp.asarray(P.outcome_shares),
                )
                named = numpyro.deterministic(prefix + "named_result", named)
            else:
                sigma = jnp.where(jnp.asarray(P.is_leader), tau_lead, tau_rest) / jnp.sqrt(2.0)
                covariance = (basis.T * (sigma**2)[None, :]) @ basis * (T_UNIT**2 / mixing)
                covariance = covariance + 1e-12 * jnp.eye(dims)
                if P.outcome_contrasts is None:
                    # Non-centered prediction: a standard-normal shock scaled by the
                    # covariance's Cholesky factor, so a small discrepancy scale cannot
                    # open a funnel between scale and shock.
                    election_z = numpyro.sample(
                        prefix + "election_z", dist.Normal(0.0, 1.0).expand((dims,)).to_event(1)
                    )
                    election = numpyro.deterministic(
                        prefix + "election",
                        contrasts[-1] + jnp.linalg.cholesky(covariance) @ election_z,
                    )
                else:
                    election = numpyro.sample(
                        prefix + "election",
                        dist.MultivariateNormal(contrasts[-1], covariance_matrix=covariance),
                        obs=jnp.asarray(P.outcome_contrasts),
                    )
                named = numpyro.deterministic(
                    prefix + "named_result", jax.nn.softmax(election @ basis.T)
                )
            logit_tail = numpyro.sample(
                prefix + "logit_tail",
                dist.StudentT(T_DF, mu_tail, sigma_tail * T_UNIT),
                obs=None if P.outcome_logit_tail is None else jnp.asarray(P.outcome_logit_tail),
            )
            tail = jax.nn.sigmoid(logit_tail)
            numpyro.deterministic(prefix + "tail", tail)
            numpyro.deterministic(prefix + "full_ballot", named * (1.0 - tail))

    return model
