"""Build the mayoral_forecast.json feed from the lightweight three-component
poll-average model (ADR: replaces the endpoint model as the published forecast).

Emits schema v3 ("central-band-with-sensitivity-v1"): a bridge-base central estimate
plus stable/volatile stress variants, published as the finest ADR-0006 band on which
all variants agree, with the per-variant sensitivity range. Output is keyed by
canonical Results person IDs (viable_field / incumbent_candidate_id), matching the
feed contract the frontend resolves from the Backend release. The lightweight model
itself works in local poll keys (chow/bradford/alexander); this builder maps between
the two using the certified mayoral candidate feed.
"""

from __future__ import annotations

import csv
import json
from datetime import date, datetime
from pathlib import Path

import numpy as np

from backend.model.lightweight_mayoral import ForecastConfig, Poll, forecast
from backend.model.mayoral_candidate_ids import mayoral_candidate_id

MAYORAL_FORECAST_FEED_SCHEMA_VERSION = 3
TIER = "Lightweight poll-average — central band with assumption sensitivity"

# ADR-0006 band grids (verbatim from backend/model/publication.py), finest first.
GRID10 = [
    (0.0, 0.05, "0–<5%", "less than 1 in 10"),
    (0.05, 0.15, "5–<15%", "about 1 in 10"),
    (0.15, 0.25, "15–<25%", "about 2 in 10"),
    (0.25, 0.35, "25–<35%", "about 3 in 10"),
    (0.35, 0.45, "35–<45%", "about 4 in 10"),
    (0.45, 0.55, "45–<55%", "about 5 in 10"),
    (0.55, 0.65, "55–<65%", "about 6 in 10"),
    (0.65, 0.75, "65–<75%", "about 7 in 10"),
    (0.75, 0.85, "75–<85%", "about 8 in 10"),
    (0.85, 0.95, "85–<95%", "about 9 in 10"),
    (0.95, 1.01, "95–100%", "more than 9 in 10"),
]
GRID5 = [
    (0.0, 0.10, "0–<10%", "less than 1 in 5"),
    (0.10, 0.30, "10–<30%", "about 1 in 5"),
    (0.30, 0.50, "30–<50%", "about 2 in 5"),
    (0.50, 0.70, "50–<70%", "about 3 in 5"),
    (0.70, 0.90, "70–<90%", "about 4 in 5"),
    (0.90, 1.01, "90–100%", "more than 4 in 5"),
]

# Sensitivity variants over the three-component uncertainty model; "bridge-base" is
# the authoritative central calibration (see the Polling methodology doc).
VARIANTS = {
    "bridge-base": {},
    "stable": {
        "polling_error_sd": 0.035,
        "drift_sd": 0.020,
        "soft_fraction_range": (0.15, 0.35),
        "split_to_target": 0.45,
        "dropout_prob": 0.02,
    },
    "volatile": {
        "polling_error_sd": 0.055,
        "drift_sd": 0.050,
        "soft_fraction_range": (0.35, 0.70),
        "split_to_target": 0.65,
        "dropout_prob": 0.10,
    },
}
LABELS = list(VARIANTS)
_ELECTION_DATE = date(2026, 10, 26)


def _band_idx(p, grid):
    for i, (lo, hi, _, _) in enumerate(grid):
        if lo <= p < hi:
            return i
    return len(grid) - 1


def _finest_stable_band(probs):
    """Finest grid on which every variant lands in the same band (ADR-0006 rule)."""
    for grid in (GRID10, GRID5):
        idxs = {_band_idx(p, grid) for p in probs}
        if len(idxs) == 1:
            _, _, label, freq = grid[idxs.pop()]
            return label, freq
    _, _, label, freq = GRID5[_band_idx(probs[0], GRID5)]
    return label, freq


def _card(quantity, candidate_id, central_p, variant_ps):
    scenarios = [
        {
            "label": lab,
            "role": "authoritative" if lab == "bridge-base" else "stress_test",
            "probability": round(float(variant_ps[lab]), 6),
        }
        for lab in LABELS
    ]
    label, freq = _finest_stable_band([variant_ps[lab] for lab in LABELS])
    central = round(float(central_p), 6)
    for s in scenarios:
        if s["label"] == "bridge-base":
            s["probability"] = central
    lower = min(min(s["probability"] for s in scenarios), central)
    upper = max(max(s["probability"] for s in scenarios), central)
    return {
        "quantity": quantity,
        "candidate_id": candidate_id,
        "tier": TIER,
        "availability": "Forecast Available",
        "band": label,
        "frequency_statement": freq,
        "probability": central,
        "reason": "Poll-average central estimate; band is the finest ADR-0006 level on "
        "which the stable/central/volatile assumption variants agree.",
        "sensitivity": {
            "kind": "model_assumptions",
            "lower": lower,
            "upper": upper,
            "includes_monte_carlo_error": True,
            "scenarios": scenarios,
        },
    }


def _margin_distribution(samples):
    """Reflected (at 0) Gaussian KDE of the winner-minus-runner-up gap, numpy-only."""
    s = np.asarray(samples)
    if s.size > 20000:
        s = np.random.default_rng(0).choice(s, 20000, replace=False)
    data = np.concatenate([s, -s])
    iqr = np.subtract(*np.percentile(data, [75, 25]))
    bw = max(0.9 * min(data.std(), iqr / 1.34) * data.size ** (-0.2), 1e-3)
    x = np.linspace(0.0, min(0.6, float(s.max()) * 1.1 + 0.05), 120)
    z = (x[:, None] - data[None, :]) / bw
    dens = 2.0 * np.exp(-0.5 * z**2).sum(axis=1) / (data.size * bw * np.sqrt(2 * np.pi))
    return {
        "unit": "share_gap",
        "x": [round(float(v), 6) for v in x],
        "density": [round(float(d), 6) for d in dens],
        "close_threshold": 0.05,
    }


def _person_to_local(root: Path, viable_field) -> dict[str, str]:
    """Map each certified viable person ID to its local poll key via display name."""
    feed = json.loads((root / "data/upstream/results/mayoral_candidates.json").read_text())
    display = {
        (c.get("person_id") or c["candidacy_id"]): c["display_name"] for c in feed["candidates"]
    }
    mapping = {}
    for pid in viable_field:
        name = display[pid]
        parts = name.split()
        mapping[pid] = mayoral_candidate_id(parts[0], " ".join(parts[1:]))
    return mapping


def _load_polls(polls_csv: Path, field_local):
    """Read the descriptive polls.csv into Poll rows keyed by local candidate columns."""
    polls, ids_by_key = [], {}
    with polls_csv.open(encoding="utf-8") as handle:
        for r in csv.DictReader(handle):
            shares = {
                c: float(r[c]) for c in list(field_local) + ["other"] if r.get(c) not in ("", None)
            }
            p = Poll(
                firm=r["firm"],
                date=date.fromisoformat(r["date_conducted"]),
                n=float(r["sample_size"]) if r["sample_size"] else None,
                shares=shares,
            )
            polls.append(p)
            ids_by_key[id(p)] = r["poll_id"]
    return polls, ids_by_key


def build_lightweight_mayoral_forecast_feed(
    root: str | Path, live_cycle: dict, *, polls_dir: str | Path, analysis_cutoff: datetime
) -> dict:
    """Assemble the schema-3 mayoral forecast feed from the lightweight model, keyed by
    canonical person IDs. ``polls_dir`` is the hydrated Polling release model/polls dir."""
    root = Path(root)
    viable = list(live_cycle["viable_field"])
    incumbent_pid = live_cycle["incumbent_candidate_id"]
    person_to_local = _person_to_local(root, viable)
    field_local = tuple(person_to_local[pid] for pid in viable)
    local_to_person = {loc: pid for pid, loc in person_to_local.items()}
    incumbent_local = person_to_local[incumbent_pid]

    polls, ids_by_key = _load_polls(Path(polls_dir) / "polls.csv", field_local)
    asof = analysis_cutoff.date()
    base = {"field": field_local, "election_date": _ELECTION_DATE, "asof": asof}
    results = {
        lab: forecast(polls, ForecastConfig(**base, **params)) for lab, params in VARIANTS.items()
    }
    central = results["bridge-base"]

    covered = [ids_by_key[id(p)] for p in polls if all(c in p.shares for c in field_local)]

    candidate_win = {}
    for loc in field_local:
        pid = local_to_person[loc]
        variant_ps = {lab: results[lab]["win_prob"][loc] for lab in LABELS}
        candidate_win[pid] = _card("challenger_win", pid, central["win_prob"][loc], variant_ps)

    close = _card(
        "close_result",
        None,
        central["close_prob"],
        {lab: results[lab]["close_prob"] for lab in LABELS},
    )
    defeat = _card(
        "incumbent_defeat",
        None,
        1 - central["win_prob"][incumbent_local],
        {lab: 1 - results[lab]["win_prob"][incumbent_local] for lab in LABELS},
    )
    favourite_local = max(field_local, key=lambda c: central["win_prob"][c])

    return {
        "schema_version": MAYORAL_FORECAST_FEED_SCHEMA_VERSION,
        "publication_policy": "central-band-with-sensitivity-v1",
        "analysis_cutoff": analysis_cutoff.isoformat(),
        "sensitivity_variant_labels": LABELS,
        "election_cycle_id": live_cycle["election_cycle_id"],
        "evidence_tier": TIER,
        "final_field_samples": covered,
        "incumbent_candidate_id": incumbent_pid,
        "forecast_favourite": {
            "tier": TIER,
            "availability": "Forecast Available",
            "candidate_id": local_to_person[favourite_local],
            "reason": "Highest poll-average win probability across the viable field.",
        },
        "candidate_win": candidate_win,
        "close_result": close,
        "incumbent_defeat": defeat,
        "margin_distribution": _margin_distribution(central["winner_gap_samples"]),
        "challenger_chance_decomposition": {
            k: round(float(v), 6) if isinstance(v, float) else v
            for k, v in central["decomposition"].items()
        },
    }
