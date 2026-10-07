"""Reactive allocation of a departed candidate's support (backend issue 51, phase 1 build).

Applied only to the forecast-target campaigns (the held-out campaign and 2026); training
campaigns are untouched. For each Suspended Campaign announced on or before the target's
cutoff, in date order:

* the latent date grid gains a node at the exit day;
* at every latent date on or after the exit, the departed candidate keeps ``keep`` of their
  latent share (log-normal prior, S2's: the usable cases of the suspension table, leaving
  out the held-out campaign's own cycle);
* the freed share ``(1 - keep) * s_d`` goes to the remaining named candidates by an
  allocation vector ``a ~ Dirichlet(ALLOCATION_CONCENTRATION * centre)``, ``centre`` being
  the remaining candidates' proportional split of the latent support at the exit node;
* C3 only: a one-time shift of the remaining candidates' composition, a log-ratio shift
  ``delta = H @ (sigma * z)`` (``H`` the remaining candidates' Helmert basis,
  ``z ~ N(0, I)``, ``sigma ~ HalfNormal(SHIFT_SCALE)``), applied on and after the exit with
  the remaining candidates' total unchanged;
* post-exit readings are compositions over the remaining candidates (any share they report
  for a departed candidate is set aside) against this post-exit latent; pre-exit readings
  are modelled as before; election day reads the post-exit latent.

With no post-exit reading the allocation and shift keep their priors. Pollster house
effects already exist in every campaign (``firm_z`` x ``tau_firm``), so "C1 = C2 plus house
effects" adds nothing to C2 as specified (issue 51 phase 1 report).
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from datetime import date

import jax.numpy as jnp
import numpy as np

from .readings import CampaignPolls, _campaign_polls, _normalize

ALLOCATION_CONCENTRATION = 4.0
# One standard deviation of the two-way share shift at p = 0.5 is 8 points:
# d(share) = p (1 - p) d(logit) = 0.25 * sqrt(2) * sigma * z, so E[sigma^2]^(1/2) = s gives
# sd = 0.25 * sqrt(2) * s = 0.08  ->  s = 0.08 / (0.25 * sqrt(2)) = 0.2263.
SHIFT_SCALE = 0.08 / (0.25 * np.sqrt(2.0))
VERSIONS = ("c2", "c3")


@dataclass(frozen=True)
class ExitSpec:
    candidate: int  # index into the campaign's named candidates
    name: str
    day: int  # days before election day of the public exit
    keep_mu: float  # log-normal keep-fraction prior
    keep_sigma: float


def target_exits(
    campaign: CampaignPolls,
    rows: list[dict],
    cutoff: date,
    keep_prior: tuple[float, float],
) -> tuple[ExitSpec, ...]:
    """Exits of named candidates announced on or before ``cutoff``, earliest first."""
    index = {_normalize(n): i for i, n in enumerate(campaign.names)}
    out = []
    for row in rows:
        if row["election_cycle_id"] != campaign.key or row["announcement_date"] > cutoff:
            continue
        i = index.get(_normalize(row["candidate_name"]))
        if i is None:
            continue
        day = (campaign.election_date - row["announcement_date"]).days
        out.append(ExitSpec(i, campaign.names[i], day, float(keep_prior[0]), float(keep_prior[1])))
    return tuple(sorted(out, key=lambda e: (-e.day, e.candidate)))


def set_aside_after_exits(campaign: CampaignPolls, exits: tuple[ExitSpec, ...]) -> CampaignPolls:
    """Drop a departed candidate from readings on or after their exit (renormalizing the
    rest; ``n_eff`` scales with the retained share). Readings left with fewer than two
    offered candidates are dropped."""
    if not exits:
        return campaign
    polls = []
    for poll in campaign.polls:
        gone = {e.candidate for e in exits if poll.days_before_election <= e.day}
        pairs = [(i, s) for i, s in zip(poll.offered, poll.shares) if i not in gone]
        if len(pairs) < 2:
            continue
        if len(pairs) == len(poll.offered):
            polls.append(poll)
            continue
        total = sum(s for _, s in pairs)
        polls.append(
            dataclasses.replace(
                poll,
                offered=tuple(i for i, _ in pairs),
                shares=tuple(s / total for _, s in pairs),
                n_eff=poll.n_eff * total,
            )
        )
    return _campaign_polls(
        campaign.key,
        campaign.candidates,
        campaign.names,
        campaign.election_date,
        polls,
        campaign.outcome_shares,
        campaign.outcome_tail,
    )


def exit_transform(s, post, departed: int, remaining, keep, allocation, shift=None):
    """Post-exit latent support for one exit.

    ``s`` (T, K) latent support; ``post`` (T,) bool for dates on or after the exit;
    ``remaining`` index array; ``allocation`` sums to 1 over ``remaining``; ``shift`` an
    optional sum-zero log-ratio vector over ``remaining`` (C3). Pre-exit rows are unchanged.
    """
    s = jnp.asarray(s)
    remaining = jnp.asarray(remaining)
    freed = (1.0 - keep) * s[:, departed]
    new = s.at[:, remaining].add(freed[:, None] * jnp.asarray(allocation)[None, :])
    new = new.at[:, departed].set(keep * s[:, departed])
    if shift is not None:
        r = new[:, remaining]
        total = r.sum(axis=1, keepdims=True)
        shifted = r * jnp.exp(jnp.asarray(shift))[None, :]
        shifted = shifted / shifted.sum(axis=1, keepdims=True) * total
        new = new.at[:, remaining].set(shifted)
    return jnp.where(jnp.asarray(post)[:, None], new, s)
