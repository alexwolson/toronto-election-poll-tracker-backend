# Spec: make the compact joint model the published mayoral forecast

September 21, 2026. Awaiting the user's approval before implementation.
Decision already taken by the user: the published forecast moves to the compact
joint model with the approved margin-first presentation, recorded in an ADR.

## 1. Requirement

Replace the lightweight poll-average forecast (`backend-2026-09-21.3`, feed
schema 3, band board) with the compact joint model's election-day distributions,
published through a new feed contract (schema 4) and rendered with the approved
"B plus A" presentation (margin distribution, candidate vote-share ranges,
full-race win probabilities). Every public number comes from one set of joint
draws. Nothing is tuned to a preferred probability (ADR 0030).

Constraints carried from the session:
- Statistical specification is frozen as validated: isotropic election
  discrepancy, Gaussian innovations, certified-field 2026 polls only, joint
  refit of the seven historical campaigns with the population priors.
- Held-out record is the calibration basis (leader-margin RMSE 16–17 points at
  five weeks, isotropic 80% coverage 4/4 and 6/7).
- Public presentation shows no bands, no scenarios, no diagnostics; sensitivity
  and diagnostics are audit metadata or build gates, not page content.
- Research artifacts (draws) never enter git; nothing over 90 MB.

## 2. Feed contract: `mayoral_forecast.json` schema 4

`publication_policy: "margin-first-joint-draws-v1"`. Fail closed: the frontend
accepts schema 4 only. Shares are fractions in [0, 1]; margins are vote-share
points.

```
schema_version: 4
publication_policy: "margin-first-joint-draws-v1"
election_cycle_id: "toronto_2026"          # underscore, frontend contract
election_date: "2026-10-26"
analysis_cutoff: ISO 8601 with offset
evidence_tier: "Compact joint model — certified field"
incumbent_candidate_id: per_…
final_field_samples: [poll_id …]           # the polls the fit used
forecast_favourite: {tier, availability, candidate_id, reason}   # ADR 0051 shape
candidate_win: { per_…: {quantity:"challenger_win", candidate_id, tier,
                         availability, probability, reason} }   # no band, no sensitivity
election_day:
  denominator: "full_ballot"
  interval_mass: 0.8
  statistic: "median"
  candidates: [ {candidate_id, display_name, median, lower, upper, win_probability} … ]
  residual_pool: {label:"Other candidates", median, lower, upper,
                  win_probability: 0.0, candidate_count: 50,
                  named_in_polls: [ {candidate_id, display_name, latest_polled_share, poll_id} … ],
                  note: "many minor candidates; not one candidate"}
  # named_in_polls lists certified candidates outside the modelled three whom a
  # certified-field poll reported individually (Sept 2026: McVie, Paloma Parker).
  # They are modelled inside the pool, not as named candidates; see ADR 0054.
  pairwise_margin:
    leader_candidate_id: per_…            # highest win probability
    challenger_candidate_id: per_…        # second
    unit: "vote_share_points"
    median, lower, upper
    probability_challenger_ahead
    outcomes: {close_threshold_points: 2, leader_ahead, close, challenger_ahead}  # exact, from draws; the published view
    bin_width: 5, range: [-100, 100]
    bins: [ {left, right, probability} × 40 ]   # sums to 1; audit metadata after the 2026-09-21 review
model:
  name: "compact_mayoral", version: <git short sha of the builder>
  specification: {discrepancy:"isotropic", innovations:"gaussian",
                  polls:"certified_field_only", hyperpriors:"population_joint_refit"}
  draws: 16000, chains: 4, seed: 20260921
  qualification_passed: true
sensitivity:                                # audit metadata, not rendered
  - {label:"leaders-discrepancy", role:"stress_test", win_probability:{…}, margin_median}
  - {label:"with-pre-certification-polls", role:"stress_test", …}
```

Dropped from schema 3: `band`, `frequency_statement`, per-card `sensitivity`,
`sensitivity_variant_labels`, `close_result`, `incumbent_defeat`,
`margin_distribution` (unsigned KDE with `by_winner`),
`challenger_chance_decomposition`. `candidate_win` is retained because the
`/polls` route derives the viable field from its keys and the favourite card
keeps ADR 0051's shape.

Display policy defaults (the design record marked these provisional; adopted
here unless the user objects): central 80% intervals; medians for vote shares;
whole-percent probabilities with "<1%" and ">99%" at the tails; the residual
pool cannot win; the compared pair is named by the feed, never hardcoded.

## 3. Backend

Files touched (new unless noted):
- `backend/model/compact_mayoral/{__init__,readings,model,hyperpriors}.py` —
  promoted from `docs/research/compact_mayoral/` with one change: input paths.
  Historical corpus from the backend-tracked
  `data/raw/polls/historical_mayoral/` (identical to the data repo's audited
  copy; verified), outcomes from `data/raw/elections/mayoral_outcomes.csv`,
  election dates from `data/raw/elections/mayoral_elections.csv`, reading
  classification from a new tracked `data/raw/polls/mayoral_reading_classification.csv`
  (332 rows: reading id, cycle, class, denominator, dependence group; derived
  once from the 2026-09-12 register by `scripts/derive_reading_classification.py`,
  which records the register's sha256 in the CSV header comment), 2026 polls
  from the hydrated Polling release `polls.csv`, candidate ids from the hydrated
  `results/mayoral_candidates.json`.
- `backend/model/compact_mayoral/fit.py` — production fit: population
  hyperpriors, isotropic, Gaussian, all campaigns, 4 chains × (1,000 warmup +
  4,000 draws), target acceptance 0.95, fixed seed. Runtime about 30 s on the Mac.
- `backend/model/compact_mayoral/qualification.py` — fail-closed gate on the
  fit: zero divergent transitions (one automatic retry at target acceptance
  0.99 with the seed + 1), R-hat < 1.01 and bulk ESS ≥ 400 on every non-constant
  coordinate, finite draws, named shares summing to one. Failure raises and the
  build stops; the previous release stays live.
- `backend/model/compact_mayoral_feed.py` — draws → schema 4 (section 2),
  including the two sensitivity refits (leaders variant; pre-certification
  polls), each about 9 s.
- `scripts/build_publication_snapshot.py` (modified) — calls the new builder;
  `MAYORAL_FORECAST_FEED_SCHEMA_VERSION = 4` flows into `manifest.json`.
- `pyproject.toml` (modified) — `uv add jax numpyro` (CPU wheels; Python 3.14
  verified working in this session).
- `docs/adr/0054-publish-the-compact-joint-model-election-day-distributions.md`
  — adoption, calibration basis, feed 4 contract, presentation change,
  supersession of ADR 0049/0053 for the mayoral feed, residual-pool rule,
  Monte Carlo precision, qualification gate, and the explicit statement that
  the published Chow probability falls from about 84% to about 63% because
  the calibration basis changed, not because of new polls.
- `docs/mayoral-forecast-methodology.md` — plain-language methodology
  replacing the data repo's lightweight document (that one gets a superseded
  notice).
- `backend/model/lightweight_mayoral*.py` and tests — kept for one release
  cycle as a documented fallback, removed afterwards.

Tests first (in `tests/model/`): adapter resolves the backend-tracked inputs
and reproduces the research counts (97 historical polls, 6 certified-field
2026 polls, 2014 reference set); classification CSV round-trips the register;
feed builder emits schema 4 from synthetic draws with bins summing to one,
intervals containing medians, named win probabilities summing to one with the
pool at zero, leader/challenger ordered by win probability, and the pairwise
probability equal to the fraction of draws with the challenger ahead;
qualification gate rejects synthetic diagnostics with a divergence, a bad
R-hat, or low ESS; snapshot script integration on the fixture root. The
research package's 11 tests move with the code (recovery tests trimmed to
about ten seconds each so CI stays fast).

## 4. Frontend

Files touched:
- `src/types/feeds.ts`, `src/lib/feeds.ts` — schema 4 types and validator
  (structure above, all fields required, fail closed; schema 2/3 no longer
  accepted). `FORECAST_FALLBACK` becomes a schema 4 "unavailable" feed.
- `src/lib/mayoral-forecast.ts` — replace the band and KDE selectors with
  `electionDayShares(feed)`, `pairwiseMargin(feed)`, `winProbabilities(feed)`;
  keep `leadForecast` and `viableField`; add `chance()` formatting; remove
  `frequencyWithUnit`, `marginDistribution`, `incumbentDefeat`,
  `agnosticQuantities`, `HISTORICAL_MAYORAL_MARGINS`.
- `src/components/forecast/{margin-chart,vote-share-ranges,win-probabilities}.tsx`
  — production versions of the prototype's three charts: server-rendered SVG
  and markup, colours and ordering from `src/lib/candidates.ts`, bin geometry
  derived from the feed's `left`/`right` rather than hardcoded, copy id-driven.
- `src/components/forecast-hero.tsx` (rewritten) — the approved hierarchy:
  headline, lede with the median margin, margin chart with the
  "challenger finishes ahead" aside, vote-share ranges, full-race win
  probabilities, "Forecast evidence through {date}", and a methodology
  `<details>` for the polls used and assumptions.
- Removed: `src/components/margin-distribution.tsx`, the band-board CSS,
  `src/components/forecast-prototype/` and `PrototypeHost`, the
  `prototype:forecast` script (the prototype stays on its branch, as the
  design record asks).
- Copy: `src/lib/methodology.ts` (flow step 6, glossary), `src/app/how-it-works/page.tsx`
  (the "how a result becomes a public band" example becomes "how draws become
  the three views"), `PRODUCT.md`, `DESIGN.md` (band-card pattern retired,
  margin-first pattern documented), `docs/v2-release.md` checklist line,
  `fixtures/README.md`, `docs/design/forecast-presentation-prototype.md`
  (closing note pointing at the implementation).
- Fixtures regenerated to schema 4 from a real build output
  (`fixtures/`, `fixtures-preview/`).

Tests first: `feeds.test.ts` (schema 4 accepted, 2/3 rejected, each dropped
field rejected), `mayoral-forecast.test.ts` (new selectors, ordering,
formatting table for `chance`), component tests for the three charts and the
hero (accessible names, no band vocabulary, id-driven names), `primary-page-copy`
updated (no `band-board`), `methodology.test.tsx` updated. ESLint, `tsc`,
`npm test`, and a static build must pass before the PR.

## 5. Release sequence

1. Backend PR → merge → cut `backend-2026-09-2X.1` in the clean worktree
   (`refresh_all.py` runs lint, tests, the 30 s fit, the gate, the bundle).
2. Frontend PR → merge (production keeps serving the last deployment; a
   rebuild against the old tag would fail closed, which is intended).
3. Preview deploy with `--build-env BACKEND_RELEASE_TAG=<new tag>`; verify
   the three views against the feed numbers.
4. You run the two-value promotion (`BACKEND_RELEASE_TAG` update, then
   `npm run deploy:production -- <tag>`); I verify production.

## 6. Effort

Backend about 2 hours, frontend about 2–3 hours, release about 1 hour with
the usual retries. All on this Mac; no cloud.

## 7. Out of scope (follow-ups)

A staleness/retained-forecast state in the feed; a "what changed since the
last snapshot" panel; past-election markers on the new margin chart (not in
the approved design); deleting the lightweight module; a tighter `tau_lead`
prior for the leaders stress test.

## 8. Decisions taken here that the user may override

Display defaults in section 2; sensitivity block carried as audit metadata
(leaders, pre-certification) and not rendered; schema 4 replaces 2/3 rather
than coexisting; lightweight module kept one release then deleted; no
past-election markers.
