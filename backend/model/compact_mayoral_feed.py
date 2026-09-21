"""Build the schema-4 mayoral forecast feed from the compact joint model (ADR 0054).

Publication policy ``margin-first-joint-draws-v1``: every public number comes
from one set of joint election-day draws. The feed carries full-ballot
vote-share medians with central 80% intervals for the named candidates and the
residual pool, the signed leader-minus-challenger margin as fixed five-point
bins, full-race win probabilities, the polls used, the analysis cutoff, a model
record, and two prespecified sensitivity refits as audit metadata.
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path

import numpy as np

from backend.model.compact_mayoral.hyperpriors import population_hyperpriors
from backend.model.compact_mayoral.qualification import QualificationError, qualify
from backend.model.compact_mayoral.readings import (
    CURRENT_FIELD,
    CampaignPolls,
    certified_candidates,
    current_campaign,
    historical_campaigns,
    minor_candidates_reported,
)
from backend.model.compact_mayoral.sampling import (
    PRODUCTION,
    SENSITIVITY,
    FitResult,
    FitSettings,
    fit_joint,
)

MAYORAL_FORECAST_FEED_SCHEMA_VERSION = 4
PUBLICATION_POLICY = "margin-first-joint-draws-v1"
TIER = "Compact joint model — certified field"
INTERVAL_MASS = 0.8
BIN_WIDTH = 5
BIN_RANGE = (-100, 100)
# The published three-outcome summary of the leader-minus-challenger margin: "ahead
# by at least this many points" on either side, and "within this many points" between.
CLOSE_THRESHOLD_POINTS = 2.0
SPECIFICATION = {
    "discrepancy": "isotropic",
    "innovations": "gaussian",
    "polls": "certified_field_only",
    "hyperpriors": "population_joint_refit",
}
REASON = "Joint election-day draws from the compact model over seven past campaigns and 2026."


def _r(value: float, places: int = 6) -> float:
    return round(float(value), places)


def _quantiles(x: np.ndarray) -> dict:
    lower, upper = (1 - INTERVAL_MASS) / 2, 1 - (1 - INTERVAL_MASS) / 2
    return {
        "median": _r(np.median(x)),
        "lower": _r(np.quantile(x, lower)),
        "upper": _r(np.quantile(x, upper)),
    }


def margin_bins(margins_points: np.ndarray) -> list[dict]:
    """Fixed five-point bins over [-100, 100]; the upper edge is closed."""
    lo, hi = BIN_RANGE
    edges = np.arange(lo, hi + BIN_WIDTH, BIN_WIDTH)
    x = np.clip(np.asarray(margins_points, dtype=float), lo, hi)
    counts, _ = np.histogram(x, bins=edges)
    counts = counts.astype(float)
    total = counts.sum()
    return [
        {"left": int(edges[i]), "right": int(edges[i + 1]), "probability": _r(counts[i] / total)}
        for i in range(len(edges) - 1)
    ]


def _git_version() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            cwd=Path(__file__).resolve().parent,
        ).stdout.strip()
    except OSError, subprocess.CalledProcessError:
        return "unknown"


def _card(candidate_id: str, probability: float) -> dict:
    return {
        "quantity": "challenger_win",
        "candidate_id": candidate_id,
        "tier": TIER,
        "availability": "Forecast Available",
        "probability": _r(probability),
        "reason": REASON,
    }


def assemble_forecast_feed(
    *,
    campaign: CampaignPolls,
    draws: dict[str, np.ndarray],
    live_cycle: dict,
    analysis_cutoff: datetime,
    model_record: dict,
    sensitivity: list[dict],
    residual_named: list[dict],
    residual_candidate_count: int,
) -> dict:
    prefix = campaign.key + "/"
    named = np.asarray(draws[prefix + "named_result"])
    full = np.asarray(draws[prefix + "full_ballot"])
    tail = np.asarray(draws[prefix + "tail"]).ravel()
    winners = named.argmax(axis=1)
    win = [float((winners == i).mean()) for i in range(len(campaign.candidates))]
    order = sorted(range(len(win)), key=lambda i: (-win[i], i))
    leader, challenger = order[0], order[1]
    margins = 100.0 * (full[:, leader] - full[:, challenger])
    return {
        "schema_version": MAYORAL_FORECAST_FEED_SCHEMA_VERSION,
        "publication_policy": PUBLICATION_POLICY,
        "election_cycle_id": live_cycle["election_cycle_id"].replace("-", "_"),
        "election_date": campaign.election_date.isoformat(),
        "analysis_cutoff": analysis_cutoff.isoformat(),
        "evidence_tier": TIER,
        "incumbent_candidate_id": live_cycle.get("incumbent_candidate_id"),
        "final_field_samples": [p.reading_id for p in campaign.polls],
        "forecast_favourite": {
            "tier": TIER,
            "availability": "Forecast Available",
            "candidate_id": campaign.candidates[leader],
            "reason": "Highest full-race win probability in the joint election-day draws.",
        },
        "candidate_win": {cid: _card(cid, win[i]) for i, cid in enumerate(campaign.candidates)},
        "election_day": {
            "denominator": "full_ballot",
            "interval_mass": INTERVAL_MASS,
            "statistic": "median",
            "candidates": [
                {
                    "candidate_id": cid,
                    "display_name": campaign.names[i],
                    **_quantiles(full[:, i]),
                    "win_probability": _r(win[i]),
                }
                for i, cid in enumerate(campaign.candidates)
            ],
            "residual_pool": {
                "label": "Other candidates",
                **_quantiles(tail),
                "win_probability": 0.0,
                "candidate_count": residual_candidate_count,
                "named_in_polls": residual_named,
                "note": "Many minor candidates, modelled as one pool; not one candidate.",
            },
            "pairwise_margin": {
                "leader_candidate_id": campaign.candidates[leader],
                "challenger_candidate_id": campaign.candidates[challenger],
                "unit": "vote_share_points",
                **_quantiles(margins),
                "probability_challenger_ahead": _r((margins < 0).mean()),
                # Exact three-way summary computed from the draws, not from the bins.
                "outcomes": {
                    "close_threshold_points": CLOSE_THRESHOLD_POINTS,
                    "leader_ahead": _r((margins >= CLOSE_THRESHOLD_POINTS).mean()),
                    "close": _r(
                        (
                            (margins > -CLOSE_THRESHOLD_POINTS) & (margins < CLOSE_THRESHOLD_POINTS)
                        ).mean()
                    ),
                    "challenger_ahead": _r((margins <= -CLOSE_THRESHOLD_POINTS).mean()),
                },
                "bin_width": BIN_WIDTH,
                "range": list(BIN_RANGE),
                "bins": margin_bins(margins),
            },
        },
        "model": model_record,
        "sensitivity": sensitivity,
    }


def _sensitivity_record(label: str, campaign: CampaignPolls, result: FitResult) -> dict:
    prefix = campaign.key + "/"
    named = np.asarray(result.draws[prefix + "named_result"])
    full = np.asarray(result.draws[prefix + "full_ballot"])
    winners = named.argmax(axis=1)
    win = {cid: _r((winners == i).mean()) for i, cid in enumerate(campaign.candidates)}
    order = sorted(range(len(campaign.candidates)), key=lambda i: (-win[campaign.candidates[i]], i))
    margins = 100.0 * (full[:, order[0]] - full[:, order[1]])
    return {
        "label": label,
        "role": "stress_test",
        "win_probability": win,
        "leader_margin": {
            "leader_candidate_id": campaign.candidates[order[0]],
            "challenger_candidate_id": campaign.candidates[order[1]],
            **_quantiles(margins),
        },
        "diagnostics": result.diagnostics.as_dict(),
    }


def build_compact_mayoral_forecast_feed(
    root: str | Path,
    live_cycle: dict,
    *,
    polls_dir: str | Path,
    analysis_cutoff: datetime,
    settings: FitSettings = PRODUCTION,
    sensitivity_settings: FitSettings = SENSITIVITY,
    qualification=qualify,
) -> dict:
    """Fit, qualify (fail closed), run the sensitivity refits, and assemble schema 4.

    ``qualification`` is the gate applied to the main fit's diagnostics; pass
    ``None`` only in tests that use short chains.
    """
    root = Path(root)
    polls_csv = Path(polls_dir) / "polls.csv"
    candidates_json = root / "data/upstream/results/mayoral_candidates.json"
    election_date = datetime.fromisoformat(live_cycle["election_date"]).date()
    history = tuple(historical_campaigns().values())
    current = current_campaign(polls_csv, candidates_json, election_date=election_date)
    hyperpriors = population_hyperpriors()

    result = fit_joint((*history, current), hyperpriors, settings=settings)
    if qualification is not None:
        try:
            qualification(result.diagnostics)
        except QualificationError as first:
            if result.diagnostics.divergences == 0:
                raise
            retry = FitSettings(
                warmup=settings.warmup,
                draws=settings.draws,
                chains=settings.chains,
                seed=settings.seed + 1,
                target_accept=0.99,
            )
            result = fit_joint((*history, current), hyperpriors, settings=retry)
            try:
                qualification(result.diagnostics)
            except QualificationError as second:
                raise QualificationError(f"{first}; retry: {second}") from second

    sensitivity = [
        _sensitivity_record(
            "leaders-discrepancy",
            current,
            fit_joint(
                (*history, current), hyperpriors, settings=sensitivity_settings, variant="leaders"
            ),
        )
    ]
    widened = current_campaign(
        polls_csv, candidates_json, election_date=election_date, require_full_field=False
    )
    sensitivity.append(
        _sensitivity_record(
            "with-pre-certification-polls",
            widened,
            fit_joint((*history, widened), hyperpriors, settings=sensitivity_settings),
        )
    )

    certified = certified_candidates(candidates_json)
    model_record = {
        "name": "compact_mayoral",
        "version": _git_version(),
        "specification": dict(SPECIFICATION),
        "draws": result.settings.draws * result.settings.chains,
        "chains": result.settings.chains,
        "warmup": result.settings.warmup,
        "seed": result.settings.seed,
        "target_accept": result.settings.target_accept,
        "qualification_passed": True if qualification is not None else None,
        "diagnostics": result.diagnostics.as_dict(),
        "historical_campaigns": [c.key for c in history],
        "historical_polls": sum(len(c.polls) for c in history),
        "elapsed_seconds": round(result.elapsed_seconds, 1),
    }
    return assemble_forecast_feed(
        campaign=current,
        draws=result.draws,
        live_cycle=live_cycle,
        analysis_cutoff=analysis_cutoff,
        model_record=model_record,
        sensitivity=sensitivity,
        residual_named=minor_candidates_reported(polls_csv, candidates_json),
        residual_candidate_count=len(certified) - len(CURRENT_FIELD),
    )


def write_feed(path: str | Path, feed: dict) -> None:
    Path(path).write_text(json.dumps(feed, allow_nan=False, indent=None), encoding="utf-8")
