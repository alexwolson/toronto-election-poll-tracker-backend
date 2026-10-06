# Current Project Scope

## Current operating scope (2026-09-29)

Production uses the v3 compact joint mayoral model in
`backend/model/compact_mayoral/` and `compact_mayoral_feed.py`, publishing forecast
feed schema 4. ADRs 0054–0057 record adoption, the Dirichlet election-day
discrepancy, the uncertainty breakdown and current-cycle reading selection.
One eligible reading per current sample is selected from the exact Polling release
independently of the public archive, using its own base. The historical corpus
comes from the same release, by the same selection rule (ADR 0060). Main and historical
snapshot fits must pass the numerical qualification gate; sensitivity refits are
audit metadata rather than probability-band publication gates.

Follow the [poll ingestion and release runbook](../../toronto-election-poll-tracker-data/docs/runbooks/add-2026-mayoral-poll.md)
for the Results → Polling → Backend → Frontend chain and
[the current methodology](mayoral-forecast-methodology.md) for the model.
`scripts/refresh_all.py` hydrates the pinned releases, runs checks, builds all
Backend feeds and packages the release. The frontend deploys an exact Backend tag.
