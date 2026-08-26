"""Live mayoral forecast feed for the frontend package (INT).

Turns the qualified Mayoral Endpoint Bridge into the published per-candidate
quantities. The pure, outcome-free core (``forecast_quantities``) reduces the
model's share draws to the three public quantities and their Monte-Carlo error
intervals; the production layer builds the live target from the current-cycle
poll bundle, runs the Mandatory Sensitivity Variant suite, and composes the M3
publication gates into per-candidate availability.

Field-consistency (ADR 0046) governs which polls feed the forecast: exactly the
same final-field samples the evidence tier counts (those measuring the certified
viable field), so the forecast and its published tier agree. Nothing publishes
until the field is certified — until then the tier is M1 and every quantity is
Forecast Unavailable, correctly.
"""

from __future__ import annotations

import collections
import math
from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

from backend.model.historical_mayoral import load_historical_mayoral_corpus
from backend.model.historical_mayoral_evaluation import (
    build_historical_mayoral_evaluation_cycles,
)
from backend.model.mayoral_candidate_ids import load_canonical_mayoral_candidate_ids
from backend.model.mayoral_endpoint import (
    DRAW_COUNT,
    MAYORAL_ENDPOINT_ANALYSIS_TIME_LOCAL,
    MAYORAL_ENDPOINT_EVALUATION_LEAD_TIMES,
    MayoralEndpointDataError,
    MayoralEndpointEvidence,
    MayoralEndpointPredictor,
)
from backend.model.mayoral_evaluation import (
    FullBallotShareDraws,
    HeldOutCycle,
    LeadTimeSnapshot,
    TrainingCycle,
)
from backend.model.mayoral_evidence_tier import (
    MayoralEvidenceTier,
    MayoralEvidenceTierResult,
    MayoralPollSampleEvidence,
    classify_mayoral_evidence_tier,
)
from backend.model.mayoral_incumbency import load_mayoral_incumbency_population
from backend.model.mayoral_incumbency_endpoint import (
    IncumbencyEndpointError,
    IncumbencyInformedPredictor,
)
from backend.model.mayoral_publication import (
    compose_mayoral_quantity_publication,
)
from backend.model.mayoral_publication_gates import (
    CHALLENGER_WIN,
    CLOSE_RESULT,
    INCUMBENT_DEFEAT,
)
from backend.model.poll_sources import load_poll_source_bundle
from backend.model.publication import (
    ErrorInterval,
    SensitivityVariant,
    unavailable_variant,
)

MAYORAL_FORECAST_FEED_SCHEMA_VERSION = 2
_TORONTO = ZoneInfo("America/Toronto")
_CLOSE_THRESHOLD = 0.05
# Tail-mass sensitivity: halve and double the fitted candidate-tail mass (ADR 0018).
_TAIL_MULTIPLIER_LOW = 0.5
_TAIL_MULTIPLIER_HIGH = 2.0
# Leave-one-pollster-out is Not Applicable below this many pollsters (ADR 0048).
_MIN_POLLSTERS_FOR_LEAVE_ONE_OUT = 3
# Two-sided 95% normal quantile, for the Monte-Carlo error interval (ADR 0018).
_Z_95 = 1.959963984540054


# --- pure quantity core (outcome-free) -------------------------------------


@dataclass(frozen=True, slots=True)
class QuantityEstimate:
    """A probability point estimate plus its two-sided 95% MC error interval."""

    probability: float
    interval_lower: float
    interval_upper: float


def _wilson_interval(p: float, n: int) -> tuple[float, float]:
    """Two-sided 95% Wilson score interval for a proportion p from n draws.

    Wilson stays inside [0, 1] and is well-behaved near 0 and 1, where the Band
    Stability Gate is most sensitive; the point estimate always lies within it.
    """
    if n <= 0:
        raise ValueError("draw count must be positive")
    z2 = _Z_95 * _Z_95
    denom = 1.0 + z2 / n
    center = (p + z2 / (2.0 * n)) / denom
    half = (_Z_95 * math.sqrt(p * (1.0 - p) / n + z2 / (4.0 * n * n))) / denom
    return max(0.0, center - half), min(1.0, center + half)


def _estimate(p: float, n: int) -> QuantityEstimate:
    lower, upper = _wilson_interval(p, n)
    return QuantityEstimate(probability=p, interval_lower=lower, interval_upper=upper)


_MARGIN_GRID_SIZE = 120


@dataclass(frozen=True, slots=True)
class MarginDistribution:
    """Smoothed density of the winning margin (winner share minus runner-up
    share) across the share draws. `x` is a grid in share units on [0, x_max];
    `density` is a reflected-boundary Gaussian KDE evaluated there. It integrates
    to ~1 over the grid and is the shape behind the homepage close-result panel."""

    x: tuple[float, ...]
    density: tuple[float, ...]

    def to_feed(self, close_threshold: float) -> dict:
        return {
            "unit": "share_gap",  # winner minus runner-up, a fraction in [0, 1]
            "x": list(self.x),
            "density": list(self.density),
            "close_threshold": close_threshold,
        }


def _margin_distribution(
    margins: np.ndarray, *, grid_size: int = _MARGIN_GRID_SIZE
) -> MarginDistribution:
    """Reflected-boundary Gaussian KDE of the winning margins.

    The margin is a top-two gap, bounded below at 0, so a naive KDE would leak
    probability mass to negative values. We reflect the sample across 0 (fold in
    the mirror points -d) and evaluate on [0, x_max]; the density then keeps its
    support on [0, ∞) and stays ~normalized on the grid.
    """
    data = np.asarray(margins, dtype=float)
    n = data.size
    # Silverman's rule of thumb, robustified with the IQR and floored so a
    # near-constant sample still yields a finite, smooth curve rather than a spike.
    std = float(np.std(data))
    q75, q25 = (float(v) for v in np.percentile(data, [75, 25]))
    spread = min(std, (q75 - q25) / 1.349) if std > 0 else 0.0
    if spread <= 0:
        spread = std if std > 0 else 1e-3
    bandwidth = max(0.9 * spread * n ** (-1 / 5), 1e-3)

    x_max = max(0.5, float(data.max()) * 1.05)
    xs = np.linspace(0.0, x_max, grid_size)
    diffs = (xs[:, None] - data[None, :]) / bandwidth
    reflected = (xs[:, None] + data[None, :]) / bandwidth
    kernel = np.exp(-0.5 * diffs**2) + np.exp(-0.5 * reflected**2)
    density = kernel.sum(axis=1) / (n * bandwidth * math.sqrt(2.0 * math.pi))
    return MarginDistribution(
        x=tuple(float(v) for v in xs),
        density=tuple(float(v) for v in density),
    )


@dataclass(frozen=True, slots=True)
class MayoralForecastQuantities:
    """Every public quantity for one fitted set of share draws."""

    candidate_win: dict[str, QuantityEstimate]
    close_result: QuantityEstimate
    incumbent_defeat: QuantityEstimate | None  # None in an open race
    margin_distribution: MarginDistribution


def forecast_quantities(
    draws: FullBallotShareDraws,
    *,
    incumbent_candidate_id: str | None,
    close_threshold: float = _CLOSE_THRESHOLD,
) -> MayoralForecastQuantities:
    """Reduce full-ballot share draws to the published quantities + 95% intervals."""
    candidate_ids = draws.candidate_ids
    rows = draws.draws  # (n_draws, n_candidates) read-only ndarray
    draw_count = rows.shape[0]
    # Winner weight per candidate, splitting an exact top-share tie equally.
    winners_mask = rows == rows.max(axis=1, keepdims=True)
    ties = winners_mask.sum(axis=1, keepdims=True)
    win_weight_arr = (winners_mask / (draw_count * ties)).sum(axis=0)
    win_weight = {
        candidate_id: float(win_weight_arr[index])
        for index, candidate_id in enumerate(candidate_ids)
    }
    ordered_rows = np.sort(rows, axis=1)
    margins = ordered_rows[:, -1] - ordered_rows[:, -2]
    close_draws = int(np.count_nonzero(margins <= close_threshold))

    candidate_win = {
        candidate_id: _estimate(win_weight[candidate_id], draw_count)
        for candidate_id in candidate_ids
    }
    close_result = _estimate(close_draws / draw_count, draw_count)
    incumbent_defeat: QuantityEstimate | None = None
    if incumbent_candidate_id is not None:
        if incumbent_candidate_id not in win_weight:
            raise ValueError("incumbent_candidate_id is not on the ballot")
        incumbent_defeat = _estimate(1.0 - win_weight[incumbent_candidate_id], draw_count)
    return MayoralForecastQuantities(
        candidate_win=candidate_win,
        close_result=close_result,
        incumbent_defeat=incumbent_defeat,
        margin_distribution=_margin_distribution(margins),
    )


# --- live target + evidence from the current-cycle bundle -------------------


# The registered field carries names; the poll bundle keys the modelled
def _measured_named_candidates(bundle: object) -> dict[str, frozenset[str]]:
    read_sample = {r.poll_reading_id: r.poll_sample_id for r in bundle.poll_readings}
    measured: dict[str, set[str]] = collections.defaultdict(set)
    for response in bundle.poll_responses:
        if response.response_kind == "candidate" and response.candidate_id:
            measured[read_sample[response.poll_reading_id]].add(response.candidate_id)
    return {sample_id: frozenset(names) for sample_id, names in measured.items()}


@dataclass(frozen=True, slots=True)
class LiveForecastInputs:
    training: tuple[TrainingCycle, ...]
    target: HeldOutCycle
    tier_result: MayoralEvidenceTierResult
    incumbent_candidate_id: str | None
    viable_field: tuple[str, ...]
    final_field_sample_ids: tuple[str, ...]
    final_field_pollsters: tuple[str, ...]


def load_live_forecast_inputs(
    root: str | Path, live_cycle: dict, *, polls_dir: str | Path
) -> LiveForecastInputs:
    """Build the training corpus, the live target, and the evidence tier from the
    current-cycle bundle, restricted to the field-consistency selection (ADR 0046)."""
    root = Path(root)
    cycle_id = live_cycle["election_cycle_id"]
    viable = frozenset(live_cycle["viable_field"])
    incumbent = live_cycle["incumbent_candidate_id"]
    final_field = viable if bool(live_cycle["field_certified"]) else None

    bundle = load_poll_source_bundle(str(polls_dir), require_audited_sources=False)
    measured = _measured_named_candidates(bundle)
    citywide = [
        sample
        for sample in bundle.poll_samples
        if sample.election_cycle_id == cycle_id
        and sample.geography_type == "citywide"
        and sample.extraction_status == "extracted"
    ]
    tier_samples = tuple(
        MayoralPollSampleEvidence(
            sample_id=sample.poll_sample_id,
            pollster=sample.pollster,
            measured_candidates=measured.get(sample.poll_sample_id, frozenset()),
        )
        for sample in citywide
    )
    tier_result = classify_mayoral_evidence_tier(tier_samples, final_field=final_field)

    # Field-consistency evidence: samples measuring exactly the viable field.
    final_field_samples = [
        sample for sample in citywide if measured.get(sample.poll_sample_id) == viable
    ]
    sample_ids = {sample.poll_sample_id for sample in final_field_samples}
    readings = [r for r in bundle.poll_readings if r.poll_sample_id in sample_ids]
    reading_ids = {r.poll_reading_id for r in readings}
    responses = [r for r in bundle.poll_responses if r.poll_reading_id in reading_ids]
    if not final_field_samples:
        raise ValueError("no final-field samples to forecast from")
    # The endpoint (and the incumbency parse) use the historical underscore cycle
    # convention (toronto_YYYY); the current-cycle bundle keys samples with a
    # hyphen. Relabel the samples so the endpoint's sample<->evidence cycle check
    # and IncumbencyInformedPredictor's city/year parse both succeed.
    endpoint_cycle = cycle_id.replace("-", "_")
    evidence = MayoralEndpointEvidence(
        election_cycle_id=endpoint_cycle,
        final_ballot_evidence_available_at=min(
            sample.evidence_available_at for sample in final_field_samples
        ),
        poll_samples=tuple(
            replace(sample, election_cycle_id=endpoint_cycle) for sample in final_field_samples
        ),
        poll_readings=tuple(readings),
        poll_responses=tuple(responses),
    )
    snapshot = LeadTimeSnapshot(
        days_before_election=0,
        analysis_cutoff=datetime.fromisoformat(f"{live_cycle['election_date']}T12:00:00").replace(
            tzinfo=_TORONTO
        ),
        evidence_revision=f"live-{cycle_id}",
        evidence=evidence,
    )
    target = HeldOutCycle(
        election_cycle_id=endpoint_cycle,
        election_type="general",
        snapshot=snapshot,
        candidate_ids=load_canonical_mayoral_candidate_ids(
            root / "data/upstream/results/mayoral_candidates.json"
        ),
        incumbent_candidate_id=incumbent,
    )

    corpus = load_historical_mayoral_corpus(root)
    cycles = build_historical_mayoral_evaluation_cycles(
        corpus,
        lead_times=MAYORAL_ENDPOINT_EVALUATION_LEAD_TIMES,
        analysis_time_local=MAYORAL_ENDPOINT_ANALYSIS_TIME_LOCAL,
    )
    training = tuple(
        TrainingCycle(
            election_cycle_id=cycle.election_cycle_id,
            election_type=cycle.election_type,
            snapshot=min(cycle.snapshots, key=lambda s: s.days_before_election),
            history=cycle.snapshots,
            outcome=cycle.outcome,
        )
        for cycle in cycles
    )
    return LiveForecastInputs(
        training=training,
        target=target,
        tier_result=tier_result,
        incumbent_candidate_id=incumbent,
        viable_field=tuple(sorted(viable)),
        final_field_sample_ids=tuple(sorted(sample_ids)),
        final_field_pollsters=tuple(sorted({sample.pollster for sample in final_field_samples})),
    )


# --- Mandatory Sensitivity Variant suite (ADR 0018) -------------------------


def _variant_predictors(inputs: LiveForecastInputs, root: Path) -> list[tuple]:
    """The frozen Mandatory Sensitivity Variants as (label, fit_predict) pairs:
    the qualified bridge and its comparator baseline, low/base/high candidate-tail
    assumptions, leave-one-sample-out, leave-one-pollster-out, and the incumbency
    variant. A variant that cannot run fails the Band Stability Gate (ADR 0018)."""
    bridge = "firm-balanced-bridge"
    variants: list[tuple] = [
        ("bridge-base", MayoralEndpointPredictor(bridge, draw_count=DRAW_COUNT)),
        (
            "comparator-baseline",
            MayoralEndpointPredictor("latest-sample-comparator", draw_count=DRAW_COUNT),
        ),
        (
            "tail-low",
            MayoralEndpointPredictor(
                bridge,
                draw_count=DRAW_COUNT,
                tail_mass_multiplier=_TAIL_MULTIPLIER_LOW,
            ),
        ),
        (
            "tail-high",
            MayoralEndpointPredictor(
                bridge,
                draw_count=DRAW_COUNT,
                tail_mass_multiplier=_TAIL_MULTIPLIER_HIGH,
            ),
        ),
    ]
    for sample_id in inputs.final_field_sample_ids:
        variants.append(
            (
                f"leave-out-sample:{sample_id}",
                MayoralEndpointPredictor(
                    bridge,
                    draw_count=DRAW_COUNT,
                    excluded_poll_sample_ids=frozenset({sample_id}),
                ),
            )
        )
    # Leave-one-pollster-out is Not Applicable below three pollsters (ADR 0048):
    # dropping one would leave too little to refit, so the perturbation is
    # unassessable and the variant is omitted rather than failing the gate.
    if len(inputs.final_field_pollsters) >= _MIN_POLLSTERS_FOR_LEAVE_ONE_OUT:
        for pollster in inputs.final_field_pollsters:
            variants.append(
                (
                    f"leave-out-pollster:{pollster}",
                    MayoralEndpointPredictor(
                        bridge,
                        draw_count=DRAW_COUNT,
                        excluded_pollsters=frozenset({pollster}),
                    ),
                )
            )
    variants.append(
        (
            "incumbency-prior",
            IncumbencyInformedPredictor(
                population=load_mayoral_incumbency_population(root),
                draw_count=DRAW_COUNT,
            ),
        )
    )
    return variants


def _run_variants(
    inputs: LiveForecastInputs, root: Path
) -> dict[str, MayoralForecastQuantities | None]:
    """Run each variant; a variant that cannot compute (too little evidence after
    an exclusion) is recorded as None and fails the Band Stability Gate (ADR 0018)."""
    per_variant: dict[str, MayoralForecastQuantities | None] = {}
    for label, predictor in _variant_predictors(inputs, root):
        try:
            prediction = predictor(inputs.training, inputs.target)
        except MayoralEndpointDataError, IncumbencyEndpointError:
            per_variant[label] = None
            continue
        per_variant[label] = forecast_quantities(
            prediction.full_ballot_share_draws,
            incumbent_candidate_id=inputs.incumbent_candidate_id,
        )
    return per_variant


def _d(value: float) -> Decimal:
    return Decimal(str(value))


def _variant_row(label: str, estimate: QuantityEstimate) -> SensitivityVariant:
    return SensitivityVariant(
        label=label,
        probability=_d(estimate.probability),
        error_interval=ErrorInterval(
            lower=_d(estimate.interval_lower), upper=_d(estimate.interval_upper)
        ),
    )


# --- feed assembly ----------------------------------------------------------


def build_mayoral_forecast_feed(
    root: str | Path, live_cycle: dict, *, polls_dir: str | Path
) -> dict:
    """Assemble the per-candidate forecast feed: each quantity's evidence tier,
    availability, published band, and (when Available) point estimate."""
    root = Path(root)
    inputs = load_live_forecast_inputs(root, live_cycle, polls_dir=polls_dir)
    tier = inputs.tier_result
    has_incumbent = inputs.incumbent_candidate_id is not None
    # The variant suite is only needed when the tier could unlock a quantity;
    # below M2 every predictive quantity is tier-gated Unavailable anyway.
    per_variant = (
        _run_variants(inputs, root)
        if tier.tier.rank >= MayoralEvidenceTier.M2_POST_FINAL.rank
        else {}
    )

    def quantity_card(
        quantity: str,
        estimate_of,
        *,
        candidate_id: str | None = None,
    ) -> dict:
        variants = [
            _variant_row(label, estimate_of(quantities))
            if quantities is not None
            else unavailable_variant(label)
            for label, quantities in per_variant.items()
        ]
        publication = compose_mayoral_quantity_publication(
            quantity,
            tier,
            race_has_incumbent=has_incumbent,
            candidate_id=candidate_id,
            variants=variants or None,
        )
        point = per_variant["bridge-base"] if publication.is_published else None
        estimate = estimate_of(point) if point is not None else None
        return {
            "quantity": quantity,
            "candidate_id": candidate_id,
            "tier": publication.tier.label,
            "availability": publication.availability.value,
            "band": publication.band.label if publication.band else None,
            "frequency_statement": (
                publication.band.frequency_statement if publication.band else None
            ),
            "probability": estimate.probability if estimate else None,
            "reason": publication.reason,
        }

    candidate_win = {
        candidate_id: quantity_card(
            CHALLENGER_WIN,
            lambda q, cid=candidate_id: q.candidate_win[cid],
            candidate_id=candidate_id,
        )
        for candidate_id in inputs.viable_field
    }
    close_result = quantity_card(CLOSE_RESULT, lambda q: q.close_result)
    incumbent_defeat = quantity_card(INCUMBENT_DEFEAT, lambda q: q.incumbent_defeat)

    # The margin distribution rides on the close-result gate: we only surface its
    # shape when the close-result summary itself publishes (else the raw shape
    # would leak an estimate the Band Stability Gate judged too unstable to show).
    bridge_base = per_variant.get("bridge-base")
    margin_distribution = (
        bridge_base.margin_distribution.to_feed(_CLOSE_THRESHOLD)
        if close_result["availability"] == "Forecast Available" and bridge_base is not None
        else None
    )

    return {
        "schema_version": MAYORAL_FORECAST_FEED_SCHEMA_VERSION,
        "election_cycle_id": inputs.target.election_cycle_id,
        "evidence_tier": tier.tier.label,
        "final_field_samples": list(inputs.final_field_sample_ids),
        "incumbent_candidate_id": inputs.incumbent_candidate_id,
        "candidate_win": candidate_win,
        "close_result": close_result,
        "incumbent_defeat": incumbent_defeat,
        "margin_distribution": margin_distribution,
    }
