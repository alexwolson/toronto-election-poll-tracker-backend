# Pre-registration: an era rule for the historical corpus (2026-09-22)

Status: **rule written before any fit was run.** Results are appended below the
line marked "Results" only after the runs complete; nothing above that line is
edited afterwards except typos.

## What prompted this

The published forecast (`backend-2026-09-22.3`, ADR 0055 Dirichlet election-day
reading) attributes 72% of the Chow–Bradford margin's variance to election day,
i.e. to how far Toronto's counts have landed from the final polling picture.
That scale is one number learned from all seven past campaigns. Rebuilding the
raw per-race record (leaders as the polls knew them at the horizon, last three
polls that offered both, margin in points versus the count between the same two;
`raw_poll_miss.py`, rebuilt 2026-09-22, now in `compact_mayoral/width_diagnostics/`) gives:

| Race | Polls at ≥14 d | Pair | Polled | Count | Miss |
|---|---|---|---|---|---|
| 2003 | 2 | Miller vs Hall | +3 | +36 | +32 |
| 2006 | 2 | Miller vs Pitfield | +50 | +28 | −22 |
| 2010 | 4 | Ford vs Smitherman | +12 | +12 | 0 |
| 2014 | 23 | Tory vs Ford | +10 | +7 | −3 |
| 2018 | 9 | Tory vs Keesmaat | +33 | +43 | +10 |
| 2022 | 1 | Tory vs Peñalosa | +41 | +50 | +9 |
| 2023 | 34 | Chow vs Saunders | +21 | +30 | +9 |

RMSE 16.2 over seven, 7.4 over the five races with four or more polls. At 39
days (2010, 2014, 2018, 2023): misses −8, −8, +9, +10, RMSE 8.8. Two caveats
recorded honestly: 2023 scored against the count's actual pair (Chow over
Bailão by about five) is a miss of roughly −15, not +9, so the well-polled
record is nearer RMSE 9–10 than 7.4; and 2003's +32 is largely a runner-up
collapse (Hall to Tory), i.e. the polls named the wrong pair.

The Dirichlet model's held-out 80% bands at 14 days are 32–55 points wide and
2026's election-day row is 39 wide. The well-polled record would justify a band
roughly half that. The width is carried by 2003 and 2006, with 2023's late
surge the one modern contributor.

## The rule, and why it is stated on inputs

**Candidate corpus: campaigns from 2010 onward** (2010, 2014, 2018, 2022,
2023). 2003 and 2006 are dropped from the corpus entirely (polls and results).

The criterion is about the polling inputs, not the residuals, and it is fixed
here before running. OBSERVED from the audited corpus (`readings.py`, 2026-09-22):

| Race | Polls | In final 30 d | In final 14 d | Last poll | Firms |
|---|---|---|---|---|---|
| 2003 | 3 | 3 | 2 | 9 d | Environics, COMPAS, Ipsos-Reid |
| 2006 | 3 | 3 | 1 | 10 d | Decima, Léger, Ipsos Reid |
| 2010 | 9 | 6 | 5 | 4 d | Angus Reid, Nanos, Ipsos, EKOS, Pollara |
| 2014 | 29 | 10 | 6 | 2 d | Forum, Mainstreet, Nanos, Ipsos, Maple Leaf |
| 2018 | 10 | 4 | 1 | 13 d | Forum, Mainstreet, Probit |
| 2022 | 1 | 1 | 0 | 17 d | Forum |
| 2023 | 42 | 17 | 9 | 1 d | Mainstreet, Liaison, Forum, Viewpoints, Ipsos |

- 2003 and 2006 have three polls each, one per firm, from a generation of
  firms of which only Ipsos appears again in the corpus (once, in 2023). With
  two or three polls, movement after the last poll and election-day
  discrepancy are not separable within the campaign; the model books the whole
  gap to election day.
- From 2010 the corpus has multi-firm polling that reaches into the final
  fortnight in every competitive race, and from 2014 it is the firms that poll
  2026 (Forum, Mainstreet, Liaison).
- The rule is a boundary in time, not a poll-count threshold, so the thin
  modern races (2018, 2022) stay in. That is deliberate: they are the same
  polling era as 2026 and their thinness is the model's problem to handle.

Stated plainly for the record: this rule was proposed after the residuals were
seen, and the direction of its effect is known (a narrower election-day band
and a higher Chow probability). That is exactly why the decision rule below is
fixed now and why the era corpus ships first as a sensitivity, never straight
to production.

## What is held fixed

Everything except the campaign set: the `dirichlet` variant, the
`population_joint_refit` hyperpriors including `phi_election ~ LogNormal(log 40,
1.5)`, Gaussian innovations, research seed 20260921, `target_accept` 0.95, 4 chains ×
(1000 + 1000) (the settings the existing `dirichlet` folds were run with; corrected from a
mis-stated 20260922 / 0.99 before any era fit ran), the reading classification, the leader rule,
and `evaluate.py` unchanged. The current model's held-out numbers are the
`dirichlet` folds already in `compact-mayoral-runs-2026-09-22/evaluation.json`
(same settings), so only the era-corpus folds are new fits.

## Comparison

Identical folds for both corpora: at 39 days 2010, 2014, 2018, 2023; at 14
days 2010, 2014, 2018, 2022, 2023. (2003 and 2006 cannot be folds for the era
model, so they are excluded from the comparison for both; the current model's
2003 miss at 14 days is on the record above and does not count for or against
either here.)

Metrics as in `evaluate.py`: mean leader-margin CRPS (horizon pair), 80%
coverage, PIT, mean −log P(winner), candidate KS, divergences per fold, worst
R-hat.

## Decision rule (fixed before running)

The era corpus is **adopted for production** only if all of:

1. Mean CRPS on the shared folds is lower than the current model's at **both**
   horizons.
2. 80% coverage on the shared folds is at least 3/4 at 39 days and at least
   4/5 at 14 days (one fold below nominal is tolerated; two is not).
3. At most 4 divergences in any fold and worst R-hat below 1.02.

Otherwise it is **not adopted**, and it is published only as a stress-test
entry in the feed's `sensitivity` block, labelled `from-2010-corpus`. If it is
adopted, the full seven-campaign corpus becomes the stress-test entry instead,
labelled `with-2003-2006`, so readers can see what the exclusion does.

The 2026 forecast under the era corpus is computed **last**, after the
verdict, and reported here whatever the verdict.

Not covered by this test, recorded so it is not confused with it: scoring the
margin against the count's pair rather than the horizon's (the 2023 blind
spot), and a final-stretch movement rate for the walk (the structural
alternative that would also speak to 2023). Both are separate questions.

## Procedure

1. `fit.py`: a `--corpus {all,from-2010}` option that filters
   `historical_campaigns()` by election year; no other change.
2. `run_holdouts.sh`: the nine era folds into
   `compact-mayoral-runs-2026-09-22/era-holdout{39,14}-<race>-dirichlet`.
3. `evaluate.py` over both corpora on the shared folds; verdict by the rule.
4. 2026 fit with the era corpus; numbers appended.
5. If adopted: ADR, production port (the campaign filter as a named constant in
   `sampling.py`, surfaced in the feed's `model.historical_campaigns` and
   `specification`), methodology page, release, preview, promotion. If not:
   sensitivity entry only, same release path.

---

## Results

(appended after the runs)

Run 2026-09-22 late evening. Era folds: nine fits (`era` suffix `_era` on the
run names, `--corpus from-2010`), 6–7 s each, 0 divergences except 2 in the
2023 fold at 14 days, worst R-hat 1.009. Shared-fold comparison by
`era_compare.py` (`compact_mayoral/width_diagnostics/`; output saved as `era_evaluation.json` in the runs
dir). All OBSERVED.

| Metric (shared folds) | Current, 39 d | Era, 39 d | Current, 14 d | Era, 14 d |
|---|---|---|---|---|
| Mean leader-margin CRPS (pts) | 9.35 | 9.39 | 5.78 | 5.67 |
| 80% coverage | 4/4 | 4/4 | 5/5 | 5/5 |
| RMSE of median (pts) | 16.5 | 16.6 | 8.2 | 8.6 |
| Mean −log P(winner) | 0.335 | 0.316 | 0.195 | 0.169 |
| Candidate KS | 0.197 | 0.214 | 0.125 | 0.148 |
| Max divergences / fold | 2 | 0 | 1 | 2 |

Held-out band widths barely move: 44→39, 52→48, 50→51, 34→30 at 39 days;
44→39, 50→45, 55→50, 52→47, 32→30 at 14 days. Misses are the same to within a
point in every fold (2018 at 39 days still −25.6).

**Verdict by the pre-registered rule: NOT ADOPTED.** Rule 1 fails (CRPS is not
lower at both horizons: +0.04 worse at 39 days, 0.11 better at 14 days); rules
2 and 3 pass. The era corpus is a wash on the modern folds, slightly better on
the winner score, slightly worse on candidate calibration.

2026 under the era corpus, computed last (research settings): Chow 71.8 /
Bradford 27.8 (full corpus, same settings: 70.2 / 29.3); election-day margin
+11.4, 80% band −14.5..+35.6, 50 wide (full corpus +11.5, −17.1..+37.9, 55
wide); `phi_election` median 53 (full corpus 42), 80% interval 27..107 (24..79).

**What this says about the motivation.** The claim above that the election-day
width "is carried by 2003 and 2006" was INFERRED from the raw per-race table
and is wrong. Removing both races raises the election-day precision by about a
quarter and narrows 2026's band by five points. The scale is sustained by the
modern races themselves, scored over the whole composition rather than the
leader margin alone (2018 at 39 days: a 25-point miss; 2018, 2022 and 2023 at
14 days: 10-point misses), together with the `LogNormal(log 40, 1.5)` prior,
which with five or seven observations still carries weight. The raw
leader-margin table overstated how special the two thin races were because it
scores one number per race; the model's residual is every candidate's share.

Per the rule, the era corpus becomes a stress-test entry in the feed's
`sensitivity` block, labelled `from-2010-corpus`. Its effect (+1.6 points on
Chow) is small enough that cutting a release for it alone is questionable; the
recommendation is to fold the entry into the next release that would happen
anyway. The remaining open question is the structural one recorded above as
not covered here: a final-stretch movement rate, which is the only candidate
that speaks to the modern misses (2023's late surge) rather than to the thin
races.
