"""Fail-closed numerical qualification of a compact-model fit (ADR 0054).

A fit is publishable only if every non-constant coordinate mixed (split R-hat
below the threshold, bulk ESS above it) and no transition diverged. Anything
else raises, the build stops, and the previous release stays live.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Diagnostics:
    draws: int  # retained draws per chain
    chains: int
    divergences: int
    worst_r_hat: float
    min_ess: float
    coordinates_over_r_hat: int
    mean_leapfrog_steps: float
    constant_coordinates_ignored: int

    def as_dict(self) -> dict:
        return {
            "draws_per_chain": self.draws,
            "chains": self.chains,
            "divergences": self.divergences,
            "worst_r_hat": self.worst_r_hat,
            "min_ess": self.min_ess,
            "coordinates_over_r_hat": self.coordinates_over_r_hat,
            "mean_leapfrog_steps": self.mean_leapfrog_steps,
            "constant_coordinates_ignored": self.constant_coordinates_ignored,
        }


class QualificationError(RuntimeError):
    """The fit failed a numerical criterion; the reasons are listed in the message."""


def qualify(
    diagnostics: Diagnostics,
    *,
    max_r_hat: float = 1.01,
    min_ess: float = 400.0,
    max_divergences: int = 0,
) -> None:
    reasons = []
    if diagnostics.divergences > max_divergences:
        reasons.append(f"{diagnostics.divergences} divergent transitions (max {max_divergences})")
    if not math.isfinite(diagnostics.worst_r_hat):
        reasons.append("non-finite R-hat")
    elif diagnostics.worst_r_hat >= max_r_hat:
        reasons.append(
            f"worst R-hat {diagnostics.worst_r_hat:.4f} >= {max_r_hat} "
            f"({diagnostics.coordinates_over_r_hat} coordinates)"
        )
    if not math.isfinite(diagnostics.min_ess) or diagnostics.min_ess < min_ess:
        reasons.append(f"min bulk ESS {diagnostics.min_ess:.0f} < {min_ess:.0f}")
    if reasons:
        raise QualificationError("fit not qualified: " + "; ".join(reasons))
