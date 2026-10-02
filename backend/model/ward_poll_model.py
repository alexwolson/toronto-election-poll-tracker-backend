"""Small joint model for shares conditional on a poll's named set (ADR 0059).

Historical discrepancy includes sampling, response mapping and campaign movement.
Concentration is not an effective respondent count. No poll residual is allocated.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.polynomial.hermite import hermgauss
from scipy.special import gammaln, logsumexp

METHOD = "conditional-named-set-dirichlet-v1"
SEED = 20261002
DRAWS = 100_000


@dataclass(frozen=True)
class WardPollFit:
    mu: np.ndarray
    tau: np.ndarray
    weights: np.ndarray

    def concentrations(self, seed: int = SEED, draws: int = DRAWS) -> np.ndarray:
        rng = np.random.default_rng(seed)
        i = rng.choice(self.weights.size, size=draws, p=self.weights.ravel())
        return np.exp(self.mu.ravel()[i] + self.tau.ravel()[i] * rng.normal(size=draws))

    def predict(self, shares: np.ndarray, seed: int = SEED) -> np.ndarray:
        shares = np.asarray(shares, dtype=float)
        if len(shares) < 2 or np.any(shares <= 0) or not np.isfinite(shares).all():
            raise ValueError("ward model requires at least two positive named shares")
        p = shares / shares.sum()
        rng = np.random.default_rng(seed + 1)
        gamma = rng.gamma(self.concentrations(seed)[:, None] * p)
        totals = gamma.sum(axis=1)
        if np.any(totals == 0):
            raise ValueError("ward predictive draws underflowed")
        return gamma / totals[:, None]


def cohorts(errors: list[dict]) -> list[tuple[str, np.ndarray, np.ndarray]]:
    result = []
    for sid in sorted({r["sample_id"] for r in errors}):
        rows = [r for r in errors if r["sample_id"] == sid]
        p = np.array([r["poll_share"] for r in rows], dtype=float)
        q = np.array([r["result_share"] for r in rows], dtype=float)
        if len(rows) < 2 or np.any(p <= 0) or np.any(q <= 0):
            raise ValueError("historical named-set model requires positive matched shares")
        result.append((sid, p / p.sum(), q / q.sum()))
    return result


def fit(
    records: list[tuple[str, np.ndarray, np.ndarray]],
    *,
    prior_median: float = 30,
    tau_scale: float = 1,
    nodes: int = 64,
) -> WardPollFit:
    """Integrate a two-parameter hierarchical concentration model on a fixed grid.

    log(kappa_ward) ~ Normal(mu, tau), mu ~ Normal(log(30), 1.5),
    tau ~ HalfNormal(1). Each historical contest is one joint Dirichlet vector.
    Gaussian quadrature integrates ward-specific concentration; no MCMC gate.
    """
    mus = np.linspace(-4, 10, 351)
    taus = np.linspace(0, 4, 101)
    mu, tau = np.meshgrid(mus, taus, indexing="ij")
    h, w = hermgauss(nodes)
    k = np.exp(mu[..., None] + np.sqrt(2) * tau[..., None] * h)
    logw = np.log(w / np.sqrt(np.pi))
    posterior = -0.5 * ((mu - np.log(prior_median)) / 1.5) ** 2
    posterior -= 0.5 * (tau / tau_scale) ** 2
    # Trapezoidal endpoint weights; common grid widths cancel on normalization.
    posterior[:, 0] += np.log(0.5)
    posterior[:, -1] += np.log(0.5)
    for _, p, q in records:
        a = k[..., None] * p
        density = gammaln(k) - gammaln(a).sum(axis=-1)
        density += ((a - 1) * np.log(q)).sum(axis=-1)
        posterior += logsumexp(density + logw, axis=-1)
    weights = np.exp(posterior - logsumexp(posterior))
    edge_mass = weights[0, :].sum() + weights[-1, :].sum() + weights[:, -1].sum()
    if not np.isfinite(weights).all() or edge_mass > 0.001:
        raise ValueError("ward concentration posterior exceeds integration grid")
    return WardPollFit(mu, tau, weights)


def summary(draws: np.ndarray) -> dict:
    quantiles = np.quantile(draws, [0.025, 0.1, 0.5, 0.9, 0.975], axis=0)
    return {
        "lower_95": quantiles[0].tolist(),
        "lower": quantiles[1].tolist(),
        "median": quantiles[2].tolist(),
        "upper": quantiles[3].tolist(),
        "upper_95": quantiles[4].tolist(),
    }


def model_audit(errors: list[dict]) -> dict:
    records = cohorts(errors)
    fitted = fit(records)
    coarse = fit(records, nodes=32)
    total_variation = float(np.abs(fitted.weights - coarse.weights).sum() / 2)
    if total_variation > 0.005:
        raise ValueError("ward concentration quadrature did not converge")
    held_out = []
    for index, (sid, p, q) in enumerate(records):
        training = [r for r in records if r[0] != sid]
        predictions = fit(training).predict(p, SEED + index * 10)
        s = summary(predictions)
        lo, hi = np.array(s["lower"]), np.array(s["upper"])
        # Proper marginal interval score, averaged within a contest, then equally by contest.
        interval_score = hi - lo + 10 * np.maximum(lo - q, 0) + 10 * np.maximum(q - hi, 0)
        held_out.append(
            {
                "omitted_sample": sid,
                "named_candidates": len(p),
                "covered_80": int(np.sum((q >= lo) & (q <= hi))),
                "covered_95": int(np.sum((q >= s["lower_95"]) & (q <= s["upper_95"]))),
                "mean_interval_width": float(np.mean(hi - lo)),
                "mean_interval_score": float(np.mean(interval_score)),
                "poll_point_mae": float(np.mean(np.abs(p - q))),
                "model_median_mae": float(np.mean(np.abs(s["median"] - q))),
                "actual": q.tolist(),
                **s,
            }
        )
    concentration = fitted.concentrations()
    return {
        "name": METHOD,
        "denominator": "named_candidates",
        "interval_mass": 0.8,
        "draws": DRAWS,
        "seed": SEED,
        "prior": {"mu_mean": float(np.log(30)), "mu_sd": 1.5, "tau_half_normal_sd": 1},
        "posterior_concentration_10_50_90": np.quantile(concentration, [0.1, 0.5, 0.9]).tolist(),
        "quadrature_total_variation": total_variation,
        "qualification_passed": True,
        "leave_one_contest_out": held_out,
        "mean_held_out_interval_score": float(
            np.mean([r["mean_interval_score"] for r in held_out])
        ),
        "note": "Model-based ranges conditional on the named set; one historical firm/cycle. "
        "Total discrepancy is transferred to current mixed-mode polls without sample-size "
        "shrinkage. Cross-cycle and mode-transfer errors cannot be estimated from this corpus.",
    }


def logistic_normal_prediction(records, shares: np.ndarray) -> np.ndarray:
    """One-scale alternative family; no fitted covariance or candidate effects."""
    x = np.linspace(-5, 4, 1801)
    scale = np.exp(x)
    scores = -0.5 * ((x - np.log(0.8)) / 1) ** 2
    for _, p, q in records:
        residual = np.log(q) - np.log(p)
        residual -= residual.mean()
        scores -= (len(p) - 1) * x + np.sum(residual**2) / (2 * scale**2)
    weights = np.exp(scores - logsumexp(scores))
    if weights[[0, -1]].sum() > 0.001:
        raise ValueError("logistic-normal sensitivity exceeds integration grid")
    rng = np.random.default_rng(SEED)
    sigma = rng.choice(scale, size=DRAWS, p=weights)
    p = shares / shares.sum()
    logits = np.log(p) + sigma[:, None] * rng.normal(size=(DRAWS, len(p)))
    logits -= logits.max(axis=1, keepdims=True)
    values = np.exp(logits)
    return values / values.sum(axis=1, keepdims=True)
