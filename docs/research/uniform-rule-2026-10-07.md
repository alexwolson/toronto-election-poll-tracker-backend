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


## Results

(appended after the runs)
