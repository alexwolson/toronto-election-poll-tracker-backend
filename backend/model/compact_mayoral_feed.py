"""Build the schema-4 mayoral forecast feed from the compact joint model (ADR 0054).

Publication policy ``margin-first-joint-draws-v1``: every public number comes
from one set of joint election-day draws. The feed carries full-ballot
vote-share medians with central 80% intervals for the named candidates and the
residual pool, the signed leader-minus-challenger margin as fixed five-point
bins, full-race win probabilities, the polls used, the analysis cutoff, a model
record, two prespecified sensitivity refits as audit metadata, and where the
uncertainty comes from (ADR 0056): the leader margin under each source of doubt on
its own (poll noise, campaign movement, election-day error) and under all three
together, which is the published margin.
"""

from __future__ import annotations

import csv
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np

from backend.model.compact_mayoral.hyperpriors import population_hyperpriors
from backend.model.compact_mayoral.qualification import QualificationError, qualify
from backend.model.compact_mayoral.readings import (
    CURRENT_FIELD,
    CURRENT_KEY,
    CampaignPolls,
    _campaign_polls,
    certified_candidates,
    current_campaign,
    current_reading_selection,
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
    "discrepancy": "dirichlet",
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
    scale = (1.0 - tail)[:, None]

    def gap(site: str) -> np.ndarray:
        # Leader-minus-challenger gap for one snapshot of the same draws, in
        # full-ballot points like the published margin.
        shares = np.asarray(draws[prefix + site]) * scale
        return 100.0 * (shares[:, leader] - shares[:, challenger])

    def summary(x: np.ndarray) -> dict:
        return {
            **_quantiles(x),
            "probability_leader_ahead": _r((x > 0).mean()),
            "probability_challenger_ahead": _r((x < 0).mean()),
        }

    # Where the uncertainty comes from (ADR 0056): each source on its own, applied
    # to today's middle estimate, then all three together, which is the result.
    now, at_election, result = gap("current"), gap("election_support"), gap("named_result")
    centre = float(np.median(now))
    parts = [
        ("polls_today", now - centre),
        ("campaign_movement", at_election - now),
        ("election_day", result - at_election),
    ]
    # The three parts are close to independent in the fit, so their variances add up
    # to the total within a percent; each source's share of that sum is the additive
    # number a reader can add up, which its range and its "ahead" chance are not.
    variances = [float(np.var(x)) for _, x in parts]
    explained = sum(variances)
    uncertainty_sources = [
        {"key": key, **summary(centre + x), "share_of_uncertainty": _r(v / explained)}
        for (key, x), v in zip(parts, variances, strict=True)
    ]

    return {
        "schema_version": MAYORAL_FORECAST_FEED_SCHEMA_VERSION,
        "publication_policy": PUBLICATION_POLICY,
        "election_cycle_id": live_cycle["election_cycle_id"].replace("-", "_"),
        "election_date": campaign.election_date.isoformat(),
        "analysis_cutoff": analysis_cutoff.isoformat(),
        "evidence_tier": TIER,
        "incumbent_candidate_id": live_cycle.get("incumbent_candidate_id"),
        "final_field_samples": [p.group for p in campaign.polls],
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
        "uncertainty": {
            "leader_candidate_id": campaign.candidates[leader],
            "challenger_candidate_id": campaign.candidates[challenger],
            "unit": "vote_share_points",
            "interval_mass": INTERVAL_MASS,
            "statistic": "median",
            "centre": _r(centre),
            "sources": uncertainty_sources,
            "combined": summary(result),
            "variance_explained": _r(explained / float(np.var(result))),
            "note": (
                "Each source is applied on its own to today's middle estimate of the gap: "
                "the polls' own noise; five more weeks of movement; the election-day "
                "difference from final polls. 'combined' is all three together and equals "
                "the published margin. share_of_uncertainty is each source's variance as a "
                "fraction of the three sources' summed variance (they add to 1); ranges and "
                "'ahead' chances do not add. variance_explained is that sum over the "
                "combined variance."
            ),
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


@dataclass(frozen=True)
class HistoryCutoff:
    """The 2026 campaign as it stood after the polls published on ``date``."""

    date: str
    new_samples: list[str]
    campaign: CampaignPolls


def history_cutoffs(campaign: CampaignPolls, published: dict[str, str]) -> list[HistoryCutoff]:
    """One cutoff per distinct publication date, oldest first.

    A poll moves the forecast only once it is published, so each cutoff holds the
    polls published on or before its date (a late release of early fieldwork
    lands on its publication date). The last cutoff is the full campaign.
    """
    missing = sorted({p.group for p in campaign.polls} - set(published))
    if missing:
        raise ValueError(f"no publication date for sample(s) {missing}")
    cutoffs = []
    for day in sorted({published[p.group] for p in campaign.polls}):
        polls = [p for p in campaign.polls if published[p.group] <= day]
        cutoffs.append(
            HistoryCutoff(
                date=day,
                new_samples=sorted(p.group for p in polls if published[p.group] == day),
                campaign=_campaign_polls(
                    CURRENT_KEY,
                    campaign.candidates,
                    campaign.names,
                    campaign.election_date,
                    polls,
                    None,
                    None,
                ),
            )
        )
    return cutoffs


def _qualified_fit(campaigns, hyperpriors, settings: FitSettings, qualification) -> FitResult:
    """Fit; if the gate fails with divergences, retry once at a tighter acceptance."""
    result = fit_joint(campaigns, hyperpriors, settings=settings)
    if qualification is None:
        return result
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
        result = fit_joint(campaigns, hyperpriors, settings=retry)
        try:
            qualification(result.diagnostics)
        except QualificationError as second:
            raise QualificationError(f"{first}; retry: {second}") from second
    return result


def _history_point(cutoff: HistoryCutoff, result: FitResult) -> dict:
    campaign = cutoff.campaign
    named = np.asarray(result.draws[CURRENT_KEY + "/named_result"])
    winners = named.argmax(axis=1)
    return {
        "date": cutoff.date,
        "poll_sample_ids": cutoff.new_samples,
        "polls": len(campaign.polls),
        "win_probability": {
            cid: _r(float((winners == i).mean())) for i, cid in enumerate(campaign.candidates)
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
    polling = Path(polls_dir)
    polls_csv = polling / "polls.csv"
    candidates_json = root / "data/upstream/results/mayoral_candidates.json"
    election_date = datetime.fromisoformat(live_cycle["election_date"]).date()
    history = tuple(historical_campaigns().values())
    current = current_campaign(polling, candidates_json, election_date=election_date)
    hyperpriors = population_hyperpriors()

    result = _qualified_fit((*history, current), hyperpriors, settings, qualification)

    # How the forecast would have stood after each release, recomputed with this
    # model (same settings and gate); the last point is the main fit.
    published = {
        row["poll_sample_id"]: row["publication_date"]
        for row in csv.DictReader((polling / "poll_samples.csv").open(encoding="utf-8"))
    }
    cutoffs = history_cutoffs(current, published)
    forecast_history = [
        _history_point(
            cutoff,
            _qualified_fit((*history, cutoff.campaign), hyperpriors, settings, qualification),
        )
        for cutoff in cutoffs[:-1]
    ]
    forecast_history.append(_history_point(cutoffs[-1], result))

    sensitivity = [
        _sensitivity_record(
            "isotropic-discrepancy",
            current,
            fit_joint(
                (*history, current), hyperpriors, settings=sensitivity_settings, variant="isotropic"
            ),
        )
    ]
    widened = current_campaign(
        polling, candidates_json, election_date=election_date, require_full_field=False
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
        # The reading chosen per 2026 sample and its own base (ADR 0057).
        "current_readings": current_reading_selection(polling),
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
    feed = assemble_forecast_feed(
        campaign=current,
        draws=result.draws,
        live_cycle=live_cycle,
        analysis_cutoff=analysis_cutoff,
        model_record=model_record,
        sensitivity=sensitivity,
        residual_named=minor_candidates_reported(polls_csv, candidates_json),
        residual_candidate_count=len(certified) - len(CURRENT_FIELD),
    )
    feed["history"] = forecast_history
    return feed


def write_feed(path: str | Path, feed: dict) -> None:
    Path(path).write_text(json.dumps(feed, allow_nan=False, indent=None), encoding="utf-8")
