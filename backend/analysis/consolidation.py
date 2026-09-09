"""Descriptive pool concentration and conditional transfers between 2026 challengers.

Historical changes are accounting identities, not measured individual switching
rates or causal Tory effects. A scenario's rival fraction is a net assumption.
"""

import hashlib
import json
import math
import statistics
from collections.abc import Mapping
from datetime import date
from pathlib import Path

POOL_2023 = ("bailao", "saunders", "furey", "bradford")


def summarize_pool(shares: Mapping[str, float], recipient: str = "bailao") -> dict:
    if recipient not in shares or any(not math.isfinite(x) or x < 0 for x in shares.values()):
        raise ValueError("Pool must include the recipient and finite, nonnegative support.")
    pool = sum(shares.values())
    if pool <= 0:
        raise ValueError("Historical pool must have positive support.")
    return {
        "recipient_share_pp": shares[recipient],
        "rival_share_pp": pool - shares[recipient],
        "pool_share_pp": pool,
        "recipient_pool_fraction": shares[recipient] / pool,
    }


def compare_pools(before: Mapping[str, float], after: Mapping[str, float]) -> dict:
    """Separate concentration and pool growth with a symmetric accounting identity."""
    if set(before) != set(after):
        raise ValueError("Compare the same candidate set at both dates.")
    pre, post = summarize_pool(before), summarize_pool(after)
    p0, p1 = pre["pool_share_pp"], post["pool_share_pp"]
    q0, q1 = pre["recipient_pool_fraction"], post["recipient_pool_fraction"]
    return {
        "before": pre,
        "after": post,
        "recipient_change_pp": post["recipient_share_pp"] - pre["recipient_share_pp"],
        "rival_change_pp": post["rival_share_pp"] - pre["rival_share_pp"],
        "pool_change_pp": p1 - p0,
        "pool_fraction_change": q1 - q0,
        "gap_closed_fraction": (q1 - q0) / (1 - q0) if q0 < 1 else None,
        "rival_net_decline_fraction": (
            1 - post["rival_share_pp"] / pre["rival_share_pp"]
            if pre["rival_share_pp"] > 0
            else None
        ),
        "concentration_component_pp": (p0 + p1) / 2 * (q1 - q0),
        "pool_growth_component_pp": (q0 + q1) / 2 * (p1 - p0),
    }


def calculate_consolidation(
    baseline: Mapping[str, float], recipient: str, rival_fraction: float
) -> dict:
    """Move a net fraction of the other challenger's dated support to the recipient.

Chow and the residual are fixed. The fraction already describes the realized
transfer, so no date-based retention assumption is applied a second time.
"""
    if set(baseline) != {"chow", "bradford", "alexander", "residual"}:
        raise ValueError("Expected Chow, Bradford, Alexander and residual shares.")
    if any(not math.isfinite(x) or x < 0 for x in baseline.values()):
        raise ValueError("Shares must be finite and nonnegative.")
    if not math.isclose(sum(baseline.values()), 100, rel_tol=0, abs_tol=1e-8):
        raise ValueError("Shares must sum to 100.")
    if recipient not in ("bradford", "alexander") or not 0 <= rival_fraction <= 1:
        raise ValueError("Expected a challenger recipient and rival fraction from 0 to 1.")
    rival = "alexander" if recipient == "bradford" else "bradford"
    pool = baseline[recipient] + baseline[rival]
    gain = rival_fraction * baseline[rival]
    shares = dict(baseline)
    shares[recipient] += gain
    shares[rival] -= gain
    tie_gain = max(
        0, baseline["chow"] - baseline[recipient], (baseline[rival] - baseline[recipient]) / 2
    )
    # Outside-pool support is illustrated only as an additional transfer from Chow.
    chow_gain_to_tie = max(
        0, (shares["chow"] - shares[recipient]) / 2, shares[rival] - shares[recipient]
    )
    return {
        "feasible": True,
        "shares": shares,
        "rival_fraction": rival_fraction,
        "gain_pp": gain,
        "pool_share_pp": pool,
        "recipient_pool_fraction_before": baseline[recipient] / pool if pool else None,
        "recipient_pool_fraction_after": shares[recipient] / pool if pool else None,
        "recipient_margin_pp": shares[recipient] - max(shares["chow"], shares[rival]),
        "full_consolidation_margin_pp": pool - baseline["chow"],
        "rival_fraction_to_tie": (
            tie_gain / baseline[rival] if baseline[rival] else (0 if tie_gain == 0 else None)
        ),
        "rival_fraction_to_tie_pair": (
            max(0, (baseline[rival] - baseline[recipient]) / 2) / baseline[rival]
            if baseline[rival]
            else 0
        ),
        "tie_reachable": tie_gain <= baseline[rival] + 1e-9,
        "chow_transfer_to_tie_pp": (
            chow_gain_to_tie if chow_gain_to_tie <= shares["chow"] + 1e-9 else None
        ),
        "chow_transfer_to_tie_after_full_pp": max(0, (baseline["chow"] - pool) / 2),
    }


def build_consolidation_analysis(root: Path, baselines: list[dict]) -> dict:
    path = root / "docs/research/tory-consolidation-inputs.json"
    inputs = json.loads(path.read_text())
    readings = {row["id"]: row for row in inputs["readings"]}

    def selected(row, names=POOL_2023):
        return {name: row["reported_shares"][name] for name in names}

    comparisons = []
    for pair in inputs["comparisons"]:
        before, after = (readings[pair[key]] for key in ("before_id", "after_id"))
        comparisons.append(
            {
                **pair,
                **compare_pools(selected(before), selected(after)),
                "source_url": after["source_url"],
                "including_hunter": compare_pools(
                    selected(before, (*POOL_2023, "hunter")),
                    selected(after, (*POOL_2023, "hunter")),
                ),
            }
        )

    event = date(2023, 6, 21)

    def midpoint(row):
        return (
            (date.fromisoformat(row["fieldwork_start"]) - event).days
            + (date.fromisoformat(row["fieldwork_end"]) - event).days
        ) / 2

    trends = []
    for comparison in comparisons[:2]:
        post = readings[comparison["after_id"]]
        pre = [
            row
            for row in readings.values()
            if row["pollster"] == post["pollster"] and -14 <= midpoint(row) < 0
        ]
        slope, intercept = statistics.linear_regression(
            [midpoint(row) for row in pre],
            [summarize_pool(selected(row))["recipient_pool_fraction"] for row in pre],
        )
        projected = intercept + slope * midpoint(post)
        observed = comparison["after"]["recipient_pool_fraction"]
        trends.append(
            {
                "pollster": post["pollster"],
                "window_days": 14,
                "n_polls": len(pre),
                "input_reading_ids": [row["id"] for row in pre],
                "projected_pool_fraction": projected,
                "observed_pool_fraction": observed,
                "excess_pool_fraction": observed - projected,
                "gap_closed_above_trend": (observed - projected) / (1 - projected),
            }
        )

    outcome = inputs["official_result"]
    outcome_shares = {
        key: count / outcome["valid_candidate_votes"] * 100
        for key, count in outcome["votes"].items()
    }
    scenarios = [
        {
            "baseline_id": base["id"],
            "recipient": recipient,
            **calculate_consolidation(base["shares"], recipient, percent / 100),
        }
        for base in baselines
        for recipient in ("bradford", "alexander")
        for percent in range(101)
    ]
    return {
        "interpretation": (
            "Candidate-pool concentration, not measured voter ideology or individual transfers. "
            "Historical movements do not identify a Tory effect."
        ),
        "fraction_definition": (
            "Chosen net fraction of the rival challenger's baseline support transferred. "
            "Independent of the percentage-point and timing controls."
        ),
        "historical_pool": list(POOL_2023),
        "inputs": inputs,
        "input_path": str(path.relative_to(root)),
        "input_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "historical_comparisons": comparisons,
        "concentration_pretrends": trends,
        "historical_result": summarize_pool(outcome_shares),
        "scenarios": scenarios,
    }
