"""NUTS fit of the compact model with the diagnostics the qualification gate needs."""

from __future__ import annotations

import time
from dataclasses import dataclass

import jax
import numpy as np
from numpyro.diagnostics import summary as numpyro_summary
from numpyro.infer import MCMC, NUTS

from .model import build_model
from .qualification import Diagnostics
from .readings import CampaignPolls


@dataclass(frozen=True)
class FitSettings:
    warmup: int = 1000
    draws: int = 4000
    chains: int = 4
    seed: int = 20260921
    target_accept: float = 0.95


PRODUCTION = FitSettings()
SENSITIVITY = FitSettings(draws=1000)


@dataclass(frozen=True)
class FitResult:
    draws: dict[str, np.ndarray]  # chains merged: (chains * draws, ...) per site
    diagnostics: Diagnostics
    elapsed_seconds: float
    settings: FitSettings


def _diagnostics(grouped: dict, extras: dict, flat: dict, settings: FitSettings) -> Diagnostics:
    # Constant coordinates (deterministic functions of observed results) carry no
    # mixing information; their R-hat is floating-point noise and is excluded.
    with np.errstate(invalid="ignore", divide="ignore"):  # constant coordinates divide by zero
        summary = numpyro_summary(grouped, prob=0.9, group_by_chain=True)
    worst, lowest, over, ignored = -np.inf, np.inf, 0, 0
    for site, stats in summary.items():
        r_hat = np.asarray(stats["r_hat"], dtype=float).ravel()
        ess = np.asarray(stats["n_eff"], dtype=float).ravel()
        varying = flat[site].reshape(flat[site].shape[0], -1).std(axis=0) > 1e-9
        ignored += int((~varying).sum())
        keep = np.isfinite(r_hat) & varying
        if keep.any():
            worst = max(worst, float(r_hat[keep].max()))
            lowest = min(lowest, float(ess[keep].min()))
            over += int((r_hat[keep] >= 1.01).sum())
    steps = np.asarray(extras["num_steps"], dtype=float)
    return Diagnostics(
        draws=settings.draws,
        chains=settings.chains,
        divergences=int(np.asarray(extras["diverging"]).sum()),
        worst_r_hat=float(worst) if np.isfinite(worst) else float("nan"),
        min_ess=float(lowest) if np.isfinite(lowest) else float("nan"),
        coordinates_over_r_hat=over,
        mean_leapfrog_steps=float(steps.mean()),
        constant_coordinates_ignored=ignored,
    )


def fit_joint(
    campaigns: tuple[CampaignPolls, ...],
    hyperpriors: dict,
    *,
    settings: FitSettings = PRODUCTION,
    variant: str = "isotropic",
    innovations: str = "gaussian",
) -> FitResult:
    """Fit all campaigns jointly; returns merged draws of every site plus diagnostics."""
    jax.config.update("jax_enable_x64", True)
    started = time.monotonic()
    model = build_model(campaigns, hyperpriors, variant=variant, innovations=innovations)
    kernel = NUTS(model, target_accept_prob=settings.target_accept, dense_mass=False)
    parallel = jax.local_device_count() >= settings.chains
    mcmc = MCMC(
        kernel,
        num_warmup=settings.warmup,
        num_samples=settings.draws,
        num_chains=settings.chains,
        chain_method="parallel" if parallel else "sequential",
        progress_bar=False,
    )
    mcmc.run(jax.random.key(settings.seed), extra_fields=("diverging", "num_steps"))
    grouped = mcmc.get_samples(group_by_chain=True)
    flat = {k: np.asarray(v).reshape((-1,) + np.asarray(v).shape[2:]) for k, v in grouped.items()}
    extras = mcmc.get_extra_fields(group_by_chain=True)
    diagnostics = _diagnostics(grouped, extras, flat, settings)
    return FitResult(
        draws=flat,
        diagnostics=diagnostics,
        elapsed_seconds=time.monotonic() - started,
        settings=settings,
    )
