# Treating every 2026 poll the same way: Alexander in Other candidates (2026-10-07)

Issue: [Test treating every 2026 poll the same way, with Alexander in Other candidates](https://github.com/alexwolson/toronto-election-poll-tracker-backend/issues/48)
(map: [Handle Alexander's Suspended Campaign in the mayoral forecast](https://github.com/alexwolson/toronto-election-poll-tracker-backend/issues/27)).

## Pre-registration (committed before any held-out fit runs)

The rules below are copied verbatim from the issue body as amended on 2026-10-07, before any run.
The Forum Oct 6 poll is ingested on Polling branch `poll/forum-2026-10-06` (double-read clean:
Chow 46, Bradford 42, someone else 12, base 1,488 decided and leaning).

### Question

What does the **uniform rule** do to the forecast on current inputs, and does it pass a do-no-harm check on the held-out record? Under the uniform rule, Chow and Bradford are the named candidates in every 2026 poll, and Alexander counts with Other candidates in every poll, before and after Oct 6.

**Why this is being asked (maintainer, 2026-10-07).**
- **Polls are already returning.** The decided treatment assumes a long stretch with no polling of the field without Alexander, and that is already false. Forum polled Oct 6, the day he ended his campaign, and released it within a day.
- **The decided treatment splits polls by date.** Before Oct 6 a poll is a three-way race with Alexander named. After Oct 6 it becomes a two-way comparison with his share set aside, and S2 adjusts the forecast after the exit only.

**The same-firm pair** (decided and leaning):

| | Chow | Bradford | Alexander | Someone else | Chow's share of the two-way |
|---|---|---|---|---|---|
| Forum Sept 23 (n 1,014) | 46 | 35 | 6 | 13 | 56.8% |
| Forum Oct 6 (n 1,604; 1,488 decided and leaning) | 46 | 42 | not offered | 12 | 52.3% |

### Rules (written before any run)

**Setup**
1. Ingest Forum's Oct 6 poll through the double-read workflow. It goes to Polling as a data PR, because the poll is needed whichever rule wins.
2. Build the research inputs from current `main` in Polling and Backend, including the 2010 Ipsos Reid addition, plus that PR.

**Evidence window (clarified 2026-10-07, before any run).** Every arm uses the same 2026 samples: those production admits (from Forum Jul 29, the first poll naming the full Final Ballot field, onward), plus Post-Suspension samples naming Chow and Bradford. Today that means production's set plus Forum Oct 6.
- In this data, every sample from Jul 29 to Oct 4 names all three candidates.
- The 16 earlier samples name only Chow and Bradford, often alongside Tory and others. They stay out in every arm.
- Within a sample, every arm picks the reading production would pick: Alexander still counts when breaking a tie in favour of the fuller field.
- The test therefore isolates how Alexander is handled. Whether the uniform rule should also reach back to the pre-Alexander polls is a question for the grilling ticket, not this test.

**Current inputs: report only, no gate.** Same model specification and settings as production, seed 20260921.

| Arm | Treatment | Forum Oct 6 |
|---|---|---|
| P | Production rule as built (Forum Oct 6 is dropped because it omits Alexander) | (dropped) |
| A0 / A1 | Decided treatment: Post-Suspension Readings enter as Chow–Bradford compositions, Alexander's post-exit share is set aside, S2 applied | without / with |
| U0 / U1 | Uniform rule: Alexander folded into Other candidates in every 2026 reading; named set Chow and Bradford | without / with |

Report for each arm:
- the win probabilities;
- the median and 80% band of Chow's election-day share of the two-way;
- the median and 80% bands of the full-ballot shares and the pool;
- the posterior of the campaign-movement scale;
- the sampling diagnostics.

The question being answered: how far Forum's Oct 6 poll pulls each rule, against its 52.3%.

**Do-no-harm on the held-out record: binding.** Amended 2026-10-07 before any run: the first draft reused the seed-replicate test's baseline fits and changed only 2010.
- **Arms:** baseline (the production rule) and uniform. Both run on the same current inputs, over 13 folds (7 at 14 days, 6 at 20 days with 2022 skipped), with seeds 20260921 to 20260925.
- **The baseline is rebuilt, not reused.** The inputs now include the 2010 Ipsos Reid addition. The harness is checked first: one stored baseline fold re-run on its own pinned inputs must come out bit-identical.
- **The uniform arm** changes two things in every fit:
  - **2026 under the uniform rule.** Every fold fits 2026 jointly, so 2026 appears as production would have it: Alexander in the pool in every 2026 reading, and Forum Oct 6 admitted.
  - **The held-out campaign.** A candidate whose Suspended Campaign was announced on or before the cutoff is folded into the pool in all that campaign's readings. In practice that is only 2010 Thomson: his exit (Sept 28) is before both cutoffs; Rossi's (Oct 13) and 2023's two exits are after them.

  The other training campaigns are unchanged, because changing them failed the Sept 22 test.
- **Target:** the 2010 fold is scored on the leader margin among the remaining named candidates, and also reported against the baseline's own target.
- **Pass rules:** the Oct 6 rules as corrected on Oct 7:
  1. at each horizon, the mean leader-margin CRPS over seeds is no worse than the baseline's by more than 0.10;
  2. a fold counts as covered when 3 of 5 seeds cover it, and the uniform rule covers at least as many folds as the baseline;
  3. no more fits fail sampling (at most 4 divergences, worst R-hat below 1.02) than in the baseline.

**Target check: report only.** In the 2010 fold, does the pool's 80% band cover the actual pool share (the minor candidates plus Thomson)?

**Records.**
- A research note on a `research/uniform-rule` branch, with these rules committed before any held-out fit runs and the results committed after.
- Runs go in `research-runs/` at the workspace root.
- The verdict goes to [Decide whether every 2026 poll treats Alexander the same way](https://github.com/alexwolson/toronto-election-poll-tracker-backend/issues/49), the grilling ticket this blocks.


## Results (appended after the runs, 2026-10-07)

Runs: `research-runs/uniform-rule-2026-10-07/` (workspace root, outside every repo). Code (research,
uncommitted at run time): `uniform_rule.py`, `test_uniform_rule.py` (7 tests), `uniform_rule_compare.py`, and
three flags in `fit.py` (`--current-rule`, `--drop-current-poll`, `--fold-held-out-suspensions`). Output:
`compare.txt`, `uniform_rule_evaluation.json`. Wall time 11:43-12:59 UTC.

**Setup checks (OBSERVED).**
- Harness: seed 20260922's stored 14-day 2010 baseline fold, re-run on its own pinned inputs, came out
  bit-identical to the stored run (all 124 draw arrays equal).
- Inputs: `polls.csv` from Polling branch `poll/forum-2026-10-06` (commit d21d06f = c7c965e plus the Forum
  ingestion; the historical corpus and election tables are unchanged). It has 30 archive rows; the only
  difference from the seed-replicate pins is the Forum Oct 6 row. `mayoral_candidates.json` from
  `results-2026-09-30.2` is byte-identical to the earlier pin.
- Reading choice: for all 14 production samples, the archive row the research harness reads is the reading
  production's selection picks. Bases differ (the harness uses recruited sample size, production the
  weighted base); this is the harness's long-standing simplification and is the same in every arm.
- The rebuilt held-out baseline is bit-identical to the seed-replicate test's 65 baseline fits: the
  production rule drops Forum Oct 6, so its inputs did not change.

### Current inputs (report only)

Production settings: 4 chains x (1,000 + 4,000), target acceptance 0.95, seed 20260921, all seven past
campaigns plus 2026. A0 is P's own fit with S2 applied (identical inputs). Shares are full-ballot medians
with central 80% intervals; the two-way share is Chow / (Chow + Bradford) on election day.

| Arm | Polls | Win: Chow / Bradford / Alexander | Chow two-way | Chow | Bradford | Alexander | Pool | 2026 weekly movement (x100) | Divergences / worst R-hat |
|---|---|---|---|---|---|---|---|---|---|
| P | 14 | 75.5 / 24.3 / 0.2 | 57.0 (43.1-70.0) | 48.5 (34.9-61.0) | 36.6 (24.6-49.3) | 6.6 (1.9-13.6) | 5.6 (2.1-14.0) | 5.10 (2.48-8.73) | 1 / 1.0009 |
| A0 | 14 | 75.6 / 24.4 / 0.0 | 57.0 (43.1-70.0) | 52.0 (37.9-64.7) | 39.2 (26.4-52.7) | 1.0 (0.2-3.4) | 5.6 (2.1-14.0) | 5.10 (2.48-8.73) | 1 / 1.0009 |
| A1 | 15 | 70.4 / 29.6 / 0.0 | 55.5 (41.3-68.8) | 50.6 (36.5-63.5) | 40.5 (27.4-54.1) | 1.0 (0.2-3.4) | 5.6 (2.2-13.9) | 5.42 (2.80-8.97) | 0 / 1.0008 |
| U0 | 14 | 75.4 / 24.6 | 56.9 (43.3-69.7) | 52.7 (38.9-65.5) | 39.9 (27.2-53.1) | (in pool) | 5.6 (2.2-13.8) | 5.09 (2.27-9.38) | 2 / 1.0014 |
| U1 | 15 | 71.1 / 28.9 | 55.6 (41.9-68.3) | 51.5 (37.6-64.0) | 41.2 (28.6-54.5) | (in pool) | 5.6 (2.2-13.9) | 5.36 (2.53-9.54) | 1 / 1.0008 |

- Forum Oct 6 (two-way 52.3%) pulls Chow's two-way median by 1.5 points under the decided treatment (57.0 to
  55.5) and 1.3 under the uniform rule (56.9 to 55.6), about 30% of the way to the poll. Chow's win
  probability falls 5.2 points (A) and 4.3 (U). The 2026 movement-scale median rises about 6% (A) and 5% (U);
  the shared `m_move` is unchanged (0.083 to 0.084).
- Without Forum the two rules agree (A0 75.6 against U0 75.4). The pool is 5.6 in every arm: under the uniform
  rule the 2026 tail is drawn from the historical tail distribution, which polls do not inform, so Alexander's
  residual support is not added to it.
- Production's qualification needs zero divergences and would retry at target acceptance 0.99 with seed + 1;
  P, U0 and U1 have 1-2 divergences. No retry was run (report only).

### Held-out do-no-harm (binding)

Leader-margin CRPS in points, mean over seeds 20260921-25; covered = folds whose 80% band holds the result in
at least 3 of 5 seeds.

| Fold | 20 d baseline | 20 d uniform | 14 d baseline | 14 d uniform |
|---|---|---|---|---|
| 2003 | 23.96 | 24.06 | 23.97 | 23.79 |
| 2006 | 27.42 | 27.39 | 11.69 | 11.80 |
| 2010 (Thomson folded in the uniform arm) | 3.95 | 4.54 | 3.65 | 3.88 |
| 2014 | 5.15 | 5.13 | 5.15 | 5.13 |
| 2018 | 6.81 | 6.85 | 6.71 | 6.73 |
| 2022 | (no 20-day poll) | | 6.62 | 6.46 |
| 2023 | 5.93 | 6.01 | 6.97 | 7.10 |
| **Mean** | **12.20** | **12.33 (+0.128)** | **9.25** | **9.27 (+0.019)** |
| Covered folds | 4 of 6 | 4 of 6 | 6 of 7 | 6 of 7 |

- Per-seed uniform-minus-baseline differences: 20 days +0.149, +0.187, +0.337, +0.007, -0.041; 14 days
  -0.032, +0.168, +0.200, -0.208, -0.031.
- Sampling: 4 uniform fits fail the rule (all 2023 folds: seed 20260922 14 d, 19 divergences, R-hat 1.0174;
  20260923 14 d, R-hat 1.0295; 20260924 20 d, 5 divergences; 20260925 20 d, 97 divergences, R-hat 1.0351) against
  1 baseline fit (20260925 14 d 2023, R-hat 1.0211). Worst sites are the held-out 2023 election-day mixing and
  precision.
- 2010 scored against the baseline's own target (the margin among all five named, +12.08 against +12.10 among
  the remaining four): uniform mean CRPS 12.33 at 20 days and 9.27 at 14, the same as scored above.

**Verdict as written: FAIL.** Rule 1 fails at 20 days (+0.128 against the 0.10 tolerance; it passes at 14
days, +0.019). Rule 2 passes (4 = 4 and 6 = 6). Rule 3 fails (4 failing fits against the baseline's 1).

- Most of the 20-day difference is the 2010 fold (+0.59, which alone adds +0.098 to the mean), the same
  direction and size as S2's proportional reallocation in that fold (3.95 to 4.49). The other folds add +0.03.
- The seed spread of the 20-day difference (sd about 0.15) is larger than the tolerance.

**Target check (report only).** In every seed at both horizons, the uniform arm's 2010 pool band (about 2.0-15.8,
median about 5.9) covers the actual pool share including Thomson (4.93%).
