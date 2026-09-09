"""Alexander ballot-entry comparisons and explicitly assumed further-growth mixes.

Net changes in response categories are not individual transitions. The extension
holds a decided/leaning denominator fixed and allows the Other response to shrink.
It is separate from the endorsement scenarios that hold that residual fixed.
"""

import math
from collections.abc import Mapping
from decimal import Decimal

LABELS = {
    "chow": "Olivia Chow",
    "bradford": "Brad Bradford",
    "alexander": "Chris Alexander",
    "residual": "Someone else",
    "undecided": "Undecided",
}
DONORS = ("chow", "bradford", "residual")
PAIRS = (
    (
        "forum",
        "Forum: two ballots on July 29",
        "forum_20260729_mayor_primary",
        "forum_20260729_mayor_alexander",
    ),
    (
        "liaison",
        "Liaison: July 24–26 to August 4–5, decided/leaning",
        "liaison_20260724_26_mayor_decided_leaning",
        "liaison_20260804_05_mayor_decided_leaning",
    ),
    (
        "liaison_all",
        "Liaison: entry interval, all voters",
        "liaison_20260724_26_mayor_all",
        "liaison_20260804_05_mayor_all",
    ),
    (
        "liaison_later",
        "Liaison: August 4–5 to August 14–16, decided/leaning",
        "liaison_20260804_05_mayor_decided_leaning",
        "liaison_20260814_16_mayor_decided_leaning",
    ),
    (
        "liaison_later_all",
        "Liaison: later August interval, all voters",
        "liaison_20260804_05_mayor_all",
        "liaison_20260814_16_mayor_all",
    ),
)


def apply_entry_profile(
    baseline: Mapping[str, float], gain_pp: float, weights: Mapping[str, float]
) -> dict:
    """Apply one assumed positive growth mix, rejecting an exhausted source pool.

    Weights are an accounting allocation derived from aggregate entry differences,
    not measured switching probabilities. They are not reversed for Bradford.
    """
    if set(baseline) != {*DONORS, "alexander"} or set(weights) != set(DONORS):
        raise ValueError("Expected three named candidates, Other, and three donor weights.")
    if any(not math.isfinite(x) or x < 0 for x in (*baseline.values(), *weights.values())):
        raise ValueError("Shares and weights must be finite and nonnegative.")
    if not math.isclose(sum(baseline.values()), 100, abs_tol=1e-8, rel_tol=0):
        raise ValueError("Baseline must sum to 100.")
    if not math.isclose(sum(weights.values()), 1, abs_tol=1e-8, rel_tol=0):
        raise ValueError("Weights must sum to one.")
    if not math.isfinite(gain_pp) or gain_pp < 0:
        raise ValueError("Entry profiles describe nonnegative growth only.")
    limits = {key: baseline[key] / weight for key, weight in weights.items() if weight > 0}
    limiting = min(limits, key=limits.get)
    maximum = limits[limiting]
    available = gain_pp <= maximum + 1e-9
    shares = dict(baseline)
    shares["alexander"] += gain_pp
    losses = {key: gain_pp * weight for key, weight in weights.items()}
    for key, loss in losses.items():
        shares[key] -= loss
    return {
        "feasible": available,
        "reason": None if available else f"{LABELS[limiting]} has too little support for this mix.",
        "shares": shares if available else None,
        "assumed_losses_pp": losses,
        "max_gain_pp": maximum,
        "limiting_source": limiting,
        "realized_effect_pp": gain_pp,
    }


def _one(rows: list[dict], key: str, value: str) -> dict:
    matches = [row for row in rows if row[key] == value]
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one {key}={value}.")
    return matches[0]


def _reading(tables: dict, reading_id: str) -> dict:
    reading = _one(tables["poll_readings"], "poll_reading_id", reading_id)
    sample = _one(tables["poll_samples"], "poll_sample_id", reading["poll_sample_id"])
    source = _one(tables["source_documents"], "source_document_id", reading["source_document_id"])
    if reading["response_coverage"] != "complete":
        raise ValueError(f"Incomplete reading: {reading_id}")
    shares = {}
    for row in tables["poll_responses"]:
        if row["poll_reading_id"] != reading_id:
            continue
        kind = row["response_kind"]
        key = (
            "residual"
            if kind == "other"
            else "undecided"
            if kind == "undecided"
            else row["candidate_id"]
        )
        if key not in LABELS or key in shares:
            raise ValueError(f"Unexpected or duplicate response: {reading_id} / {key}")
        value = Decimal(row["share"]) * 100
        if not value.is_finite() or value < 0:
            raise ValueError(f"Invalid response: {reading_id} / {key}")
        shares[key] = value
    if not set(DONORS).issubset(shares):
        raise ValueError(f"Missing response categories: {reading_id}")
    total = sum(shares.values())
    tolerance = (
        len(shares) * Decimal("0.5") * Decimal(10) ** -int(reading["reported_share_precision"])
    )
    if total <= 0 or abs(total - 100) > tolerance:
        raise ValueError(f"Invalid rounded total: {reading_id}")
    return {
        "reading_id": reading_id,
        "sample_id": sample["poll_sample_id"],
        "fieldwork_start": sample["fieldwork_start"],
        "fieldwork_end": sample["fieldwork_end"],
        "publication_date": sample["publication_date"],
        "denominator": reading["denominator_text"],
        "unweighted_base": int(reading["unweighted_base"]) if reading["unweighted_base"] else None,
        "weighted_base": int(reading["weighted_base"]) if reading["weighted_base"] else None,
        "reported_base": int(reading["reported_base"]) if reading["reported_base"] else None,
        "reported_shares": {key: float(value) for key, value in shares.items()},
        "reported_total": float(total),
        "normalized_shares": {key: float(value * 100 / total) for key, value in shares.items()},
        "not_listed": [] if "alexander" in shares else ["alexander"],
        "source_url": source["publisher_url"],
        "source_sha256": source["sha256"],
        "source_locator": reading["source_locator"],
        "notes": reading["notes"],
    }


def build_entry_analysis(tables: dict, baselines: list, timings: list, effects: tuple) -> dict:
    """Retain published comparisons and build two conditional growth illustrations."""
    comparisons = []
    for identifier, label, before_id, after_id in PAIRS:
        before, after = (_reading(tables, key) for key in (before_id, after_id))
        comparisons.append(
            {
                "id": identifier,
                "label": label,
                "before": before,
                "after": after,
                "same_sample": before["sample_id"] == after["sample_id"],
                "reported_deltas": {
                    key: after["reported_shares"].get(key, 0)
                    - before["reported_shares"].get(key, 0)
                    for key in LABELS
                    if key in before["reported_shares"] or key in after["reported_shares"]
                },
            }
        )
    profiles = []
    for comparison in comparisons[:2]:
        before = comparison["before"]["normalized_shares"]
        after = comparison["after"]["normalized_shares"]
        if "alexander" in before or after["alexander"] <= 0:
            raise ValueError("An entry comparison must add Alexander as a new response option.")
        weights = {key: (before[key] - after[key]) / after["alexander"] for key in DONORS}
        # Validates that this particular pair admits an allocation without other switches.
        apply_entry_profile({**before, "alexander": 0}, 0, weights)
        label = (
            "Forum ballot comparison"
            if comparison["id"] == "forum"
            else "Liaison before/after entry"
        )
        profiles.append({"id": comparison["id"], "label": label, "weights": weights})
    extensions = []
    for baseline in baselines:
        for timing in timings:
            for profile in profiles:
                for effect in effects:
                    gain = effect * timing["retained_fraction"]
                    result = apply_entry_profile(
                        baseline["shares"], max(0, gain), profile["weights"]
                    )
                    if gain < 0:
                        result.update(
                            {
                                "feasible": False,
                                "shares": None,
                                "assumed_losses_pp": None,
                                "realized_effect_pp": gain,
                                "reason": "Entry evidence does not supply a reverse-flow model for losses.",
                            }
                        )
                    extensions.append(
                        {
                            "baseline_id": baseline["id"],
                            "timing_id": timing["id"],
                            "profile_id": profile["id"],
                            "effect_pp": effect,
                            **result,
                        }
                    )
    return {
        "interpretation": "Net response-category comparisons; no individual switching probabilities.",
        "profile_assumption": (
            "Only switches into Alexander, after separately scaling rounded readings to 100. "
            "Applying these entry allocations to further growth is an explicit assumption."
        ),
        "comparisons": comparisons,
        "profiles": profiles,
        "extensions": extensions,
    }
