# Tory endorsement scenario analysis

The user approved the research memo's conditional analysis on September 9, 2026
("Let's do it"). Implement that scope as a reproducible local research report.

## Requirement and design

Compare hypothetical Tory endorsements of Bradford and Alexander using fixed,
sourced decided/leaning poll baselines. Show assumed support shifts, margins against
the strongest other named candidate, and the gain needed to tie for the lead.
Use -3, 0, +3, +6, +9 percentage-point settings and transfers involving Chow,
the other challenger, or an equal mixture. Reverse the flows for adverse effects.

Use the Pallas August 19–21 and Liaison August 14–16 readings independently, with
their original values, fieldwork, publication dates, source links, reading IDs,
and file hashes. Normalize source rounding for this arithmetic only and disclose
the adjustment. Hold the published residual fixed; it is not a candidate or donor.

Record hypothetical event dates and an explicitly assumed fraction of the potential
shift realized by election day (100%, 50%, or 0%). Calendar dates never estimate
persistence. The realized net shift includes any restriction from already-cast
ballots; no unsupported turnout or early-vote allocation is added.

Reject infeasible transfers with an explanation, without clipping or reallocating.
Show thresholds against every named opponent, since catching Chow alone may leave
Alexander behind Bradford. A threshold above available donor support is unavailable.

The report is conditional arithmetic holding all other change fixed. It has no
causal coefficient, confidence interval, win probabilities, or production-feed
integration. It is not a model refresh, poll ingestion, or deployment.

## Files and verification

- `backend/analysis/endorsement_scenarios.py`: public calculation and baseline/report
  interface; the worked examples and conservation constraints in the approved memo
  define the calculation boundary tested with failing tests first.
- `scripts/analyze_tory_endorsement.py`: reproducible report entry point.
- `backend/analysis/endorsement_report.html`: interactive view of precomputed results;
  no duplicated statistical calculations in browser code.
- `tests/analysis/test_endorsement_scenarios.py`: observable calculation behavior,
  impossible transfers, ties, persistence, and source-backed report generation.
- `docs/research/tory-endorsement-scenarios/`: generated HTML, JSON, CSV, and Markdown.

Test vertical slices using the accepted numerical examples, then run the complete
analysis test suite, lint changed Python, check deterministic generation, and inspect
desktop/mobile report interactions. Existing forecast qualification is unchanged:
this calculation does not import, fit, mutate, or publish the Mayoral Forecast.

Why: a standalone sensitivity calculation makes the effect and vote-flow assumptions
reviewable without assigning an empirically unsupported endorsement effect.
