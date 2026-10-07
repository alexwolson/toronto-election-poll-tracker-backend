# Current Project Scope

## Current operating scope (2026-10-07)

Production uses the v3 compact joint mayoral model in
`backend/model/compact_mayoral/` and `compact_mayoral_feed.py`. ADRs 0054–0057
record adoption, the Dirichlet election-day discrepancy, the uncertainty breakdown
and current-cycle reading selection.
One eligible reading per current sample is selected from the exact Polling release
independently of the public archive, using its own base. The historical corpus
comes from the same release, by the same selection rule (ADR 0060). Main and historical
snapshot fits must pass the numerical qualification gate; sensitivity refits are
audit metadata rather than probability-band publication gates.

[ADR 0061](adr/0061-learn-where-a-suspended-campaigns-support-goes.md) records how
the model handles Chris Alexander's Suspended Campaign (October 6). Post-Suspension
Readings enter as Chow–Bradford compositions. In the 2026 campaign only, Alexander
keeps a Kept Fraction drawn from ten past cases, and the rest of his support
divides by an Exit Allocation learned from those readings (C2). Under it the
forecast feed moves from schema 4 to 5, and Backend reads `campaign_suspended_on`
from the Results candidates feed at schema 6.

**Status (2026-10-07).** Production is still `backend-2026-10-06.1` (schema 4,
fitted on polls taken before the exit), with a site notice. No Backend release
ships until the ADR 0061 build is done (the release hold). The records PR merges
first, then the code PR. One Backend release then carries both, plus the held
2010 Ipsos Reid addition, and goes out with the matching Frontend after a
preview. Production is due by Fri 2026-10-16. If that is missed, production stays
on `backend-2026-10-06.1` with the notice through election day. The plan and every
decision are on [Handle Alexander's Suspended Campaign in the mayoral
forecast](https://github.com/alexwolson/toronto-election-poll-tracker-backend/issues/27).

Follow the [poll ingestion and release runbook](../../toronto-election-poll-tracker-data/docs/runbooks/add-2026-mayoral-poll.md)
for the Results → Polling → Backend → Frontend chain and
[the current methodology](mayoral-forecast-methodology.md) for the model.
`scripts/refresh_all.py` hydrates the pinned releases, runs checks, builds all
Backend feeds and packages the release. The frontend deploys an exact Backend tag.
