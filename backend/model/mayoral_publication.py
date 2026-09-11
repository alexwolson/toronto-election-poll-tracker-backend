"""Compose a public Mayoral quantity's publication decision (M3 gate logic).

This orchestrates the frozen registry (tier floor + historical unlock, ADR 0033
/ 0005), operational-integrity fail-closed (ADR 0032), and the shared Band
Stability Gate (ADR 0018) into one per-quantity verdict. Each quantity is gated
independently (ADR 0003), and its evidence tier is always reported alongside the
verdict, never folded into it (ADR 0033).

The orchestrator consumes already-computed Mandatory Sensitivity Variants; the
production of those variants from the live endpoint (running each seam and
reducing draws to a quantity probability + 95% error interval) is model-to-gate
wiring and belongs to snapshot integration (INT), not to this gate layer.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from backend.model.mayoral_evidence_tier import (
    MayoralEvidenceTier,
    MayoralEvidenceTierResult,
)
from backend.model.mayoral_publication_gates import (
    QuantityGateStatus,
    mayoral_quantity_gate_status,
)
from backend.model.publication import (
    PROBABILITY_BAND_GRID_FIVE,
    ProbabilityBand,
    SensitivityVariant,
    band_for,
    evaluate_band_stability,
)


class Availability(Enum):
    """The public availability state of a quantity (ADR 0003, 0033)."""

    AVAILABLE = "Forecast Available"
    UNAVAILABLE = "Forecast Unavailable"
    NOT_APPLICABLE = "Not Applicable"


@dataclass(frozen=True, slots=True)
class MayoralQuantityPublication:
    """A quantity's availability, its published band (if any), and its tier."""

    quantity: str
    candidate_id: str | None
    tier: MayoralEvidenceTier
    availability: Availability
    band: ProbabilityBand | None
    reason: str
    sensitivity_range: tuple[Decimal, Decimal] | None = None

    @property
    def is_published(self) -> bool:
        return self.availability is Availability.AVAILABLE


def compose_mayoral_quantity_publication(
    quantity: str,
    tier_result: MayoralEvidenceTierResult,
    *,
    race_has_incumbent: bool,
    candidate_id: str | None = None,
    variants: Iterable[SensitivityVariant] | None = None,
    central_variant_label: str | None = None,
) -> MayoralQuantityPublication:
    """Resolve one public mayoral quantity to Available / Unavailable / N/A."""

    tier = tier_result.tier
    status = mayoral_quantity_gate_status(
        quantity,
        tier_result,
        race_has_incumbent=race_has_incumbent,
        candidate_id=candidate_id,
    )

    def result(
        availability: Availability,
        band: ProbabilityBand | None,
        reason: str,
    ) -> MayoralQuantityPublication:
        return MayoralQuantityPublication(
            quantity=quantity,
            candidate_id=candidate_id,
            tier=tier,
            availability=availability,
            band=band,
            reason=reason,
        )

    if status is QuantityGateStatus.NOT_APPLICABLE:
        return result(Availability.NOT_APPLICABLE, None, "not applicable in this race")
    if status is QuantityGateStatus.HISTORY_BLOCKED:
        return result(
            Availability.UNAVAILABLE,
            None,
            "required tier has not appeared in three Held-Out Election Cycles",
        )
    if status is QuantityGateStatus.TIER_TOO_LOW:
        return result(
            Availability.UNAVAILABLE,
            None,
            f"current-cycle polling has not reached the required tier ({tier.label})",
        )

    # UNLOCKED: fail closed on missing variants (ADR 0032), then the stability gate.
    variant_tuple = tuple(variants) if variants is not None else ()
    if not variant_tuple:
        return result(
            Availability.UNAVAILABLE,
            None,
            "no sensitivity variants were computed",
        )

    if central_variant_label is not None:
        # ADR 0053: show central rounding and sensitivity separately. Tier and
        # integrity checks remain; agreement on a rounding bin is not required.
        labels = [v.label for v in variant_tuple]
        if len(set(labels)) != len(labels):
            return result(Availability.UNAVAILABLE, None, "duplicate sensitivity variant labels")
        failed = [v.label for v in variant_tuple if not v.can_run()]
        if failed:
            return result(Availability.UNAVAILABLE, None, f"unrunnable variants: {failed}")
        central = next((v for v in variant_tuple if v.label == central_variant_label), None)
        if central is None:
            return result(Availability.UNAVAILABLE, None, "central sensitivity variant is missing")
        return MayoralQuantityPublication(
            quantity,
            candidate_id,
            tier,
            Availability.AVAILABLE,
            (
                band_for(central.probability)
                if central.probability < Decimal(".05") or central.probability >= Decimal(".95")
                else band_for(central.probability, PROBABILITY_BAND_GRID_FIVE)
            ),
            "",
            (
                min(v.error_interval.lower for v in variant_tuple),
                max(v.error_interval.upper for v in variant_tuple),
            ),
        )

    decision = evaluate_band_stability(variant_tuple)
    if decision.is_published:
        return result(Availability.AVAILABLE, decision.band, "")
    return result(Availability.UNAVAILABLE, None, decision.reason)
