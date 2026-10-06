# 0060. Read the historical corpus from the pinned Polling release

Date: 2026-10-06. Status: accepted.

## Context

The Polling repository owns poll evidence, but the compact model read the
historical mayoral corpus from Backend's own tracked copy of
`data/raw/polls/historical_mayoral/`. A tracked classification table,
`data/raw/polls/mayoral_reading_classification.csv`, derived from the 2026-09-12
research register, filtered that copy. The Polling release did not carry the
audited corpus. A historical poll added in the Polling repository therefore
never reached the forecast unless someone copied it by hand. The two copies had
already drifted: on 2026-09-23 the Polling copy gained `denominator_semantics`
and Backend's did not. Historical denominator semantics also had two sources:
the classification table, which the model used, and the readings' own column.
This came up while the Ipsos Reid poll of Sept 24–26, 2010 was being added
(issues 35 and 36).

Backend also kept a stale duplicate of the historical ingestion scripts, plus
the pre-compact mayoral chain (the historical loader and evaluation, the
endpoint and its qualification, the legacy forecast feed, the incumbency
endpoint, and five diagnostic or evaluation scripts). Only that chain read the
copy, and the production build loads none of it.

## Decision

1. The Polling repository is the only owner of the historical corpus and of the
   per-reading classification. Each Polling release ships the five corpus tables
   and `reading_classification.csv` as flat assets named
   `historical_mayoral_<table>.csv`. The build fails unless the classification
   covers every corpus reading exactly once.
2. Backend reads the historical campaigns from its pinned Polling release, the
   same directory it reads the 2026 polls from. Loading the release inputs
   fails closed if any of the six assets is missing (ADR 0032).
3. One selection rule serves every campaign. Each sample's ordinary reading is
   chosen by the reading's own `denominator_semantics` (decided-plus-leaners,
   then decided-only, then all-respondents, then `other`; ties go to more named
   candidates, then id), as ADR 0057 set for 2026. The classification supplies
   only the measurement class. A sample's readings are grouped by their
   `poll_sample_id`, which is what the register's dependence group always was.
4. Backend deletes its corpus copy, the classification table and its derivation
   script, the duplicated ingestion scripts, and the pre-compact chain with its
   tests. A maintained copy of that chain still runs in the Polling repository
   against the owned corpus. Git history keeps the Backend versions.

## Consequences

- Adding a historical poll touches only the Polling repository: run the
  double-read ingest and add the classification rows.
- The next Backend release must pin a Polling release that carries the
  historical assets. `polling-2026-10-06.2` and earlier releases do not, so
  Backend refuses them.
- On the same inputs the forecast is unchanged. A production fit on a candidate
  Polling release reproduced the previous build's draws exactly (Chow 0.7425,
  Bradford 0.255625, Alexander 0.001875).
- Tests use a checked-in two-campaign fixture laid out as a Polling release,
  because CI does not download releases.
- The 2026-09-12 register stays a frozen research record. Its vocabulary
  splits `other` into `not_reported` and `other_source_defined`, which no longer
  matters to selection.
