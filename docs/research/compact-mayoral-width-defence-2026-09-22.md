# Why the forecast is this wide, and whether any passable release is narrower (2026-09-22)

Brief (Alex, 2026-09-22 night): explain where the width of the 2026 mayoral
forecast comes from, and show in the data and modelling that no release that
would pass the gate is narrower. A finding that the width is warranted is
acceptable; it has to be defensible. No change is proposed unless it has
already passed the gate. No answer is given until the criteria below are met.

## Standard

- **Attribution** (where the width comes from): a controlled refit that removes
  or neutralizes one thing, everything else fixed, and the change in the 2026
  election-day margin variance. Research settings throughout: `dirichlet`,
  population hyperpriors, seed 20260921, target_accept 0.95, 4×(1000+1000).
- **The gate** (would a release with this change pass): the pre-registered
  held-out comparison on identical folds (39 days: 2010, 2014, 2018, 2023;
  14 days: all seven), scored by `evaluate.py` unchanged. A candidate *passes*
  if mean leader-margin CRPS is no worse than the baseline's by more than 0.10
  points at each horizon, 80% coverage is at least 3/4 and 6/7, no fold has
  more than 4 divergences, worst R-hat is below 1.02. This is the lenient bar
  (the one used for data corrections), chosen deliberately: it is the most
  favourable to a narrower candidate, so a failure under it is the stronger
  result.
- **Narrower** means the 2026 election-day margin 80% band (baseline 51 points)
  or its sd (baseline 20.9) is smaller under the full fit.
- **Claims are made only after the runs.** Every candidate's rule is in this
  note before its folds run. Results are appended under "Results" and nothing
  above that line is edited afterwards except typos and the correction log.

## Part 1: what the width consists of (attribution, from existing runs)

Baseline 2026 margin: sd 20.9 points, 80% band −15.7..+34.9 (51 wide).
Decomposed on the draws (leader minus runner-up, full-ballot points):

| Component | sd | share of variance |
|---|---|---|
| Today's polls (posterior of current support) | 6.4 | 9% |
| Movement to election day (random walk) | 10.0 | 23% |
| Election day (Dirichlet reading, precision `phi_election` × t5 mixing) | 17.3 | 68% |

Election-day scale: `phi_election` posterior 24 / 42 / 79 (q10/q50/q90). At
2026's composition the mapping is mechanical: sd 13.5 at phi 42 with mixing 1;
the t5 scale mixture and the posterior spread of phi take it to 17.3.

What sets `phi_election`, one refit each (Δ = change in election-day variance):

| Refit | phi median | Δ eday var | band |
|---|---|---|---|
| leave out 2003 | 54 | −19% | 47 |
| leave out 2006 | 41 | −1% | 50 |
| leave out 2010 | 61 | −28% | 45 |
| leave out 2014 | 37 | +6% | 55 |
| leave out 2018 | 32 | +13% | 56 |
| leave out 2022 | 41 | +3% | 52 |
| leave out 2023 | 39 | +4% | 49 |
| 2010's two withdrawn candidates folded into the pool | 69 | −40% | 43 |
| era corpus (2010 on) | 53 | −22% | 47 |
| no election scale mixture | 31 | −16% | 52 |
| prior median 10 / 160 / 640 (sigma 1.5) | 37 / 48 / 55 | +8% / −20% / −25% | 53 / 48 / 47 |
| prior sigma 0.5 at 40 | 41 | −6% | 50 |
| 2026 alone (prior only, no history) | 40 | +63% | 52 |

Reading: the modern well-polled races (2014, 2018, 2022, 2023) each pull the
precision *up*; 2010 and 2003 pull it down; 2010's pull is almost entirely its
two withdrawn-but-on-ballot candidates (Thomson, Rossi: 6–11% in the early
polls on mixed bases, 0.2% and 0.6% in the count; corrected 2026-10-06, the
shares were swapped). The prior matters moderately; with no
history at all the width would be larger, not smaller. Mechanism and sources
for 2010 in `compact-mayoral-width-source-2026-09-22.md`.

## Part 2: candidates for a narrower release, and their rules

Each is run through the gate. Already run (rules in the two earlier notes):

| Candidate | Narrows? | Gate |
|---|---|---|
| Era corpus, 2010 onward | 55 → 50 sd-equivalent band 51 → 47 | **fails** (CRPS +0.04 at 39 d under the strict rule; passes the lenient bar at both horizons: 9.39 vs 9.35, 5.67 vs 5.78 — recorded as *passes lenient, narrows by 4 points*) |
| 2010 withdrawn candidates folded | band 51 → 43 | **fails** (CRPS +0.92 at 39 d, +0.20 at 14 d) |

Correction to the era row, made before the new runs: under the strict rule of
its own note the era corpus was not adopted, but under this note's lenient bar
it passes, and it narrows the band from 51 to 47. That is a passable release
that is narrower by four points, and the defence has to say so. It is not
adopted for production because its own pre-registration said "better at both
horizons"; the point here is only what the record allows.

To run now, rules fixed here:

- **C3. Higher prior on the precision**, LogNormal(log 160, 1.5) and
  LogNormal(log 640, 1.5). Full fits exist (bands 48 and 47). Folds:
  `holdout{H}-<race>-dirichlet_phi160` and `_phi640`. Gate as above.
- **C4. Scale mixture removed** (`--fixed-election-mixing`). Full fit exists
  (band 52, sd 20.1: barely narrower). Folds `_nomix`. Gate as above.
- **C5. Final-fortnight movement rate** (`--late-movement`): shared multiplier
  `late_move ~ LogNormal(0, 0.5)` on the walk's innovation sd for the days of
  each step inside the final 14 days; `LATE_DAYS = 14` fixed, not tuned.
  Predictions from the width-source note apply: P1 identification (q10 of
  `late_move` > 1), P2 gate, P3 re-attribution reported, P4 with the 2010
  correction on top (`_late_nowd`) no worse than `_late` by more than 0.10.
  This candidate can re-attribute width from election day to movement without
  narrowing the total; whether it narrows is read from the full fit
  (`wd-late-all`), computed after the folds.

## Part 3: the reverse check

A defence of the width has to survive the other direction. From the baseline
held-out folds: coverage 4/4 at 39 days and 6/7 at 14 days against a nominal
80% (expected 3.2 and 5.6); leader-margin PITs and a KS statistic against
uniform with a simulated p-value; candidate-level KS from `evaluate.py`. If
the PITs pile up in the tails the band is too narrow; if they pile up in the
middle it is too wide. Reported as measured, either way.

---

## Results

(appended after the runs)

Runs completed 2026-09-23 early morning: 55 held-out folds (11 per candidate:
2010/2014/2018/2023 at 39 days, all seven at 14) plus the late-movement full
fit. Sampler: no fold above 4 divergences; worst R-hat 1.022 in one `phi640`
fold (a sampler-rule failure for that candidate). Comparisons by
`gate_compare.py` (`compact_mayoral/width_diagnostics/`; `gate_*.json` in the runs dir). All OBSERVED.

### Part 2 results: the gate

| Candidate | 2026 band (baseline 51) | 2026 sd (20.9) | CRPS 39 d (9.35) | CRPS 14 d (9.16) | Coverage | Gate (lenient) |
|---|---|---|---|---|---|---|
| Era corpus, 2010 on | 47 | 18.9 | 9.39 (own folds) | 5.67 vs 5.78 (own folds) | 4/4, 5/5 | passes lenient; failed its own strict rule |
| 2010 withdrawn candidates folded | 43 | 17.5 | 10.27 | 9.36 | 3/4, 6/7 | **fails** (+0.92, +0.20) |
| Prior median 160 | 48 | 19.3 | 9.50 | 9.17 | 4/4, 6/7 | **fails** (+0.15 at 39 d) |
| Prior median 640 | 47 | 18.9 | 9.64 | 9.20 | 4/4, 6/7 | **fails** (+0.29; R-hat 1.022) |
| Scale mixture removed | 52 | 20.1 | 9.41 | 9.21 | 4/4, 6/7 | passes; **not narrower** (band +1; sd −4%; lighter tails) |
| Final-fortnight movement rate | 52 | 21.2 | 9.47 | 9.36 | 4/4, 6/7 | **fails** (+0.12, +0.20); not narrower |
| Late rate + 2010 correction (P4, vs late) | 44 | — | 10.06 vs 9.47 | 9.54 vs 9.36 | 3/4, 6/7 | **fails** (+0.59, +0.18) |

Every candidate that narrows the 2026 band by more than four points fails the
gate under its most lenient form. The two candidates that pass do not narrow
it: the scale-mixture removal trades tails for shoulders (sd down 4%, 80% band
up 1 point), and the era corpus, the one narrower passable variant, narrows the
band by four points (51 → 47) and moves Chow by 1.6 points, and was rejected
under the strict rule its own pre-registration set. A defence of the width has
to say: the record allows at most about four points less, via a corpus
choice that is defensible but was not adopted, and nothing more.

### C5 results: the late-movement hypothesis

- P1 (identification): holds. `late_move` posterior 1.21 / 1.64 / 2.19
  (q10/q50/q90): the corpus does show movement in the final fortnight about 1.6
  times the campaign-average rate. But the fold that holds out 2023 puts it at
  0.44 / 0.78 / 1.32: the signal is 2023's final fortnight of polls (Bailão 13%
  → 22% → 31%) and essentially nothing else.
- P2 (gate): fails. CRPS +0.12 at 39 days, +0.20 at 14; coverage unchanged.
- P3 (re-attribution): as predicted in direction, small in size. Election-day
  sd 17.3 → 16.4 (−10% variance), movement sd 10.0 → 12.1, `phi_election`
  42 → 49; total sd 20.9 → 21.2, band 51 → 52. Re-attribution, no narrowing.
- P4 (the artifact becomes dispensable): fails. With the late rate in place,
  folding 2010's withdrawn candidates still costs 0.59 points at 39 days.

Verdict by the pre-registered rule: **H_late is not supported** (P2 and P4
fail). Late movement is real in one campaign, is not predictive across the
record, and is not what the election-day width was standing in for.

### Part 3 results: the reverse check

Baseline held-out leader-margin PITs: 39 days 0.31, 0.25, 0.87, 0.87 (n=4);
14 days 0.97, 0.19, 0.53, 0.38, 0.68, 0.70, 0.83 (n=7). Coverage 4/4 and 6/7
(nominal 3.2 and 5.6). Outer-20% tails 1/11 (nominal 2.2), middle 40% 5/11
(nominal 4.4). KS against uniform 0.37 (p 0.54) and 0.25 (p 0.68); all eleven
0.23 (p 0.55). Candidate-level PITs (n=66): KS 0.145 (p 0.12), tails 13/66
(nominal 13.2). Nothing here says the band is too narrow; the lean, if any, is
toward slightly wide at 39 days (no tail PITs in four folds), well inside what
eleven folds can distinguish.

### What the width is, as far as seven races can say

1. Sixty-eight percent of the 2026 margin variance is the election-day term:
   how far a Toronto count has landed from where the model's latent support
   stood on the eve. Its scale is set by all seven results, with the modern
   well-polled races arguing for a *higher* precision and 2010 and 2003
   arguing for a lower one; with no history at all it would be wider.
2. The largest single contributor to that term is 2010's two withdrawn
   candidates (40% of its variance). The record nonetheless needs the width
   they produce: removing them makes the forecast overconfident held out,
   with and without a faster late-movement rate.
3. Late movement (2023), late collapse (2003) and late withdrawal (2010) are
   the events the term absorbs. A model that gives the walk a faster final
   fortnight moves a tenth of the variance into movement and predicts worse.
   With seven results, the term cannot be decomposed further than that.
4. Calibration is consistent with the width as published, at both horizons.

No change is proposed.

---

## Pre-registered check: the denominator rank (written before the run, 2026-09-23)

The corpus rule picks one reading per same-sample group by rank
decided-plus-leaners, then decided-only, then all-respondents. It was stated,
never tested. Alex chose to keep it and asked that it be checked before the
Ipsos re-add release.

**Candidate:** the reversed rank, all-respondents first, then decided-plus-leaners,
then decided-only (`--denominator-rank all_first`). Everything else fixed as in
the earlier comparisons (dirichlet, population hyperpriors, seed 20260921,
target_accept 0.95). Folds: the same as the era-rule comparison. Run names
`holdout{H}-<race>-dirichlet_allfirst`.

**Rule:** report only. The lenient gate (CRPS no worse than +0.10 at each horizon,
coverage floors, sampler health) is applied so the result is comparable with the
other candidates, but no change to the rank follows from this note; a change would
be Alex's decision on the reported numbers.


### Result (2026-09-23)

Eleven `_allfirst` folds, at most 3 divergences, worst R-hat 1.008. Versus the
current rank on the shared folds: CRPS 9.35 → 9.46 at 39 days (+0.11, just over
the lenient tolerance), 9.16 → 8.83 at 14 days (−0.33); coverage unchanged (4/4,
6/7); mean band width 45 → 42 and 47 → 43. By the pre-registered rule this is
report-only and the rank is unchanged. Reading: all-respondents readings,
renormalised, are slightly sharper late and slightly worse early, consistent with
undecideds breaking unevenly early in a campaign; not decisive either way.
