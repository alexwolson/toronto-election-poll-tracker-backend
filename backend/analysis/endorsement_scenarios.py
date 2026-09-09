"""Conditional vote transfers; no causal endorsement estimate or forecast fit.

All numerical shares and changes use percentage points on a 100-point total.
The residual stays fixed and is never treated as a candidate.
"""

import csv
import hashlib
import math
from collections.abc import Mapping
from datetime import date
from decimal import Decimal
from pathlib import Path

from backend.analysis.alexander_entry import build_entry_analysis
from backend.analysis.consolidation import build_consolidation_analysis

NAMES = {"chow": "Olivia Chow", "bradford": "Brad Bradford", "alexander": "Chris Alexander"}
ELECTION_DATE = date(2026, 10, 26)
READING_IDS = (
    "pallas_20260819_21_mayor_decided_leaning",
    "liaison_20260814_16_mayor_decided_leaning",
)
EFFECTS = (-3, 0, 3, 6, 9)
FLOWS = (
    {"id": "chow", "label": "All from Chow", "chow_fraction": 1},
    {"id": "mixed", "label": "Half Chow, half other challenger", "chow_fraction": 0.5},
    {"id": "challenger", "label": "All from other challenger", "chow_fraction": 0},
)


def calculate_scenario(
    baseline: Mapping[str, float],
    recipient: str,
    effect_pp: float,
    *,
    chow_fraction: float,
    retained_fraction: float = 1,
) -> dict:
    """Transfer points; negative effects reverse the same explicitly weighted flows.

    Retention is a user assumption about the net effect realized at election day,
    inclusive of persistence and any inability to switch already-cast ballots.
    It is not inferred from event timing or from the historical polls.
    """
    if set(baseline) != {*NAMES, "residual"}:
        raise ValueError("Baseline must contain the three named candidates and residual.")
    if any(not math.isfinite(x) or x < 0 for x in baseline.values()):
        raise ValueError("Baseline shares must be finite and nonnegative.")
    if not math.isclose(sum(baseline.values()), 100, rel_tol=0, abs_tol=1e-8):
        raise ValueError("Baseline shares must sum to 100.")
    if recipient not in ("bradford", "alexander"):
        raise ValueError("Recipient must be Bradford or Alexander.")
    if not math.isfinite(effect_pp):
        raise ValueError("Effect must be finite.")
    if not 0 <= chow_fraction <= 1 or not 0 <= retained_fraction <= 1:
        raise ValueError("Flow and retention fractions must be between 0 and 1.")
    realized_effect = effect_pp * retained_fraction
    other = "alexander" if recipient == "bradford" else "bradford"
    weights = {"chow": chow_fraction, other: 1 - chow_fraction}
    max_gain = min(baseline[key] / weight for key, weight in weights.items() if weight)
    tie_gain = max(
        0.0,
        *((baseline[key] - baseline[recipient]) / (1 + weight) for key, weight in weights.items()),
    )
    thresholds = {
        "max_gain_pp": max_gain,
        "tie_gain_pp": tie_gain,
        "tie_reachable": tie_gain <= max_gain + 1e-9,
        "realized_effect_pp": realized_effect,
    }
    shares = dict(baseline)
    shares[recipient] += realized_effect
    shares["chow"] -= realized_effect * chow_fraction
    shares[other] -= realized_effect * (1 - chow_fraction)
    exhausted = next((key for key in NAMES if shares[key] < -1e-9), None)
    if exhausted:
        return {
            "feasible": False,
            "reason": f"{NAMES[exhausted]} has too little support for this transfer.",
            "shares": None,
            "recipient_margin_pp": None,
            "leaders": [],
            **thresholds,
        }
    highest = max(shares[candidate] for candidate in NAMES)
    return {
        "feasible": True,
        "reason": None,
        **thresholds,
        "shares": shares,
        "recipient_margin_pp": shares[recipient]
        - max(shares[candidate] for candidate in NAMES if candidate != recipient),
        "leaders": [
            candidate
            for candidate in NAMES
            if math.isclose(shares[candidate], highest, rel_tol=0, abs_tol=1e-9)
        ],
    }


def build_analysis(root: Path) -> dict:
    """Read fixed source readings and return a reproducible, assumption-labeled grid.

    This is not a latest-poll selector. Source values and file fingerprints remain
    inspectable alongside the separately normalized arithmetic baseline.
    """
    tables = {}
    fingerprints = {}
    for name in ("poll_samples", "poll_readings", "poll_responses", "source_documents"):
        path = root / "data/raw/polls" / f"{name}.csv"
        fingerprints[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
        with path.open(newline="") as file:
            tables[name] = list(csv.DictReader(file))
    baselines = []
    for reading_id in READING_IDS:
        reading = _unique(tables["poll_readings"], "poll_reading_id", reading_id)
        sample = _unique(tables["poll_samples"], "poll_sample_id", reading["poll_sample_id"])
        source = _unique(
            tables["source_documents"], "source_document_id", reading["source_document_id"]
        )
        if reading["response_coverage"] != "complete" or reading["denominator_type"] not in (
            "decided_respondents",
            "custom",
        ):
            raise ValueError(f"Expected a complete decided/leaning reading: {reading_id}")
        values = {}
        for row in tables["poll_responses"]:
            if row["poll_reading_id"] != reading_id:
                continue
            if row["response_kind"] == "candidate" and row["candidate_id"] in NAMES:
                key = row["candidate_id"]
            elif row["response_kind"] == "other":
                key = "residual"
            else:
                raise ValueError(f"Unexpected response in {reading_id}: {row['response_label']}")
            if key in values:
                raise ValueError(f"Duplicate response {key} in {reading_id}")
            value = Decimal(row["share"]) * 100
            if not value.is_finite() or value < 0:
                raise ValueError(f"Invalid response value in {reading_id}")
            values[key] = value
        if set(values) != {*NAMES, "residual"}:
            raise ValueError(f"Incomplete field in {reading_id}")
        total = sum(values.values())
        rounding_tolerance = (
            len(values)
            * Decimal("0.5")
            * (Decimal(10) ** -int(reading["reported_share_precision"]))
        )
        if total <= 0 or abs(total - 100) > rounding_tolerance:
            raise ValueError(f"Total exceeds declared rounding precision in {reading_id}")
        baselines.append(
            {
                "id": sample["poll_sample_id"],
                "label": sample["pollster"],
                "reading_id": reading_id,
                "fieldwork_start": sample["fieldwork_start"],
                "fieldwork_end": sample["fieldwork_end"],
                "publication_date": sample["publication_date"],
                "sample_size": int(sample["recruited_sample_size"]),
                "denominator": reading["denominator_text"],
                "source_url": source["publisher_url"],
                "source_locator": reading["source_locator"],
                "source_document_id": source["source_document_id"],
                "source_sha256": source["sha256"],
                "reported_shares": {key: float(value) for key, value in values.items()},
                "reported_total": float(total),
                "shares": {key: float(value * 100 / total) for key, value in values.items()},
            }
        )
    timings = []
    for event in (date(2026, 10, 21), date(2026, 9, 9)):
        if any(event < date.fromisoformat(base["publication_date"]) for base in baselines):
            raise ValueError("Scenario event must follow every baseline's publication.")
        for retained in (1, 0.5, 0):
            timings.append(
                {
                    "id": f"{event.isoformat()}-{retained}",
                    "event_date": event.isoformat(),
                    "days_before_election": (ELECTION_DATE - event).days,
                    "retained_fraction": retained,
                    "label": f"{event:%b %d} · {retained:.0%} net effect retained",
                }
            )
    scenarios = []
    for base in baselines:
        for timing in timings:
            for flow in FLOWS:
                for effect in EFFECTS:
                    for recipient in ("bradford", "alexander"):
                        result = calculate_scenario(
                            base["shares"],
                            recipient,
                            effect,
                            chow_fraction=flow["chow_fraction"],
                            retained_fraction=timing["retained_fraction"],
                        )
                        scenarios.append(
                            {
                                "baseline_id": base["id"],
                                "timing_id": timing["id"],
                                "flow_id": flow["id"],
                                "recipient": recipient,
                                "effect_pp": effect,
                                **result,
                            }
                        )
    return {
        "schema_version": 1,
        "analysis_date": "2026-09-09",
        "election_date": ELECTION_DATE.isoformat(),
        "interpretation": "Conditional arithmetic using dated polls; not a causal estimate or forecast.",
        "effect_definition": "Potential net share shift, multiplied by the assumed retained fraction.",
        "timing_note": "Dates do not estimate retention. Retention includes any inability to switch already-cast ballots.",
        "rounding_note": "Published values are preserved; each reading is scaled to 100 only for transfer arithmetic.",
        "input_sha256": fingerprints,
        "candidate_names": NAMES,
        "baselines": baselines,
        "timings": timings,
        "flows": FLOWS,
        "effects_pp": EFFECTS,
        "scenarios": scenarios,
        "alexander_entry": build_entry_analysis(tables, baselines, timings, EFFECTS),
        "consolidation": build_consolidation_analysis(root, baselines),
    }


def _unique(rows: list[dict], key: str, value: str) -> dict:
    matched = [row for row in rows if row[key] == value]
    if len(matched) != 1:
        raise ValueError(f"Expected exactly one {key}={value}; found {len(matched)}")
    return matched[0]
