# Endorsement data audit

Snapshot audited: upstream schema `2.1.0`, generated `2026-08-23T12:01:48.080046Z`. This note uses only
the upstream repository's schema documentation, source code, curated inputs, and generated
artifacts. The manifest records the exact artifact row counts and checksums
([build manifest](/Users/alex/code/personal/toronto-election-results/data/out/build_manifest.json:73),
[release metadata](/Users/alex/code/personal/toronto-election-results/data/out/build_manifest.json:204)).

## Bottom line

The dataset can support **per-Endorser descriptive association tests**, but the exposure must be
named **“confirmed endorsement recorded”**, not simply “endorsed.” Endorsements are intentionally
open-world positive facts: an absent edge does not establish opposition, neutrality, or even that
the Endorser did not endorse that candidate. The clean primary comparator is therefore a candidate
with no confirmed edge **inside an Endorser–Contest cell marked
`comprehensive_source_found`**. Partial, unsearched, unavailable, and inapplicable cells should be
unknown in the primary analysis, not zero exposure
([ADR 0008](/Users/alex/code/personal/toronto-election-results/docs/adr/0008-model-endorsements-as-open-world-facts.md:5),
[data dictionary](/Users/alex/code/personal/toronto-election-results/docs/data-dictionary.md:156)).

This supports correlation, not a causal “endorsement effect”: Endorsers choose candidates in light
of campaign strength, incumbency, ideology, and strategic viability, and endorsements from one
election or slate are not independent observations.

## Tables, grain, and joins

| Artifact | Exact grain and role | Key fields |
|---|---|---|
| [`endorsers.csv`](/Users/alex/code/personal/toronto-election-results/data/out/endorsers.csv) | One exact individual, organization, or editorial board. Parent bodies, locals, affiliates, boards, and members are separate entities. | Unique `endorser_id`; `canonical_name`; `endorser_type`; optional `person_id`; panel, eligibility, applicability, and evidence fields. |
| [`endorsement_assertions.csv`](/Users/alex/code/personal/toronto-election-results/data/out/endorsement_assertions.csv) | One source-specific claim. This is the evidence/review layer, not the modelling exposure table. | Unique `assertion_id`; nullable `endorsement_id`; `endorser_id`; `contest_id`; nullable `candidacy_id`; review, kind, date/precision, source type and evidence URLs. |
| [`endorsements.csv`](/Users/alex/code/personal/toronto-election-results/data/out/endorsements.csv) | One adjudicated positive edge per `(endorser_id, contest_id, candidacy_id)`. | Stable `endorsement_id` plus the three foreign keys. |
| [`endorsement_coverage.csv`](/Users/alex/code/personal/toronto-election-results/data/out/endorsement_coverage.csv) | One row per approved Endorser and Toronto Mayor/City Councillor Contest. This is search metadata, not candidate-level negative evidence. | `(endorser_id, contest_id)`; `coverage_state`; `assessed_through`; `coverage_basis`. |

Only `confirmed` assertions produce facts. The assembler enforces exact Endorser, Contest, and
Candidacy foreign keys; requires the Candidacy to belong to the stated Contest; deduplicates the
three-part edge; and derives `endorsement_id` deterministically from it
([assembler](/Users/alex/code/personal/toronto-election-results/src/toronto_election_results/endorsements.py:196),
[fact validation](/Users/alex/code/personal/toronto-election-results/src/toronto_election_results/endorsements.py:385)).
Although the model allows one Endorser to select multiple Candidacies in one Contest, the current
artifact has one target in every one of its 154 Endorser–Contest fact cells.

For outcomes, join `endorsements.candidacy_id` to
[`election_results.csv`](/Users/alex/code/personal/toronto-election-results/data/out/election_results.csv),
retaining and checking `contest_id`. The result row supplies `vote_share`, `elected`,
`result_status`, `incumbent`, field size, election, and office. Join by IDs, never candidate names.
`person_id` is optional for the endorsed candidate and is only needed for repeated-person/history
work; 5 of the 154 fact rows currently have a null candidate `person_id`. Individual **Endorsers**
have a different rule: a person Endorser must link to exactly one persistent Person, while
non-person Endorsers may not carry a Person link
([Endorser validation](/Users/alex/code/personal/toronto-election-results/src/toronto_election_results/endorsements.py:136)).

## Current panel and usable volume

The approved panel has nine exact Endorsers: four organizations, two editorial boards, and three
individuals. The panel is deliberately selected, not a representative sample: institutions were
admitted under a 2023-anchored rule and the individuals are living former/current mayors, eligible
only from the date each first assumed office
([panel decision](/Users/alex/code/personal/toronto-election-results/docs/adr/0008-model-endorsements-as-open-world-facts.md:13),
[panel input](/Users/alex/code/personal/toronto-election-results/data/reference/endorser_panel_curations.csv)).

Counts below are recomputed from the four published CSV artifacts. “Comprehensive facts” are the
positive edges retained by the conservative primary coverage rule.

| Endorser | Type | Eligible from | Facts | Elected targets | Comprehensive cells | Comprehensive facts |
|---|---|---:|---:|---:|---:|---:|
| Toronto Star Editorial Board | editorial board | 2003-01-01 | 70 | 46 | 74 | 70 |
| Amalgamated Transit Union Local 113 | organization | 2003-01-01 | 28 | 17 | 43 | 28 |
| Toronto Sun Editorial Board | editorial board | 2003-01-01 | 17 | 12 | 29 | 17 |
| John Tory | person | 2014-12-01 | 15 | 9 | 25 | 11 |
| Progress Toronto | organization | 2018-01-01 | 13 | 7 | 29 | 13 |
| David Miller | person | 2003-12-01 | 4 | 2 | 0 | 0 |
| Elementary Teachers of Toronto (ETT) | organization | 2003-01-01 | 4 | 1 | 4 | 4 |
| CUPE Ontario | organization | 2003-01-01 | 3 | 2 | 3 | 3 |
| Olivia Chow | person | 2023-07-12 | 0 | 0 | 0 | 0 |

The conservative sample contains 207 Endorser–Contest cells, 2,510 candidate rows, and 146
confirmed positive edges. It cannot estimate a Miller or Chow contrast. Several other Endorsers
have very few independent elections even where their candidate-row count looks large: for example,
John Tory's 25 comprehensive cells are the 25 council contests in 2022, and hence only one election
event. Event-wide slate rows must not be treated as 25 independent replications.

Across the full positive table, 154 facts cover 120 distinct Candidacies in 98 Contests. Ninety-five
Candidacies have one panel endorsement, 17 have two, seven have three, and one has four. Per-Endorser
estimates will therefore be correlated, and a mutually adjusted “independent contribution” model
will have much less information than the raw row count suggests.

## Types, states, time, and null rules

- Allowed Endorser types are `person`, `organization`, and `editorial_board`. The current assertion
  kinds are 87 `editorial_choice`, 57 `endorsement`, and 11 `progressive_champion`; these labels
  should remain visible rather than being editorially rewritten as identical behaviour. Allowed
  values are enforced in the assembler and Toronto curation boundary
  ([types and target offices](/Users/alex/code/personal/toronto-election-results/src/toronto_election_results/endorsements.py:18),
  [curation columns](/Users/alex/code/personal/toronto-election-results/src/toronto_election_results/endorsement_curations.py:47)).
- Assertion review states in the general model are `proposed`, `confirmed`, `unresolved`,
  `rejected`, and `withdrawn`. The default Toronto curations currently admit only `confirmed` and
  `unresolved`; the release has 154 confirmed and one unresolved. The unresolved John Tory/Cynthia
  Lai claim has no published Candidacy row and therefore creates no fact
  ([curation rule](/Users/alex/code/personal/toronto-election-results/src/toronto_election_results/endorsement_curations.py:41),
  [documented unresolved target](/Users/alex/code/personal/toronto-election-results/src/toronto_election_results/endorsement_curations.py:789)).
- Coverage states are `not_applicable`, `not_searched`, `partially_searched`,
  `searched_no_endorsement_found`, `comprehensive_source_found`, and `source_unavailable`. Current
  counts are respectively 643, 145, 1,277, **0**, 207, and 113. `assessed_through` is deliberately
  null for all 145 `not_searched` cells; a release date is not substituted for a historical search
  date
  ([coverage semantics and counts](/Users/alex/code/personal/toronto-election-results/docs/data-dictionary.md:164),
  [coverage construction](/Users/alex/code/personal/toronto-election-results/src/toronto_election_results/endorsement_curations.py:746)).
- Assertions carry `announcement_date` plus `date_precision`. Current precision is 136 day, 16
  month, 2 year, and 1 unknown; three confirmed assertions have null dates. A known announcement
  date is rejected if it is later than election day, and an assertion may not predate Endorser
  eligibility
  ([temporal validation](/Users/alex/code/personal/toronto-election-results/src/toronto_election_results/endorsement_curations.py:457)).
  The three null-date facts should be excluded in a timing/source-quality sensitivity because they
  cannot be proven usable at a precise live prediction cutoff from the date field alone.
- Endorsements target only Toronto Mayor and City Councillor Contests. The collection window runs
  through the close of polls on 2026-10-26, and otherwise-applicable 2026 coverage cells remain
  `partially_searched` while that election is live
  ([collection window](/Users/alex/code/personal/toronto-election-results/CONTEXT.md:16),
  [live-cell rule](/Users/alex/code/personal/toronto-election-results/src/toronto_election_results/endorsement_curations.py:682)).
  The present 154 facts all join to final historical results from 2003–2025; there are no confirmed
  2026 fact edges in this snapshot. Pending 2026 Candidacies have null result values and must not
  enter a success analysis
  ([pending-result semantics](/Users/alex/code/personal/toronto-election-results/CONTEXT.md:130),
  [2026 identity decision](/Users/alex/code/personal/toronto-election-results/docs/adr/0008-model-endorsements-as-open-world-facts.md:26)).

## Provenance and integrity

The upstream build has three checked-in curation inputs:

- [`endorser_panel_curations.csv`](/Users/alex/code/personal/toronto-election-results/data/reference/endorser_panel_curations.csv) records exact entities, Person locators, eligibility, applicability, panel basis, and evidence;
- [`endorsement_assertion_curations.csv`](/Users/alex/code/personal/toronto-election-results/data/reference/endorsement_assertion_curations.csv) records exact Contest/Candidacy locators, review, dates, source type, and evidence URLs; and
- [`endorsement_coverage_curations.csv`](/Users/alex/code/personal/toronto-election-results/data/reference/endorsement_coverage_curations.csv) records audited Endorser–Contest or event/office search work, evidence, verification report, and search-certificate provenance.

All three are SHA-256 pinned in source and recorded as build-manifest inputs
([checksum enforcement](/Users/alex/code/personal/toronto-election-results/src/toronto_election_results/endorsement_curations.py:27),
[manifest sources](/Users/alex/code/personal/toronto-election-results/data/out/build_manifest.json:857)).
Curated locators include expected stable IDs, election date, office, district, and candidate display
name, and fail closed if any locator drifts; there is no fuzzy/name fallback
([exact resolution](/Users/alex/code/personal/toronto-election-results/src/toronto_election_results/endorsement_curations.py:490)).
Every assertion has a required HTTPS primary evidence URL; the optional secondary URL is null in 55
of 155 rows. Source types are heterogeneous, including first-party material, publisher editorials,
contemporaneous attribution, and recovered copies, so a source-quality sensitivity is warranted.

## Recommended analysis contract

For each `endorser_id`, separately:

1. Use only `result_status == final` Mayor or City Councillor Candidacies.
2. Primary exposure universe: Endorser–Contest cells with
   `coverage_state == comprehensive_source_found`. Define `recorded_endorsement = 1` only for an
   exact edge in `endorsements`; call the comparator “no confirmed endorsement recorded in the
   comprehensive-source cell,” never “opposed” or simply “unendorsed.”
3. Model `vote_share` as the main continuous outcome and `elected` as a secondary outcome. Separate
   or explicitly interact Mayor and Councillor; adjust for election/event, incumbency or candidate
   regime, and field size. Do not infer a causal effect.
4. Use Contest-clustered uncertainty and election-to-election checks. For event-wide slates, add an
   event-level or leave-one-election-out sensitivity; large candidate counts within one event do not
   create independent historical replication. Repeated candidate Persons and overlapping
   Endorsers add further dependence.
5. Report per Endorser: positive facts, comprehensive cells, distinct elections, effect/association,
   uncertainty, election-specific direction, date/source sensitivity, and an explicit data-limited
   tier. Correct across the family of Endorser/outcome tests.
6. A broader sensitivity may use every Contest with at least one confirmed fact for that Endorser,
   but its zero category must remain “no recorded edge” and be flagged as vulnerable to incomplete
   ascertainment. Positive facts outside comprehensive cells can support endorsed-target success
   summaries; they do not by themselves create a reliable binary comparison group.

This contract gives a defensible answer to whether each exact Endorser's **recorded selections are
historically associated with electoral success**, while respecting what the upstream dataset does
and does not claim.
