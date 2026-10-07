"""C2: a Suspended Campaign in the forecast campaign, with a learned exit allocation.

Pre-registered at 9a1ddef (``docs/research/reactive-allocation-2026-10-07.md`` on
``research/uniform-rule``), passed its do-no-harm test (backend issue 51) and adopted as
the only forecast model (backend issue 49). It applies only to the campaign being
forecast, for Suspended Campaigns announced on or before the analysis cutoff; every
training campaign is fitted as before. For each exit, in date order:

* the latent date grid gains a node at the exit day;
* on every latent date on or after the exit, the departed candidate keeps
  ``k = min(exp(log_keep), 1)`` of their latent support, ``log_keep ~ Normal(mu, sigma)``
  over the usable cases of the ten-case table (``kept_fraction_prior``);
* the freed share ``(1 - k) * s_d`` goes to the remaining named candidates by
  ``allocation ~ Dirichlet(4 * c)``, ``c`` being their proportional split of the latent
  support at the exit node;
* Post-Suspension Readings (compositions over the remaining candidates) and election
  day read this transformed latent, with the existing house effects.

With no Post-Suspension Reading the allocation and the kept fraction keep their priors.
No reading informs the kept fraction, because Post-Suspension Readings leave the
departed candidate out. The model wiring is ``model.exit_support``.
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import jax.numpy as jnp
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
CASES = ROOT / "data" / "raw" / "elections" / "mayoral_suspended_campaigns.csv"
ALLOCATION_CONCENTRATION = 4.0


@dataclass(frozen=True)
class Exit:
    """One Suspended Campaign applied in a forecast campaign."""

    candidate: int  # index into the campaign's named candidates
    suspended_on: date  # public start of the Suspended Campaign
    day: int  # days before election day of that start
    keep_mu: float  # log-normal kept-fraction prior
    keep_sigma: float


def load_cases(path: Path = CASES) -> list[dict]:
    """The ten recorded Canadian cases of a mayoral campaign suspended on the ballot."""
    with Path(path).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def kept_fraction(row: dict) -> float | None:
    """Final share over the last pre-suspension poll share; None without a positive share."""
    last = row["last_poll_share_pct"]
    if last in ("", None) or float(last) <= 0:
        return None
    return float(row["final_share_pct"]) / float(last)


def kept_fraction_prior(rows: list[dict]) -> tuple[float, float]:
    """Mean and sample standard deviation of the usable cases' log kept fractions."""
    logs = [math.log(k) for row in rows for k in [kept_fraction(row)] if k is not None]
    if len(logs) < 2:
        raise ValueError(f"need at least two usable cases, got {len(logs)}")
    return float(np.mean(logs)), float(np.std(logs, ddof=1))


def exit_transform(s, post, departed: int, remaining, keep, allocation):
    """Latent support after one exit.

    ``s`` (T, K) latent support; ``post`` (T,) bool, dates on or after the exit;
    ``remaining`` index array; ``allocation`` sums to 1 over ``remaining``. Pre-exit
    rows are unchanged.
    """
    s = jnp.asarray(s)
    remaining = jnp.asarray(remaining)
    freed = (1.0 - keep) * s[:, departed]
    new = s.at[:, remaining].add(freed[:, None] * jnp.asarray(allocation)[None, :])
    new = new.at[:, departed].set(keep * s[:, departed])
    return jnp.where(jnp.asarray(post)[:, None], new, s)
