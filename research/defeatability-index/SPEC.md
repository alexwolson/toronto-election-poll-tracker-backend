# Historical Council Defeatability Index — Implementation Spec

Status: **implemented** (`build.py` writes `data/out/defeatability_index.csv`; 19 tests green).

## Requirement

Reconstruct Matt Elliott's Council Defeatability Index for every incumbent Toronto
city councillor going into each in-scope general election, faithfully replicating his
rank-sum method, and attach realized outcomes so the index can be backtested. Source
of record is the clean `toronto-election-results` dataset.

## Settled decisions (from the design interview)

- **Framing**: predictive — score each incumbent *going into* election year Y from
  their prior win + ward growth to Y. Faithful backtest of Matt's real index. [Q1a]
- **Backtest**: attach each incumbent's realized year-Y outcome. [Q2a]
- **Population**: all sitting incumbents going into Y, with a `ran_for_reelection`
  flag; no silent drops. [Q3b]
- **Scoreable years**: 2006, 2010, 2014, 2018, 2022. 2003 excluded (no 2000 tallies).
  2018 included as a flagged cross-era special case. [Q4a]
- **Prior win**: most recent electoral win before Y — general *or* by-election. [Q13a]
- **Growth component**: Matt's "new-voter margin" = (electors added since prior win) −
  (prior winning margin), using ground-truth next-election electorate. Not census
  growth. [Q6a]
- **Ranking pool**: per-year, scoreable incumbents only; appointees / acclaimed-prior /
  no-prior-result kept as flagged rows, excluded from ranking. [Q7a]
- **Combination**: sum of three per-year cross-ward ranks (rank 1 = safest) =
  `rank_sum`; plus a percentile-normalized `defeatability_100` for cross-year
  comparison. [Q9a]
- **2018 crosswalk**: area-weighted 2014→2018 electorate overlay, with within-ward
  raking for the ~8% poly-less special polls. [Q12b, Q14b, Q15a] — see ADR 0002.
- **No reconciliation** against the poll-tracker's 121-case file. [Q10b]

## Inputs (read-only; path via config/env, never hardcoded)

Default root `TORONTO_ELECTION_RESULTS_DIR` → `../../toronto-election-results`.

- `data/out/election_results.csv` — normalized Candidacy×Contest results (Vote share,
  votes, electorate, Elected, Incumbent, persistent Person ID, and source identity).
- `data/out/office_tenures.csv` + `people.csv` — **the scored population**: the last valid
  councillor roster before each election, including appointments and retirements.
- `data/raw/voter_stats/2014-voter-statistics.xls` — subdivision electorate (crosswalk).
- `data/raw/subdivisions/voting-subdivisions-{2014,2018}-4326.geojson` — raw subdivision
  polygons used by the downstream 2018 crosswalk; upstream v2 no longer publishes a
  subdivision-level output artifact.
- *(later)* council by-election result rows, once added upstream — must carry
  `eligible_electors`, per-candidate `votes`/`elected`, and a real date.

**Population choice (baked in, flagged here so it isn't silent):** the scored set comes
from the upstream Office-tenure rows whose final reference is the scored election date,
each member joined through persistent **Person ID** to their prior win and year-Y
Candidacy. Deriving from prior-election winners remains rejected because it misses
appointments and people who leave before election day. This project performs no name
matching. The ranking pool is **runners only** (Q17b): retirees are kept as flagged rows
with the two vote-based components but no growth term or rank.

## Method (per scored incumbent, for year Y)

Components, measured on the prior win:
1. `vote_share` = votes / total_contest_votes.
2. `elector_share` = votes / eligible_electors (prior-win ward).
3. `new_voter_margin` = new_electors − winning_margin, where
   `winning_margin` = incumbent votes − runner-up votes (prior win), and
   `new_electors` = eligible_electors(Y ward) − eligible_electors(prior-win ward);
   within-era by ward number, 2018 via the crosswalk (ADR 0002).

Ranking (per year Y, over the pool of scoreable incumbents, N = pool size):
- `rank_vote_share`   = rank(vote_share, descending)  → rank 1 = highest share = safest.
- `rank_elector_share`= rank(elector_share, descending)→ rank 1 = safest.
- `rank_new_voter_margin` = rank(new_voter_margin, ascending) → rank 1 = fewest new
  voters vs cushion = safest.
- Ties: competition ranking (`method="min"`).
- `rank_sum` = the three ranks summed (higher = more defeatable).
- `defeatability_100` = 100 × mean over the three of `(rank − 1)/(N − 1)`
  (0 = safest, 100 = most defeatable; N-invariant, comparable across years).

## Output

One tidy CSV, `data/out/defeatability_index.csv`, one row per incumbent × scored year:

- **Identity**: election_year, ward_system, ward_number, ward_name, candidate_id,
  candidate_name, incumbent_source.
- **Prior win**: prior_win_year, prior_win_type (general|byelection), prior_vote_share,
  prior_elector_share, prior_winning_margin, new_electors, new_voter_margin.
- **Index**: rank_vote_share, rank_elector_share, rank_new_voter_margin, rank_sum,
  pool_size, defeatability_100.
- **Backtest**: ran_for_reelection, elected_Y, new_vote_share_Y, margin_Y.
- **Flags**: cross_era, dual_incumbent_2018, by_election_incumbent, no_prior_result.

## Tooling

uv + pandas + geopandas + rapidfuzz + xlrd, Python ≥3.14 (mirrors the source repo).
Script `scripts/build_index.py`; crosswalk isolated in its own module.

## TDD plan (failing test first, per component)

1. **Faithfulness lock**: feed Matt's own `data-qT4Kx.csv` (25 wards + mayor) through
   the ranking code and reproduce his stored Defeatability Score exactly
   (Matlow 3, Fletcher 7, Saxe 68, Malik 70). This pins the formula/orientation.
2. **Component units** on small fixtures: vote_share, elector_share, new_voter_margin.
3. **Rank orientation**: highest vote share → rank 1; largest new-voter margin → rank N.
4. **Raking** conserves each 2014 ward's total electorate (±0).
5. **Crosswalk** conserves citywide electorate; area weights per sub sum to 1.
6. **Backtest join**: ran_for_reelection / elected_Y correct on a known ward.
7. **Integration** on real data: expected row counts per year, `defeatability_100` ∈
   [0,100], no nulls in required fields for non-`no_prior_result` rows.

## Known follow-ups (not blockers)

- By-election incumbents crossing the 2018 boundary need the crosswalk on their
  by-election ward; handled when by-election data lands, with a flagged reduced score
  only if subdivision electorate is missing for that by-election.
- Differential per-ward voters'-list churn remains an uncontrolled confound in the
  growth term (documented limitation, per ADR 0001).

---

# Phase 2 — Predictive validation (analysis layer)

Status: **implemented**. Two disciplined analyses on top of the built index; the
faithful CDI (ADR 0001) is untouched — this is a separate `analysis` layer.

## Evaluation protocol (both items)

- **Unit**: ranked runners (the per-year pools) — n=154, 18 defeats; 122 / 7 ex-2018.
- **LOO-election-out CV**: hold out one election, fit on the other four, predict the
  held-out one; **pool the out-of-fold predictions across all five folds, then compute
  one metric** (per-fold AUC is meaningless when a fold has ~1 defeat). A *fixed-formula*
  index (no fitted parameters) is scored on the full sample; only *fitted* choices
  (logistic weights, threshold cutoffs, "best component" selection) use out-of-fold
  predictions.
- **Uncertainty**: bootstrap CIs (resample incumbents, fixed seed) on every headline number.
- **2018**: dual reporting (Q5a) — kept in the binary backtest, excluded from the primary
  continuous fit (cross-era Δ is ill-defined) and shown there only as a sensitivity.

## Item 1 — component & variant comparison (binary win/lose, metric = AUC)

Variants compared: (1) equal-weight rank-sum (Matt's CDI); (2) each single component;
(3) two-signal equal-weight (elector_share + new_voter_margin, dropping the redundant
vote_share); (4) logistic(defeat ~ 3 components), out-of-fold. Plus an **operating-point
table** for the equal-weight CDI: precision / recall / F1 across `defeatability_100`
cutoffs, the Youden-J optimum, and Matt's 40 / 55 thresholds as reference. Report AUC
with bootstrap CIs. Honest prior: combination barely beats the best single component
(components are ρ≈0.91 redundant), and tuning is unlikely to beat equal-weight out-of-fold.

## Item 2 — continuous vote-delta model

- **Outcome**: `Δ vote_share = new_vote_share_Y − prior vote_share` (within-era; primary
  fit **ex-2018**).
- **Predictors**: the three CDI components as **per-year percentiles**, standardized, plus
  a **candidate-count control** (`Δ n_candidates`).
- **Two models**: full-3-predictor (for prediction — LOO-CV R² / RMSE) and 2-signal (for
  interpretable, stable coefficients given the collinearity). Report OLS coefficients + CIs,
  in-sample R², **LOO-election-out CV R² + RMSE**, and Spearman(predicted, actual).

## Data extension

Add `prior_n_candidates` and `n_candidates_Y` to `build.py`'s output (from the results
contests), so the analysis reads a single table.

## Deliverable

- `src/defeatability_index/analysis.py` — TDD'd primitives only: LOO-election folds,
  AUC + bootstrap CI, the variant scorers, an OLS+CV wrapper.
- One **Markdown report** (`docs/analysis-report.md`) for Matt: plain language, headline
  numbers, the redundancy finding, the operating-point table, the vote-delta model, and
  the honest caveats (small N, 2018 anomaly, structural-not-idiosyncratic ceiling).
- A few **PNG figures** into `figures/` (variant ROC, operating-point curve,
  predicted-vs-actual Δ).

## Non-goals

Not modifying the faithful CDI; not free-searching component weights (collinearity + N=18);
not claiming predictive power beyond what out-of-fold CV + CIs support.

---

# Phase 3 — Candidate and Opponent-field history

Status: **implemented; supported signal under the revised protocol**.

## Question and unit

Predict whether a council candidate's own earlier non-council political record and the
records of every opponent add signal for that candidate's performance. The unit is one
Candidacy, not one Contest prediction. Vote share is primary; Elected is secondary. The
analysis is predictive and does not claim that officeholding causes electoral performance.

## Ownership and evidence

- Upstream owns Person identity and in-scope election results.
- This project owns sourced external Candidacy and Office-tenure supplements, keyed only
  by upstream Person ID (ADR 0003).
- History is strictly before the council election date.
- Unresolved identities remain unresolved; name similarity never creates history.
- Headline inference is blocked while unresolved council Candidacies plausibly point to
  an earlier other-office winner. The current release has no such unresolved cases;
  unresolved earlier losing runs still limit the Prior-unsuccessful-candidate axis.

## Candidate frame

`build_candidate_history_frame(...)` attaches:

- career record: Prior officeholder, Prior unsuccessful candidate, mixed, or no observed
  record;
- Returning-councillor status and the broader Prior-elected-office-holder union, with prior
  Ward irrelevant and sitting Incumbents kept separate;
- most recent/best/mean signed Prior performance margin;
- Office breadth, Victory count, prior-loss and Candidacy counts;
- All-past-race Candidacy and Victory counts spanning council, mayor, trustee, MP, and
  MPP races;
- Office types contested/won, recency, and current-other-officeholder status;
- Candidate regime: Incumbent, challenger facing an Incumbent, Open contest, or
  Incumbent collision, with By-election status separate; and
- self-excluding Opponent-field history: strongest opponent, counts/proportions, Office
  types, wins, current officeholding, and incumbent presence.

## Pre-specified evidence test

Primary sample: completed general elections from 2010 onward on stable ward boundaries;
2006, 2018, and By-elections are separate sensitivities. The 2006 Candidacies have only a
three-year observable career window because source coverage begins in 2003 (ADR 0004).
Leave one election year out at a time.

- Baseline: year, field size, and Candidate regime.
- Simple history: baseline plus own career-record category, own most recent signed margin,
  any Prior-officeholder opponent, and strongest opponent signed margin.
- Evidence: held-out Vote-share RMSE/R², Elected Brier/log loss/AUC, Contest-clustered
  uncertainty, a within-Contest outcome-permutation null, and sign stability by election.

The simple bar supports signal only when pooled held-out prediction improves, the clustered
interval excludes no improvement, and the permutation result is outside the 5% null tail.
Election-level direction is a heterogeneity diagnostic, not an automatic veto. An open
Prior-officeholder identity gate yields `not estimable` regardless of the numerical model
result.

## Full exploration

Compare baseline, simple history, a regularized full-history model, and a flexible
tree-based ceiling model. Report model performance, regularized fold-specific effect
direction, held-out permutation importance, career-record cells, Candidate regimes,
Office combinations, 2018 sensitivity, and By-election sensitivity. Detailed findings
are hypothesis-generating unless they also pass the pre-specified bar.

## Artifacts

`run_candidate_history_study(...)` writes the candidate frame, identity audit, model and
sensitivity tables, out-of-fold predictions, feature effects/importances, evidence and
exploration reports, and figures. The current release closes the Prior-officeholder identity
gate and clears the revised historical simple bar. A production 2026 feature still waits for
a complete candidate slate.

The downstream product is a separate catalog of candidate-specific Historical hints, not a
history score or model prediction (ADR 0005). A hint must identify its own Candidate-regime and
own-history or Opponent-field trigger, historical comparison, sample size, elections represented,
effect direction, and uncertainty. Aggregate model support makes hints eligible for testing but
does not by itself authorize any individual frontend statement.

Aggregate race-history Hint triggers must use every confirmed elected-office Candidacy strictly
before the subject Contest, including unsuccessful council runs, or name one Office type
explicitly (ADR 0006). The former non-council aggregate and the conditional union that added
council history only for Returning councillors are analysis-only and cannot be tested or
published as frontend flags. Incumbency is handled through adjustment and explicit strata.

The all-past-races Victory-count audit withholds a universal flag: the pooled interval includes
zero and Incumbents show a different association. Among non-incumbent candidates who are not
Returning councillors, the per-victory slope clears the numerical gate but has no supported
dose response among prior winners. The published stratified flag is therefore binary—at least
one victory versus prior races with none—and is positive in all three primary elections. No
zero-wins or per-additional-victory hint is published. Returning-councillor Victory counts remain
withheld; the separately named Open-contest patterns are reviewed below.

## Reader-readable flag screen

An expanded 21-test batch evaluates the additional reader-readable definitions before any
publication decision. Opponent-negative comparisons require every opponent's identity history to
be resolved. Ten comparison-specific associations clear the publication gate and remain
below a 5% Benjamini-Hochberg false-discovery threshold across the batch:

- any earlier race for a non-incumbent, non-returning candidate;
- at least two earlier races for that Candidate regime;
- an unsuccessful earlier council run compared with no earlier race history;
- the same record compared with other earlier-race histories, with the opposite direction;
- signed performance margin in the most recent earlier race;
- a victory in the most recent earlier race;
- an earlier MPP race; and
- for an Incumbent, the strongest opponent's most recent earlier-race margin;
- a Returning councillor in an Open contest; and
- facing a Returning councillor in an Open contest.

The publication standard is a clear, corrected historical association that is explicitly framed
as descriptive context. It does not require each flag to retain a separate coefficient after
correlated history measures are entered together. These ten rows are therefore catalog-eligible,
although several may apply to the same candidate. The two unsuccessful-council-run comparisons
must be displayed together: historically, that record did better than no earlier race history but
worse than other earlier-race histories. In contrast, merely facing a previous unsuccessful
council candidate is method-sensitive and does not clear the family correction for Incumbents.

The two Returning-councillor rows use the `consistent_small_sample` tier. They cover only four
independent Open Contests, but both remain same-direction after removing every triggered Contest
and under within-election permutation checks. Their frontend evidence must expose the four-Contest
sample. This is a documented exception for these reviewed rows, not a universal four-Contest gate.

`historical_hint_audit.csv` contains all tested flags and their eligibility result;
`supported_historical_hints.csv` contains only evidence-backed flags and is the downstream
contract; `historical-hints-report.md` is the human-readable rendering. The catalog identifies
triggers only. Computing them against a live 2026 slate belongs to the downstream library.
`all-past-races-victory-count-report.md` records the pooled and stratified samples, effects,
uncertainty, and election-level checks behind the Victory-count decision.
`candidate-history-flag-screen-report.md` records the complete reader-readable flag batch,
including samples, adjusted effects, clustered intervals, bootstrap p-values, family-adjusted
q-values, and election-level checks.
`candidate-history-flag-approval-report.md` records the publication standard, the ten approved
screen rows, and the paired-display requirement for the council-history comparison.
`docs/research/candidate-history-watch-list-review.md` records the higher-precision bootstrap,
leave-one-Contest-out, and permutation review behind the small-sample and near-miss decisions.

# Endorsement association study

The endorsement study is separate from the faithful CDI, candidate-history prediction study, and
Historical-hint catalog. It asks, for each exact upstream Endorser, whether Recorded endorsements
historically selected candidates with greater electoral success. It does not estimate votes caused
by an Endorsement.

The primary exposure set contains confirmed positive edges in Endorser–Contest cells whose
`coverage_state` is `comprehensive_source_found`. Positive facts in partially searched cells remain
in the observation audit but not the primary comparison. Missing edges are never called opposition,
neutrality, or an unendorsed decision.

Two within-Contest comparisons are reported separately:

1. The field comparison randomly selects the same number of candidates from the exact Contests in
   which the Endorser made a primary selection.
2. The stricter Incumbency-matched comparison selects from candidates in the same Contest with the
   same incumbent, non-incumbent, or unknown-incumbency status as each recorded selection.

Both comparisons hold Election, Office, Contest, and field size fixed by construction. The second
also removes the simplest Incumbency-selection explanation, but neither controls strategic choice
on polling, fundraising, campaign quality, ideology, or private information.

`elected` is the primary outcome; Vote-share lift is the continuous secondary outcome. Per-Endorser
uncertainty uses Contest-clustered bootstrap intervals and within-Contest randomization tests.
Benjamini-Hochberg q-values correct the 18 Endorser-by-outcome tests in each comparison family. A
clear label requires at least ten informative Contests in at least two elections and q < 0.05 for
one of the two outcomes. Election-specific and leave-one-election-out estimates are stability
diagnostics rather than automatic vetoes.

`endorsement_observations.csv` retains every confirmed positive fact, its coverage eligibility,
outcome, provenance summary, and field/matched baselines. `endorser_associations.csv` contains the
per-Endorser effects, intervals, corrected tests, coverage counts, timing, and stability fields.
`endorsement-analysis-report.md` is the human-readable exploration.
