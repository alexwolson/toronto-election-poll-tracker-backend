"""Hyperprior specifications for the compact model, with provenance.

Two modes:

* ``population``: the heavy model's own priors on the shared scales
  (``integrated_mayoral.state.Settings`` and ``survey.build_model``), for a joint
  refit over all campaigns.
* ``borrowed``: LogNormal/Normal summaries of the shared-scale posteriors from a
  completed heavy fit, for fitting the 2026 campaign alone. Every number is
  derived from the saved draws by :func:`summarize_globals`; nothing is typed in.

Usage (writes the provenance JSON)::

    uv run --no-project --with numpyro --with jax python -m \
        docs.research.compact_mayoral.hyperpriors <heavy_run_dir> <out.json>
"""

from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

import numpy as np
import numpyro.distributions as dist

GLOBALS = (
    "m_move",
    "omega_move",
    "tau_firm",
    "tau_election",
    "kappa",
    "tau_reference",
    "mu_tail",
    "sigma_tail",
)
LOCATIONS = {"mu_tail"}  # real-valued; every other global is a positive scale


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
            # Support-scaling exponent for the `support_scaled` variant (pre-registered
            # 2026-09-22): symmetric on [0, 1], mean 0.5, no mass at the ends.
            "gamma_election": {"dist": "Beta", "concentration1": 2.0, "concentration0": 2.0},
            # Election-day Dirichlet precision for the `dirichlet` variant (pre-registered
            # 2026-09-22, round 2): spans roughly phi = 2 to 600.
            "phi_election": {"dist": "LogNormal", "mu": float(np.log(40.0)), "sigma": 1.5},
            # Final-fortnight movement multiplier for the `late_movement` option (width
            # defence, 2026-09-22): median 1, 80% interval about 0.5 to 2.
            "late_move": {"dist": "LogNormal", "mu": 0.0, "sigma": 0.5},
        },
    }


def summarize_globals(run_dir: Path | str) -> dict[str, dict]:
    """Posterior summaries of the shared scales over every chain and retained chunk."""
    run_dir = Path(run_dir)
    parts = {name: [] for name in GLOBALS}
    files = sorted(glob.glob(str(run_dir / "chain-*" / "draws-*.npz")))
    if not files:
        raise FileNotFoundError(f"no chain-*/draws-*.npz under {run_dir}")
    for file in files:
        with np.load(file) as draws:
            for name in GLOBALS:
                if name in draws.files:
                    parts[name].append(np.asarray(draws[name], dtype=float).ravel())
    summary = {}
    for name, chunks in parts.items():
        if not chunks:
            continue
        x = np.concatenate(chunks)
        q05, q50, q95 = np.quantile(x, [0.05, 0.5, 0.95])
        record = {
            "n": int(x.size),
            "mean": float(x.mean()),
            "sd": float(x.std()),
            "q05": float(q05),
            "q50": float(q50),
            "q95": float(q95),
        }
        if name not in LOCATIONS:
            logs = np.log(x)
            record.update({"log_mean": float(logs.mean()), "log_sd": float(logs.std())})
        summary[name] = record
    return summary


def borrowed_hyperpriors(summary: dict[str, dict], source: str | None = None) -> dict:
    sites = {}
    for name, record in summary.items():
        if name in LOCATIONS:
            sites[name] = {"dist": "Normal", "loc": record["mean"], "scale": record["sd"]}
        else:
            sites[name] = {"dist": "LogNormal", "mu": record["log_mean"], "sigma": record["log_sd"]}
    return {"mode": "borrowed", "source": source, "summary": summary, "sites": sites}


def write_hyperpriors(run_dir: Path | str, out_path: Path | str) -> dict:
    summary = summarize_globals(run_dir)
    missing = set(GLOBALS) - set(summary)
    if missing:
        raise ValueError(f"heavy run lacks shared scales: {sorted(missing)}")
    record = borrowed_hyperpriors(summary, source=str(Path(run_dir).resolve()))
    Path(out_path).write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return record


def load_hyperpriors(path: Path | str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def prior_distribution(spec: dict):
    kind = spec["dist"]
    if kind == "HalfNormal":
        return dist.HalfNormal(spec["scale"])
    if kind == "LogNormal":
        return dist.LogNormal(spec["mu"], spec["sigma"])
    if kind == "Normal":
        return dist.Normal(spec["loc"], spec["scale"])
    if kind == "Beta":
        return dist.Beta(spec["concentration1"], spec["concentration0"])
    raise ValueError(f"unknown prior family {kind!r}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: hyperpriors.py <heavy_run_dir> <out.json>")
    written = write_hyperpriors(sys.argv[1], sys.argv[2])
    for name, spec in written["sites"].items():
        print(
            name, json.dumps(spec), "| posterior mean", round(written["summary"][name]["mean"], 4)
        )
