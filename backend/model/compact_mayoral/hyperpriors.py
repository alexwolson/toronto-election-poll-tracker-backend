"""Priors on the compact model's shared scales.

The production fit uses the population priors below, the same elicited scales
the research integrated model used (``integrated_mayoral.state.Settings`` and
``survey.build_model``), so the joint refit over all campaigns learns the scales
from history rather than borrowing them.
"""

from __future__ import annotations

import numpy as np
import numpyro.distributions as dist

GLOBALS = (
    "m_move",
    "omega_move",
    "tau_firm",
    "tau_election",
    "phi_election",
    "kappa",
    "tau_reference",
    "mu_tail",
    "sigma_tail",
)


def population_hyperpriors() -> dict:
    return {
        "mode": "population",
        "source": "integrated_mayoral state.Settings defaults and survey.build_model priors",
        "sites": {
            "m_move": {"dist": "HalfNormal", "scale": 0.10},
            "omega_move": {"dist": "HalfNormal", "scale": 0.35},
            "tau_firm": {"dist": "HalfNormal", "scale": 0.15},
            "tau_election": {"dist": "HalfNormal", "scale": 0.30},
            "kappa": {"dist": "LogNormal", "mu": float(np.log(1.5)), "sigma": 0.5},
            "tau_reference": {"dist": "HalfNormal", "scale": 0.05},
            "mu_tail": {"dist": "Normal", "loc": float(np.log(0.08 / 0.92)), "scale": 1.0},
            "sigma_tail": {"dist": "HalfNormal", "scale": 1.0},
            # Election-day Dirichlet precision (ADR 0055), pre-registered 2026-09-22 before
            # the held-out test: spans roughly phi = 2 to 600.
            "phi_election": {"dist": "LogNormal", "mu": float(np.log(40.0)), "sigma": 1.5},
        },
    }


def prior_distribution(spec: dict):
    kind = spec["dist"]
    if kind == "HalfNormal":
        return dist.HalfNormal(spec["scale"])
    if kind == "LogNormal":
        return dist.LogNormal(spec["mu"], spec["sigma"])
    if kind == "Normal":
        return dist.Normal(spec["loc"], spec["scale"])
    raise ValueError(f"unknown prior family {kind!r}")
