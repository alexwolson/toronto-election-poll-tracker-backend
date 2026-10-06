# Where the election-day width comes from (2026-09-22)

Question (Alex): determine the source of the forecast's width and prove it before
saying it. Target: the 2026 Chow–Bradford election-day margin under the
production `dirichlet` model (research settings: population hyperpriors, seed
20260921, target_accept 0.95, 4×(1000+1000)). Baseline `v2-all-population-dirichlet`:
margin sd 20.9 points, 80% band 51 wide; decomposition polls-today sd 6.4,
campaign-movement 10.0, election-day 17.3 (68% of variance); `phi_election`
posterior 24/42/79 (q10/q50/q90).

## Method

Controlled refits, one change each, everything else fixed. Options added to the
research package for this: `--exclude-campaigns`, `--fixed-election-mixing`,
`--drop-candidates` (`readings.without_candidates`), plus hyperprior JSON variants.
Run names `wd-*` in `compact-mayoral-runs-2026-09-22/`; table by `width_table.py`
(`compact_mayoral/width_diagnostics/`). Election-day variance change is relative to the baseline's 17.3².

| Refit | phi q10/q50/q90 | eday sd | total sd | band | Chow | Δ eday var |
|---|---|---|---|---|---|---|
| baseline (all seven) | 24/42/79 | 17.3 | 20.9 | 51 | 70.2 | — |
| leave out 2003 | 28/54/105 | 15.5 | 19.0 | 47 | 71.8 | −19% |
| leave out 2006 | 23/41/76 | 17.2 | 21.0 | 50 | 71.2 | −1% |
| leave out 2010 | 31/61/122 | 14.6 | 18.4 | 45 | 73.0 | −28% |
| leave out 2014 | 21/37/69 | 17.8 | 21.9 | 55 | 69.0 | +6% |
| leave out 2018 | 18/32/61 | 18.4 | 22.5 | 56 | 68.5 | +13% |
| leave out 2022 | 22/41/77 | 17.6 | 21.2 | 52 | 69.2 | +3% |
| leave out 2023 | 19/39/82 | 17.6 | 20.0 | 49 | 68.4 | +4% |
| era corpus (2010 on) | 27/53/107 | 15.3 | 18.9 | 47 | 71.8 | −22% |
| no election scale mixture | 20/31/46 | 15.8 | 20.1 | 52 | 69.8 | −16% |
| prior median 10 | 21/37/68 | 17.9 | 21.3 | 53 | 70.0 | +8% |
| prior median 160 | 27/48/91 | 15.4 | 19.3 | 48 | 70.9 | −20% |
| prior median 640 | 30/55/109 | 14.9 | 18.9 | 47 | 72.0 | −25% |
| prior sigma 0.5 at 40 | 27/41/64 | 16.8 | 20.3 | 50 | 71.0 | −6% |
| 2026 alone (prior only) | 6/40/271 | 22.0 | 22.8 | 52 | 71.5 | +63% |
| **2010 with its two withdrawn candidates folded into the pool** | **37/69/139** | **13.3** | **17.5** | **43** | **73.7** | **−40%** |

## Finding (attribution only; validity tested in the section below)

The largest single source of the election-day width is 2010's two withdrawn
candidates: Sarah Thomson and Rocco Rossi withdrew after nominations closed
(September 10), on September 28 and October 13 respectively, and stayed on the
ballot. OBSERVED in the corpus: the three polls at 39–47 days offered both,
Thomson at 6.4–11% and Rossi at 6–9.7%, on three different bases (Pollara all
respondents 8/6, Angus Reid decided + leaners 11/8, Nanos decided 6.4/9.7); no
poll from 16 days on offered Thomson and none from 11 days on offered Rossi; the
count gave Thomson 0.2% and Rossi 0.6%. Outside the corpus, the last poll that
offered Thomson was Ipsos Reid, September 24–26 (about 30 days out), at 7% of all
respondents; the corpus lacks it. The reference-candidate rule
(polled in an ordinary reading and on the final ballot) admits both, so the
model carries their support to election day at roughly 7–9% each and books
their collapse, and the redistribution of that support to Ford, Smitherman and
Pantalone, as election-day discrepancy (standardized residuals about −1.7 and
−2.0 for the two, +0.7 for Ford; 2010's election mixing posterior median 0.35,
i.e. already discounted as far as the Gamma(2.5, 2.5) prior allows).

Attribution evidence that it is this and not something else about 2010: keeping 2010 and
removing only the two withdrawn candidates raises `phi_election`'s median from
42 to 69 and removes 40% of the election-day variance, more than removing 2010
altogether (28%). Corrected, 2010 becomes a race that pulls the precision up
(final three-way polls Ford 44–50 / Smitherman 35–41 / Pantalone 15–17 against
a count of 49.9 / 37.7 / 12.4 among the three). Effect on the whole forecast:
margin sd 20.9 → 17.5 (30% of total variance), band 51 → 43, Chow 70.2 → 73.7.

Sources for the dates: Global News, "Rocco Rossi drops out of Toronto mayoral
race" (2010-10-13); blogTO, "Sarah Thomson drops out of mayoral race"
(2010-09-28); Wikipedia, "2010 Toronto mayoral election" (nominations closed
September 10; both names remained on the ballot).

Corrected 2026-10-06: the nomination close (was September 9), the poll ranges
and days (was "40–45 days … 8–11% each"), and the final shares, which were
swapped. Checked against the corpus, `mayoral_outcomes.csv` (Rossi 0.616%,
Thomson 0.231%) and Wikipedia; sources for the Ipsos poll are in
`suspended-campaigns-record-2026-10-06.md` on the `research/suspended-campaigns`
branch. The fits read the data, not this prose, so no result above changes.

## What else contributes, and what does not

- 2003 (−19%): Hall's collapse (21 → 10 among named) and Tory's rise (30 → 40) in
  a final nine days with no polls. Late movement booked as discrepancy; a
  different mechanism, not a data artifact.
- The prior on `phi_election` matters moderately: a 64× change in its median
  (10 → 640) moves the posterior median from 37 to 55. With 2026 alone the
  election-day sd would be 22.0, so the seven results narrow the width, not
  widen it.
- The election-day scale mixture (t with 5 df) adds 16% of variance to 2026 but
  also lowers the precision when removed (outliers then pull it down); it is
  doing the job it was given.
- 2023 is NOT a source. Its fifteen-candidate composition supports a higher
  precision on net; removing it lowers `phi_election` (42 → 39) even though
  Bailão's +15 is the largest single residual in the corpus.
- 2014, 2018, 2022 all pull the precision up; the well-polled modern races
  argue for a narrower band, not a wider one.

## Status

No production change. Correction of record (2026-09-22, after the held-out
result below): the section above establishes *where the variance comes from*.
It does not establish that the variance is spurious; that is a separate claim
whose only test is predictive, and it was reported one step early under the
word "artifact". The held-out comparison below is that test.

---

## Pre-registered held-out comparison of the correction (written before the runs)

Alex's decision (2026-09-22 night): address the 2010 artifact, held-out comparison
first. The rule, fixed here before any fold runs:

**Correction under test.** A reference candidate who withdrew before election
day is dropped from the campaign's named set: their poll shares are removed and
the rest renormalized (n_eff scaled by the retained fraction), their count share
joins the pool, leaders are recomputed (`readings.without_candidates`). In this
corpus that is exactly Thomson and Rossi in 2010 (no other reference candidate
withdrew after a nomination deadline). Everything else as in the era-rule note:
`dirichlet`, population hyperpriors, research seed 20260921, target_accept 0.95,
4×(1000+1000), `evaluate.py` unchanged.

**Folds.** All seven campaigns at 14 days, the four with polls at 39 days;
compared with the existing `dirichlet` folds (same settings). The 2010 fold's
target changes slightly with the correction (Ford minus Smitherman among three
named instead of five: +12.2 vs +12.0); it is reported separately as well as
inside the aggregates.

**Decision rule.** This is a data correction with a factual justification that
does not depend on the scoreboard, so the bar is *no worse*, not *better*:
1. Mean leader-margin CRPS at each horizon not worse than the baseline's by
   more than 0.10 points.
2. 80% coverage at least 3/4 at 39 days and at least 6/7 at 14 days.
3. At most 4 divergences in any fold, worst R-hat below 1.02.
If all three hold, the correction is adopted for production through an ADR, as
a general rule backed by a small sourced table of withdrawals (cycle, candidate,
date, source), not a hard-coded name list. If any fails, it is not adopted and
the finding stays a documented limitation. The 2026 numbers under the
correction were already computed above (Chow 73.7) and are not part of the
decision.

Run names: `holdout{H}-<race>-dirichlet_nowd` in the 09-22 runs dir.

### Results (appended after the runs, 2026-09-22 night)

Thirteen corrected folds (`_nowd`), 8–9 s each, at most 1 divergence, worst
R-hat 1.010. Comparison by `nowd_compare.py` (`compact_mayoral/width_diagnostics/`; `nowd_evaluation.json`
in the runs dir). All OBSERVED.

| Metric | Baseline, 39 d | Corrected, 39 d | Baseline, 14 d | Corrected, 14 d |
|---|---|---|---|---|
| Mean leader-margin CRPS (pts) | 9.35 | 10.27 | 9.16 | 9.36 |
| 80% coverage | 4/4 | 3/4 | 6/7 | 6/7 |
| RMSE of median (pts) | 16.5 | 17.4 | 15.8 | 16.0 |
| Mean −log P(winner) | 0.335 | 0.293 | 0.248 | 0.209 |
| Candidate KS | 0.197 | 0.241 | 0.115 | 0.172 |

**Verdict by the pre-registered rule: NOT ADOPTED.** Rule 1 fails at both
horizons (+0.92 points at 39 days, +0.20 at 14); rules 2 and 3 pass.

Where the loss comes from, fold by fold:
- 2010 itself at 39 days: the three early polls, renormalized without Thomson
  and Rossi, put Ford at +24; the count was +12. Their supporters did not
  redistribute in proportion, they went largely to Smitherman (Thomson endorsed
  him on withdrawing). Held out, the withdrawal is a future event the forecast
  cannot foresee, and the baseline's treatment of it as election-day noise
  scores better than pretending the two never ran (CRPS 5.25 vs 7.59).
- 2023 at 39 days: the narrower band (28 wide instead of 34) no longer covers
  the count; CRPS 9.15 → 9.97.
- 2003 at 14 days: narrower band, same 32-point miss; CRPS 23.6 → 25.2.
- 2014, 2018, 2022 at 14 days improve slightly; 2010 and 2023 at 14 days worsen
  slightly.

**What this changes in the finding.** The 2010 withdrawals are still the
largest single source of the election-day width (40% of its variance). But the
held-out record says the forecast needs that width: with it removed, the model
is overconfident on the races where a late field change or late surge happened
(2003, 2023) and on 2010 itself as a prediction target. Late withdrawals and
collapses are real risks in any race, the election-day term is the only place
in the model that carries them, and 2010 is the one instance in seven that
teaches it. So the width is warranted by the record even though its largest
single source is a field change rather than a polling miss. The honest
description of the election-day row is "how far counts have landed from the
final polling picture, including late changes to the field."

Production unchanged. The two variants (`from-2010` corpus, withdrawn
candidates folded) are candidates for the feed's stress-test block in a future
release, not for the forecast. The structural question that would address
2003 and 2023 on their merits, a final-stretch movement rate, remains open and
untested.

---

## Pre-registered test of the interpretation (written before any code or run)

The held-out result above shows the width is *needed*; it does not show *what
the width represents*. The interpretation offered after the fact ("late field
changes and late surges") is a hypothesis, and it gets the same treatment as
the others: predictions written down, then the runs.

**Hypothesis H_late.** Movement in the final two weeks of a Toronto campaign is
faster than the campaign-average rate the walk extrapolates. The single-rate
walk therefore cannot produce the late surges and collapses in the record
(2023 Bailão, 2003 Hall to Tory, 2018 Tory's growing lead), so the model learns
that variance into the election-day term instead, where 2010's withdrawals
supply most of it.

**Variant.** `--late-movement`: a shared multiplier `late_move ~ LogNormal(0,
0.5)` (median 1, 80% interval about 0.5 to 2) on the walk's innovation sd for
the days of each step that fall inside the final 14 days before election day.
Nothing else changes. `LATE_DAYS = 14` is fixed here, not tuned.

**Predictions, and what each would mean.**
- P1 (identification): the posterior of `late_move` sits clearly above 1 (q10
  > 1). If not, the corpus does not show faster late movement and H_late is
  dead regardless of anything else.
- P2 (validity): held-out CRPS with the variant is no worse than the baseline
  by more than 0.10 points at each horizon, coverage at least 3/4 and 6/7, at
  most 4 divergences per fold, R-hat below 1.02. Same folds and settings as the
  two comparisons above.
- P3 (attribution shift, reported not decisive): in the 2026 decomposition the
  campaign-movement share rises and the election-day share falls, and
  `phi_election` rises.
- P4 (the artifact becomes dispensable): with the variant in place, folding
  2010's withdrawn candidates into the pool no longer worsens held-out CRPS by
  more than 0.10 at either horizon. This is the prediction that ties the
  interpretation to the 2010 finding: if the width really represents late
  movement, a model that can produce late movement should not need 2010's
  withdrawals to be well calibrated.

**Verdict rule.** H_late is *supported* only if P1, P2 and P4 all hold. P1 and
P2 without P4 means late movement is real and predictive but is not what the
election-day width was standing in for. Anything else: not supported, and the
finding stays at "the width is needed; its largest source is 2010's
withdrawals; what it represents is undetermined."

Runs: `wd-late-all` (full fit), `holdout{H}-<race>-dirichlet_late` (P2),
`holdout{H}-<race>-dirichlet_late_nowd` (P4). 2026 numbers reported last.
