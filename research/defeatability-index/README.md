# Council Defeatability Index (historical)

Reconstructs Matt Elliott's Council Defeatability Index for every incumbent Toronto
city councillor going into each municipal general election (2006–2022), faithfully
replicating his rank-sum method and attaching realized outcomes so the index can be
backtested. Built on the clean [`toronto-election-results`](../../toronto-election-results)
dataset.

- **What each term means**: [`CONTEXT.md`](./CONTEXT.md)
- **How it's built and why**: [`SPEC.md`](./SPEC.md), decisions in [`docs/adr/`](./docs/adr)

## Method in one line

Per election year, rank each incumbent's three components across the pool
(vote share, elector share, new-voter margin; rank 1 = safest) and sum the ranks —
plus a percentile-normalized `defeatability_100` comparable across years.

## Status

- ✅ Ranking core (`ranking.py`) — reproduces Matt's own stored scores exactly.
- ✅ 2014→2018 electorate crosswalk (`crosswalk.py`) — conserves the citywide electorate.
- ✅ Population join → components → backtest → output (`build.py`) —
  writes `data/out/defeatability_index.csv` (201 incumbent-year rows, 2006–2022).
- ✅ Predictive validation (`analysis.py`) — writes
  [`docs/analysis-report.md`](./docs/analysis-report.md) + `figures/`.
- ⚠️ Candidate-history study (`candidate_history_study.py`) — own and Opponent-field
  political history for every council Candidacy. The pipeline and exploratory artifacts
  are implemented. The Prior-officeholder identity gate is closed and the revised
  left-censoring-aware protocol finds **supported predictive signal**; effects specific to
  Prior-unsuccessful candidates remain identity-limited.
- ✅ Endorsement association study (`endorsement_analysis.py`) — per-Endorser field and
  Incumbency-matched selection records, with open-world coverage handling and corrected uncertainty.

## Commands

```bash
uv run python -m defeatability_index.build      # build data/out/defeatability_index.csv
uv run python -m defeatability_index.analysis   # write docs/analysis-report.md + figures/
uv run python -m defeatability_index.candidate_history_study  # career-history artifacts
uv run python -m defeatability_index.endorsement_analysis     # endorsement associations
uv run pytest                                   # tests
uv run ruff check src tests
```

Candidate-history outputs live in `data/out/candidate_history/`, including the candidate
frame, identity audit, pre-specified evidence report, full exploration, model tables, and
figures. `supported_historical_hints.csv` is the machine-readable catalog for downstream
frontend use; `historical_hint_audit.csv` retains every tested but withheld flag and
`historical-hints-report.md` explains the evidence, and
`all-past-races-victory-count-report.md` records the pooled and stratified Victory-count audit.
`candidate-history-flag-screen-report.md` records the diagnostic reader-readable flag batch.
`candidate-history-flag-approval-report.md` records which corrected associations are approved for
descriptive publication and any required grouping rules.
`docs/research/candidate-history-watch-list-review.md` records the supplemental influence and
permutation checks for the reopened near-miss and Returning-councillor patterns.
`historical_hint_contract.json` locks the reader-visible race-history scope,
Returning-councillor rule, acclamation handling, null semantics, and display contract.
Study-specific external facts are sourced in
`data/reference/`; persistent Person identity remains owned by the upstream results project
(ADR 0003).

Endorsement outputs live in `data/out/endorsements/`. `endorsement_observations.csv` is the joined
positive-edge audit, `endorser_associations.csv` contains the per-Endorser field and
Incumbency-matched results, and `endorsement-analysis-report.md` explains the evidence and limits.
The upstream schema and coverage audit is recorded in
`docs/research/endorsement-data-audit.md`.
