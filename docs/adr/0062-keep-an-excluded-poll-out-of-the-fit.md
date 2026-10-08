# 0062. Keep an Excluded Poll out of the fit

Date: 2026-10-08. Status: accepted.

This ADR amends ADR 0057. It adds one explicit step before current-cycle reading
selection: a sample the maintainer has excluded is never modelled.

## Context

Scope Research published its first Toronto mayoral poll on October 8, 2026
(fieldwork October 6, n = 3,100, all respondents: Chow 44, Bradford 41). The only
source is a web post and one chart. It describes an online survey of people
invited by text message, states no weighting or sample source, and gives a margin
of error only "for a comparable probability-based sample". Scope has no earlier
election poll that can be checked against a result, and it is not a member of
the Canadian Research Insights Council.

Under ADR 0057 the poll would have entered the fit as a Post-Suspension Reading
(ADR 0061) with the largest effective base of the cycle (about 2,600). As Scope's
only poll, its house effect would rest on the shared prior alone, and it would
feed the Exit Allocation directly.

Until now nothing kept a poll out of the fit except missing data (a `blocked`
sample) or the reading rules. ADR 0057 also says the archive selection must never
steer the forecast, so a judgement about a poll needed its own recorded place.

## Decision

1. **Excluded Poll.** The maintainer may decide that a 2026 citywide sample is not
   used in the forecast. The decision is recorded in Polling's
   `data/raw/polls/model_exclusions.csv`: the sample, the decision date, one or
   more reasons, a public explanation, and internal notes. The reasons are a
   closed list: `methodology_confidence`, `insufficient_track_record` and
   `not_cric_member`. A new reason needs a new decision.
2. **Backend skips it.** `_select_current_readings` drops every listed sample
   before choosing readings. That covers the main fit, both sensitivity refits and
   every history point. The table is required: hydration refuses a Polling
   release without `model_exclusions.csv`, and the forecast fails without it,
   the same fail-closed rule as ADR 0060.
3. **The record keeps it.** An Excluded Poll is ingested in full. It stays in the
   five tables, the public archive and the polling feed, where its entries carry
   `model_exclusion: {decided_on, reasons, explanation}`. The site shows it as not
   used in the forecast, with the explanation, and leaves it off the trend chart.
4. **No forecast feed change.** The forecast's `model.current_readings` and
   `final_field_samples` simply omit the sample. Forecast schema 5 is unchanged.

The first and only Excluded Poll is `scope-2026-10-06`, for all three reasons,
decided on October 8, 2026. The maintainer checked CRIC membership against
CRIC's member list.

## Guard rails

- Exclusion is a judgement about a poll's method and provenance, made by the
  maintainer. It is never inferred from, or justified by, the poll's numbers or
  its effect on the forecast (ADR 0030). Scope's exclusion was decided before any
  forecast with or without it had been computed.
- It applies to the current cycle only. The historical corpus keeps its own
  classification (ADR 0060).
- The research harness (`docs/research/compact_mayoral/readings.py`) does not
  read the table. A research fit of 2026 must remove excluded samples itself.

## Consequences

- The forecast built from a Polling release that adds Scope matches the
  forecast without it, apart from CPU draw noise. No history point is added at
  October 8.
- Adding an exclusion is a data change plus a Polling and Backend release, like
  adding a poll. Removing one is the same.
