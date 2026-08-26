# Replicate Matt Elliott's CDI as a faithful rank-sum, not a re-derived model

## Context

Matt Elliott's Council Defeatability Index is documented only qualitatively in the
poll-tracker's `toronto-2026-model-spec.md` ("three factors combined into a single
score"); no formula exists as code or prose anywhere. The actual arithmetic is
embedded in his own City Hall Watcher export (`data-qT4Kx.csv`) and was
reverse-engineered and verified on every row: each of three components — prior-win
**vote share**, prior-win **elector share** (votes ÷ eligible electors), and a
**new-voter margin** (electors added since the win, minus the winning margin) — is
ranked across the pool (rank 1 = safest), and the score is the **sum of the three
ranks**.

## Decision

This project reproduces that rank-sum exactly for each historical election
(2003–2022), because the goal is a *faithful backtest* of Matt's real index, not a
new or "improved" model. Two deliberate deviations, both to fit the historical
data honestly:

1. **Growth = new-voter margin using ground-truth electorate deltas.** Matt had to
   *project* the next-election electorate from provincial 2025 data because the 2026
   list doesn't exist yet. For past elections the next electorate is known, so we use
   the actual `eligible_electors(Y) − eligible_electors(Y−1)`. We do **not** use
   census population growth, despite the spec's SCHEMA describing growth that way —
   Matt's stored scores do not use census growth.
2. **A per-year percentile-normalized `defeatability_100` accompanies the raw
   `rank_sum`.** The raw rank-sum is not comparable across years (44-ward years rank
   1..~38, 25-ward years 1..~18), and the whole point is cross-year validation.

## Consequences

- The rank step makes the index robust to the citywide voters'-list churn that
  corrupts raw `eligible_electors` deltas: ranking is invariant to a constant added
  to every ward, so a citywide list rebuild cancels out. Only *differential* per-ward
  list churn survives — an uncontrolled confound in the growth term, documented as a
  known limitation.
- A future reader comparing this to the spec will see census-growth language that we
  deliberately did not follow; this ADR is why.
