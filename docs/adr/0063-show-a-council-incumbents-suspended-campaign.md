# Show a council incumbent's Suspended Campaign on the race card

Status: proposed — contingent on a confirmed Suspended Campaign; the report may not hold

## Context

On October 9, 2026, CityNews reported that Frances Nunziata, the Ward 5 incumbent, was going to
end her campaign; it was not confirmed. After the August 21 withdrawal deadline she would stay on the Final Ballot.
Results ADR 0010 publishes councillor Suspended Campaign dates in
`council_campaign_suspensions.json`. The council race card (ADR 0043) is descriptive. It has no
forecast to adjust, but it labels each ward's attention level and lists its ward polls.

## Decision

- **Read the dates from the pinned Results release.** `build_council_snapshot.py` loads
  `council_campaign_suspensions.json` and fails closed when it is missing or malformed.
- **Mark every candidate.** Each candidate card carries `campaign_suspended_on`, a date or null.
- **An incumbent's Suspended Campaign is not an open seat.** The incumbent is still on the ballot
  and can still win. The card sets `incumbent_campaign_suspended_on`, and its attention level
  becomes `suspended`, labelled "Incumbent suspended campaign" (Alex, 2026-10-09). It ranks with
  open seats. The map legend lists the label only when some ward has it.
- **Keep earlier ward polls, flagged.** Each ward poll carries `before_incumbent_suspension`, which
  is true when its fieldwork came before the incumbent's suspension date. Polls are shown as they
  are, with no reallocation and no re-modelling (Alex, 2026-10-09).
- `council_race_cards.json` moves from schema 10 to 11.

## Consequences

- The frontend must accept schema 11, the `suspended` attention level, and its map key.
- A Backend release needs a Results release that carries the feed (ADR 0010 or later).
