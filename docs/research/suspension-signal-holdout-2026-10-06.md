# Suspended Campaign signal: pre-registered held-out test

October 6, 2026. Task for backend issue 43, "Test a fitted Suspended Campaign signal against the
held-out record". The design, order and pass rules were decided in issue 31, "Decide how
post-exit polls enter the current fit", and are written out in issue 43's body. This note adds only
the implementation readings below. They were fixed and committed before any fold ran. Nothing
here changes a feed, release or deployment.

## Implementation readings (fixed before any run)

1. **Where the signal acts (S1).**
   - The kept fraction multiplies the suspended candidate's latent named support on election day,
     before the Dirichlet election-day reading (`model.py`, `election_support_suspended`).
   - The freed share goes to the other named candidates in proportion to their support.
   - The residual pool is modelled separately in the compact model (its own logit, independent of
     the named composition), so it keeps its fitted share.
   - The difference from a full-ballot reallocation is the pool's proportional slice of the freed
     share. It cannot move the named margin or the winner.
2. **No poll-level hook is needed.** No modelled reading dated on or after a suspension names the
   suspended candidate. In 2023, Forum's June 23 decided reading, the one selected, leaves Davis
   blank. `check_no_post_suspension_offer` asserts this in every S1 fit.
3. **Cutoff.**
   - A campaign whose result is observed uses its election day as the cutoff, so all its
     suspensions apply.
   - The held-out campaign at horizon H uses election day minus H days.
   - In these folds the signal therefore fires only for Thomson in 2010 at 14 days (27 days out).
     Rossi (12), Davis (6) and Mammoliti (2) fall after every cutoff, and nothing fires at 39 days.
4. **2026 gets no signal inside these fits.** The table holds the ten recorded historical cases.
   The 2026 forecast every fit carries stays sealed and is not part of the decision.
5. **S1 prior.**
   - One shared kept fraction: `log keep_fraction ~ Normal(mu, sigma)`, where mu and sigma are the
     mean and sample standard deviation (n−1) of log kept fractions over the non-Toronto rows that
     have a positive last share.
   - The values come from five cases: mu = −1.5172, sigma = 0.1277, median 0.219, 80% 0.186–0.258.
   - The draw is capped at 1.
6. **S2.**
   - The fits are the baseline's.
   - For a held-out campaign with a suspension known at its cutoff, each election-day named draw is
     multiplied by a kept fraction drawn from the table's log-normal (NumPy seed 20260921), with
     Toronto 2010's rows excluded when 2010 is held out.
   - For the 2010 fold that is the same five cases as the S1 prior. With all seven usable cases
     (production use): mu = −1.8382, sigma = 0.7132, median 0.159.
   - Folds with no suspension known at the cutoff are the baseline fold unchanged.
7. **Kept fraction per case.**
   - It is the final share divided by the last pre-suspension poll share.
   - "Last" means the poll with the latest fieldwork end before the announcement. Within that
     poll, the reading follows ADR 0057's denominator rank (decided-plus-leaners, then decided,
     then all respondents); turnout screens rank last.
   - A last share of 0, or no poll, gives no ratio. That excludes Davis (Forum June 9, 0%),
     Mammoliti (Forum June 23, 0%; the 1% was June 9) and Bigger (no poll).
   - Calgary's last poll is Léger (fieldwork to Oct 11, published Oct 14), not Ipsos (to Oct 6).
     Fortier's is the 5% decided figure, not 3% of all respondents.
   - Table: `data/raw/elections/mayoral_suspended_campaigns.csv`, with a source per row from the
     issue 29 record.
8. **Settings.**
   - The 2026-09-22 comparison's settings: `run_holdouts.sh` with variant `dirichlet`, population
     hyperpriors, seed 20260921, target acceptance 0.95, 4×(1000+1000), corpus `all`, and
     `evaluate.fold_metrics` unchanged.
   - S1 adds `--suspension-signal joint` (run suffix `_joint`).
   - The baseline is re-run in this session on data repo `main` c7c965e, which includes Ipsos Reid
     Sept 24–26, 2010.
   - The decision is computed by `suspension_compare.py`.
9. **Known caveat, recorded before the runs.** The five-case prior is tight (sd 0.13 in logs), and
   Thomson kept 0.033, far below it. S1's estimate will therefore sit near the prior. Any value in
   the recorded range (0.03–0.25) removes most of the penalty Thomson's and Rossi's collapse puts on
   the election-day term, and that relief is the mechanism under test.
10. **Pre-existing state.** Two research tests fail on `origin/main` before any change here
    (`test_current_2026_*`). They pin an older 2026 poll list, and the 2026 polls do not enter the
    held-out folds.

**Expectation, from issue 43, recorded beforehand (INFERRED).** S1 fails rule 1 at both horizons.

## Input correction before the decision of record (2026-10-06, 20:50 UTC)

The first sweep (runs `runs/`, 20:15–20:42 UTC) read the 2026 campaign from a stale local
hydrate: 8 polls from the Sept 23 archive instead of the 14 in production. Every fold fits 2026
jointly with the history, so the shared scales and fold scores depend on it. Baseline and S1 used
the same stale input, so that comparison was internally consistent.

The first sweep's verdict was S1 failing rule 1 (+0.12 at 39 days, +0.19 at 14) and S2 passing.
The S1 failure at 39 days is narrow, so the sweep was rerun with the production 2026 inputs:
`polls.csv` and `mayoral_candidates.json` from `polling-2026-10-06.2` and `results-2026-09-30.2`,
the pins of `backend-2026-10-06.1`.

**Committed before the rerun:** the rerun is the decision of record, whatever it shows. Both
sweeps are reported.

## Results (appended after the runs)

All OBSERVED. CRPS is the mean leader-margin CRPS in points; coverage counts folds whose
80% band holds the true margin. Full fold tables: `compare.txt` and `compare-v2.txt` in the
session's runs (untracked, like earlier runs). Every fold sampled cleanly: at most 3 divergences,
worst R-hat 1.0184.

**Sweep 2, the decision of record (production 2026 inputs, 20:43–21:11 UTC).** The baseline
reproduces the Ipsos Reid ticket's held-out record fold for fold (14 days: 9.27).

| | Baseline | S1 (joint) | S2 (forecast side) |
|---|---|---|---|
| 39 days: CRPS / coverage | 9.40 / 4 of 4 | 9.39 / 3 of 4 (2023 lost, +29.6 vs band top +29.3) | 9.40 / 4 of 4 |
| 14 days: CRPS / coverage | 9.27 / 6 of 7 | 9.28 / 6 of 7 | 9.31 / 6 of 7 |
| Candidate KS, 39 / 14 days | 0.208 / 0.105 | 0.249 / 0.187 | 0.208 / 0.121 |
| `phi_election` per fold | 34–71 | 66–108 | as baseline |

**Verdict by the pre-registered rule: S1 passes all three rules and is adopted.** S2 also
passes, but it is consulted only if S1 fails.

**Sweep 1 (stale 8-poll 2026 input, superseded but reported).**
- Baseline: 9.16 at 39 days, 9.20 at 14.
- S1: 9.28 and 9.39, failing rule 1 at both horizons (+0.12, +0.19).
- S2: 9.16 and 9.24, passing.

**What the two sweeps say together (critique).**
- The S1-minus-baseline difference moved by 0.13 points at 39 days and 0.18 at 14 between two
  sweeps that differ only in the 2026 campaign's inputs, which do not bear on the held-out
  question. That is larger than the rule's 0.10 tolerance. The test does not resolve S1 from the
  baseline at its own resolution: under one input S1 is detectably worse, under the other
  indistinguishable.
- Seed variation was not measured. The rule did not call for it, and adding it after seeing a
  verdict would be a fork.
- **Consistent across both sweeps:**
  - S1 roughly doubles `phi_election`, which narrows the election-day range, as in the 2026-09-22
    fold-in correction.
  - Candidate calibration is worse under S1 (KS +0.04 and +0.08 in sweep 2; +0.03 and +0.08 in
    sweep 1).
  - The probability given to the actual winner is better under S1 (−log P 0.281 vs 0.336 at 39
    days).
- **The kept fraction is the prior, not something learned from 2010.** The posterior is 0.212
  (80% 0.181–0.249) against a prior median of 0.219. Thomson's 0.033 barely moves it.
- **The expectation recorded beforehand (S1 fails rule 1 at both horizons)** held in sweep 1 and
  not in the sweep of record.

## 2026 consequence (report item; matched full fits, not part of the decision)

The research harness was run on today's inputs: the data-repo corpus with Ipsos Reid 2010, the 14
production polls, 4×(1000+4000), seed 20260921. S1 applies Alexander's suspension (Oct 6) to 2026
through `--current-suspension`.

| | Baseline | S1 |
|---|---|---|
| Alexander's election-day share (full ballot), median (80%) | 6.6 (1.9–13.6) | 1.1 (0.1–3.6) |
| Chow / Bradford / Alexander win | 75.5 / 24.3 / 0.2 | 80.3 / 19.7 / 0.0 |
| Chow−Bradford named margin, median (80%) | +12.9 (−12.8 to +37.0) | +13.6 (−8.0 to +34.6) |
| `phi_election` mean | 46.5 | 80.6 |
| Diagnostics | 1 divergence, R-hat 1.0009 | 0 divergences, R-hat 1.0007 |

S1 moves Chow's win probability up about 5 points. The cause is the narrower election-day term
(the 2026-09-22 width finding), not anything about where Alexander's voters go.

**S2 on the production fit, for reference (not adopted).** `backend-2026-10-06.1` was refit at
`20f4c11` from its pins. It reproduces the published 75.375 / 24.4125 / 0.2125 exactly (0
divergences, worst R-hat 1.001208). Applying S2 with all seven usable cases (median kept fraction
0.159):
- Alexander's share goes from 6.7 (2.0–13.5) to 1.0 (0.2–3.3).
- The win probabilities become 75.5 / 24.5 / 0.0. The Chow–Bradford split is unchanged.

## Seed-replicate test (issue 45, "Run the seed-replicate test of the Suspended Campaign signal")

The maintainer held the verdict above for an explicit decision in issue 44, "Decide whether to adopt
the joint Suspended Campaign signal". That decision called for more evidence, with a rule fixed
before any run and an outcome that binds. The rule is issue 45's body:
- five paired seeds;
- horizons of 20 and 14 days, with 39 days neither run nor reported;
- CRPS averaged across the seeds;
- a fold counts as covered in 3 of the 5 seeds;
- sampling checked on every fit;
- the order S1, then S2, then neither.

This section adds only the implementation readings and the expected result. Both were committed
before any new fold ran.

### Implementation readings (fixed before any new fold)

1. **Layout.**
   - Each seed's folds sit in `<runs>/seed<N>/`, named as `run_holdouts.sh` names them.
   - The seed is passed through `fit.py --seed`, and S1 uses `--suspension-signal joint`.
   - Every other setting is the run of record's: `dirichlet`, population hyperpriors, corpus
     `all`, Gaussian innovations, target acceptance 0.95, 4×(1000+1000).
   - `suspension_replicates.check_run_config` asserts each run's recorded seed, arm and settings
     before its metrics are read.
2. **Reuse.**
   - Seed 20260921's 14-day folds (baseline and S1) are sweep 2's runs, copied out of
     `/private/tmp`.
   - Setup check: the baseline 14-day `toronto_2010` fold was re-run at seed 20260921, and its
     draws were bit-identical to the stored run (CRPS 3.77, `phi_election` 69.261).
3. **Inputs.**
   - The corpus is data repo `c7c965e`, read from a detached worktree so it can't drift mid-run.
   - `polls.csv` (sha256 `608651e2632f…`, matching sweep 2's log) and `mayoral_candidates.json`
     (`322888c6d49e…`) come from the pins of `backend-2026-10-06.1`.
4. **S2 per seed.**
   - `suspension_compare.s2_fold` gains a `seed` argument whose default is the old constant, so
     issue 43's comparison is unchanged.
   - The replicate test passes each fit's own seed.
5. **Coverage bar.** At each horizon the bar is the smaller of (number of folds − 1) and the
   baseline's covered-fold count.
6. **Where the signal fires.**
   - At both horizons, only Thomson in the 2010 fold. His exit came 27 days out; Rossi's, 12 days
     out, falls after both cutoffs.
   - 2022 has no poll 20 days out, so the harness skips it there.
   - `check_no_post_suspension_offer` passes on every campaign.
7. **Runs.**
   - One process per seed, with JAX's default threading, as in the run of record.
   - The run directories are outside every repo, in `research-runs/suspension-replicates-2026-10-06/`.
   - The decision is computed by `suspension_replicates.py`. Its rule logic is covered by
     `test_suspension_replicates.py`.

**Expected result, recorded beforehand (INFERRED).**
- **Rule 1 (CRPS):** I expect S1 to pass it at both horizons.
  - At 14 days, the run of record's difference is +0.01. I expect the five-seed mean to fall
    within about 0.05 of that.
  - At 20 days, the election-day term is a larger share of the spread than at 39 days, but the
    run of record had S1 level with the baseline at both 39 and 14 days.
- **Rule 2 (coverage) carries the risk.**
  - At 20 days, 2003 rests on one poll. Both arms' 14-day bands topped out at +22.0 and +20.0
    against an actual +35.6, so 2003 probably misses in both arms.
  - S1's 2023 band top was +29.3 at 39 days (a miss against the actual +29.6) and +31.4 at
    14 days (covered). At 20 days it may sit right at the actual. If S1 misses 2023 in three or
    more seeds while the baseline covers it, S1 covers 4 of 6 and fails.
- **Overall:** S1 is adopted, with low confidence (about 55%). The 2023 fold at 20 days decides it.

### Results (appended after the runs)

All OBSERVED.
- **The sweep:** 2026-10-06 23:06 UTC to 2026-10-07 00:08 UTC, at `1d7d0ea`, one process per seed.
- **Fits:** 130 in total, 116 new plus seed 20260921's 14 reused 14-day folds.
- **Failures:** the only fits that didn't run are 2022 at 20 days (no poll that early), as expected.
- **Load check:** the reused fold re-run under the full parallel load was again bit-identical (all
  124 saved arrays), so the reused and new folds are comparable.
- **Outputs:** the comparison is `compare-replicates.txt` and `suspension_replicates_evaluation.json`
  in `research-runs/suspension-replicates-2026-10-06/` (untracked, outside every repo).

| | Baseline | S1 (joint) | S2 (forecast side) |
|---|---|---|---|
| 20 days: CRPS averaged over seeds / covered folds | 12.20 / 4 of 6 | 12.37 / 4 of 6 | 12.29 / 4 of 6 |
| 14 days: CRPS averaged over seeds / covered folds | 9.25 / 6 of 7 | 9.30 / 6 of 7 | 9.29 / 6 of 7 |
| Variant minus baseline, 20 / 14 days | | +0.17 / +0.05 | +0.09 / +0.04 |
| Seed spread of that difference (sd), 20 / 14 days | | 0.10 / 0.03 | 0.001 / 0.002 |
| Fits breaking the sampling rule (of 65) | 1 | 1 | 1 (the baseline's) |
| `phi_election` per fit | 34–72 | 63–112 | as baseline |

- **CRPS.**
  - S1 is worse than the baseline at 20 days in every seed: +0.20, +0.14, +0.24, +0.25, +0.01.
  - By fold at 20 days: 2003 +1.20, 2006 +0.47, 2010 +0.37, 2014 −0.66, 2018 −0.37, 2023 0.00.
  - S2's difference is +0.09 at 20 days and +0.03 to +0.04 at 14 days in every seed.
- **Coverage.**
  - Every arm misses 2003 and 2006 at 20 days, in all five seeds; each of those folds has one poll.
    Every arm misses 2003 at 14 days.
  - The baseline therefore covers 4 of 6 at 20 days, and the pre-registered fallback set that
    horizon's bar at 4. 2023 is covered in every arm and seed.
- **Sampling.** No fit had more than 4 divergences. Two fits had a worst R-hat above 1.02, both at
  seed 20260925, and the same folds passed in the other four seeds:
  - the baseline's 2023 fold at 14 days (R-hat 1.0211), which S2 inherits because it is computed
    from the baseline's draws;
  - S1's 2006 fold at 20 days (1.0219).
- **The 2010 fold, the only one where the signal fires (Thomson known):** both variants are worse
  than the baseline.
  - Baseline: 3.95 at 20 days, 3.65 at 14.
  - S1: 4.32 and 3.70.
  - S2: 4.49 and 3.92.

  S2's +0.09 at 20 days is entirely this fold. Its other five 20-day folds equal the baseline.
- **Kept fraction under S1:** posterior means of 0.211–0.222 across all fits, against a prior median
  of 0.219. It is still the prior.

**Verdict as written: neither.**
- S1 fails rule 1 at 20 days (+0.17 > 0.10) and rule 3.
- S2 passes rules 1 and 2 and fails rule 3, only through the baseline fit it inherits.

**Correction and decision of record (maintainer, 2026-10-07): S2.**
- **Why rule 3 was mis-scaled.** As written, any failing fit fails the arm. About 1 fit in 90 lands
  at R-hat 1.02 or above: 2 of 130 here and 0 of 44 in issue 43's sweeps. At that rate, an arm of 11
  fits (issue 43) fails about 1 time in 9, and an arm of 65 fits fails about half the time
  (INFERRED).
- **The evidence:** the baseline, the production specification, fails the as-written bar itself
  (1 of 65). A bar the baseline cannot clear does not separate variants.
- **The correction** applies the principle the rule already used for coverage: when the baseline
  falls short, a variant passes by doing no worse, meaning no more failing fits than the baseline.
  It applies to both variants alike. S1's verdict does not change, because S1 fails rule 1
  regardless.
- **The decision of record is therefore S2.** The as-written verdict is kept and printed beside it
  (`suspension_replicates.py`, `baseline_sampling_bar`).

**The expectation recorded beforehand was wrong on rule 1.** S1 failed it at 20 days. The coverage
risk turned out to be 2006, missed by every arm, not 2023.

**Consequences, from the rule fixed in issue 43:**
- Under S2 the fitted model is unchanged.
- Any share a Post-Suspension Reading reports for Alexander is set aside.
- On the production fit with all seven usable cases (section above), Alexander's election-day share
  goes from 6.7 (2.0–13.5) to 1.0 (0.2–3.3), and the win probabilities become 75.5 / 24.5 / 0.0.
- The forecast-history chart is unchanged.

**For the ADR (findings, not rules):**
1. **The gate's resolution.**
   - The 2026 inputs alone moved the 14-day S1-minus-baseline difference by 0.18 between issue 43's
     sweeps.
   - Seeds move it by 0.10 (sd) at 20 days and 0.03 at 14 days for S1, and by about 0.002 for S2.
2. **The sampling rule's scaling with the number of fits,** and the correction above.
3. **Proportional reallocation of a suspended candidate's share made the 2010 forecast worse** at
   both horizons, as in the 2026-09-22 fold-in test. Where the freed share goes is not learned from
   the record; that question belongs to the transfer-assumption view.
