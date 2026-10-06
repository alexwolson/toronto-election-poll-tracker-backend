# How the production model responds to post-exit polls: October 6, 2026

Answers the wayfinder task [Measure how the production model responds to
post-exit polls](https://github.com/alexwolson/toronto-election-poll-tracker-backend/issues/28)
on the map [Handle Alexander's Suspended Campaign in the mayoral
forecast](https://github.com/alexwolson/toronto-election-poll-tracker-backend/issues/27).
These are scenario fits only. No ingestion, feed, release or deployment is changed.

## Findings

1. **Under today's rule, a head-to-head poll changes nothing.** The main fit drops any reading that
   omits Alexander (checked by running the real reading selection, below). If pollsters stop naming
   him, as every firm did after past exits (ticket 29), the forecast stays at 75.4 / 24.4 on
   pre-exit polls.
2. **If admitted, head-to-head polls act exactly like no-news polls.** Their win probabilities match
   the controls within 0.3 points. They say nothing about Alexander, so the model keeps him at
   8.1% of named support today and **6.7% of the ballot on election day (80%: 2.0–13.6)**. Past
   suspended candidates kept 0.05–1.3% (ticket 29).
3. **Polls that name him low are absorbed gradually.** One poll at 1% moves the model's
   estimate of his support today from 8.1% to 4.3%, and three polls move it to 2.0%. His
   election-day share falls to 3.2% after one poll and 1.1% after three. At 3% the
   three-poll figures are 4.3% today and 3.1% on election day; at 6% they are 6.8% and 5.4%.
4. **His drop raises Bradford's chances even though the polls show no change between Chow and
   Bradford.** Against the matching control, Bradford gains 3.5, 6.2 and 8.5 points with one, two
   and three polls at 1%, and 1.1, 1.8 and 3.8 points at 3%. At 6% there is no change beyond
   noise. The median Chow lead stays at +12 to +14 points throughout; all of the gain comes from a
   wider range.
5. **Why: the model treats the exit as a volatile campaign.** Its random walk has no step for a
   one-time event, so a fall from 9% to 1% within five days can only be explained as fast movement.
   The 2026 campaign's movement scale rises fivefold. The model then applies that movement to
   Chow against Bradford for the days that remain, widening the range on both sides of an unchanged
   centre.
6. **Simply adding later polls moves Chow up about 2 points** (control against baseline: Bradford
   −2.1 to −2.6). The time left falls from 22 to 11–17 days, steady polls lower the movement
   scale (0.052 to 0.043), and the gap's range at election-day support narrows. The controls
   remove this effect from the comparisons in findings 2 and 4.

## Results

Win probabilities and shares are percentages; the Chow − Bradford margin is in full-ballot points.
Ranges are central 80%. "Alexander now" is the model's estimate of his named support at the latest
poll date. Each label's suffix is the number of synthetic polls added (n1 = the Oct 9 poll; n3 =
all three).

| Scenario | Chow win | Bradford win | Chow − Bradford (80%) | Alexander on election day (80%) | Alexander now |
| --- | ---: | ---: | ---: | ---: | ---: |
| baseline | 75.4 | 24.4 | +11.6 (−11.6 to +34.2) | 6.7 (2.0–13.5) | 8.1 |
| head-to-head-n1 | 77.7 | 22.1 | +12.8 (−9.9 to +35.1) | 6.7 (2.0–13.7) | 8.1 |
| head-to-head-n2 | 78.0 | 21.8 | +12.7 (−9.7 to +35.0) | 6.7 (2.0–13.5) | 8.1 |
| head-to-head-n3 | 77.4 | 22.5 | +12.1 (−10.2 to +33.7) | 6.7 (2.0–13.6) | 8.1 |
| control-n1 | 77.6 | 22.3 | +12.6 (−10.0 to +34.7) | 6.7 (2.0–13.3) | 8.1 |
| control-n2 | 78.0 | 21.8 | +12.6 (−9.9 to +33.9) | 6.8 (2.1–13.5) | 8.2 |
| control-n3 | 77.6 | 22.2 | +12.1 (−9.6 to +33.2) | 6.9 (2.2–13.6) | 8.3 |
| alexander-6pct-n1 | 77.4 | 22.4 | +12.7 (−10.2 to +35.6) | 6.1 (1.6–12.8) | 7.4 |
| alexander-6pct-n2 | 78.6 | 21.2 | +13.8 (−9.6 to +36.6) | 5.6 (1.5–12.2) | 7.0 |
| alexander-6pct-n3 | 77.3 | 22.6 | +12.6 (−10.1 to +35.0) | 5.4 (1.4–11.7) | 6.8 |
| alexander-3pct-n1 | 76.6 | 23.4 | +13.1 (−11.6 to +37.0) | 5.0 (1.2–11.4) | 6.2 |
| alexander-3pct-n2 | 76.2 | 23.6 | +14.0 (−12.3 to +38.8) | 3.7 (0.6–9.4) | 4.9 |
| alexander-3pct-n3 | 73.9 | 26.1 | +12.4 (−13.7 to +37.9) | 3.1 (0.4–8.4) | 4.3 |
| alexander-1pct-n1 | 74.1 | 25.8 | +14.0 (−14.9 to +41.5) | 3.2 (0.4–8.8) | 4.3 |
| alexander-1pct-n2 | 71.9 | 28.1 | +14.3 (−18.8 to +44.9) | 1.6 (0.1–5.8) | 2.5 |
| alexander-1pct-n3 | 69.2 | 30.8 | +12.0 (−20.1 to +43.0) | 1.1 (0.0–4.7) | 2.0 |

Alexander's win probability is at most 0.2% in every scenario. All 16 fits pass the production
gate: 0 divergences, worst R-hat 1.0019, minimum ESS 1,740. Four needed the 0.99 retry:
head-to-head-n1 and all three 6% fits.

**Mechanism.** These are refits of the three-poll cases that also record the 2026 movement
scale and the Chow − Bradford gap at each stage, which is the feed's uncertainty breakdown
(ADR 0056). Each refit reproduces its scenario's recorded numbers exactly, since the fits are
deterministic. The stage columns give the width of the gap's 80% range in points.

| Three polls | Movement scale, log-odds per week (80%) | Today | At election-day support | Result |
| --- | ---: | ---: | ---: | ---: |
| baseline (no polls added) | 0.052 (0.025–0.090) | 12.0 | 18.7 | 45.8 |
| control | 0.043 (0.020–0.075) | 11.9 | 14.6 | 42.8 |
| head-to-head | 0.046 (0.022–0.080) | 12.1 | 15.3 | 43.8 |
| Alexander 6% | 0.065 (0.038–0.100) | 13.1 | 18.6 | 45.1 |
| Alexander 3% | 0.120 (0.087–0.163) | 15.6 | 28.2 | 51.6 |
| Alexander 1% | 0.216 (0.163–0.288) | 18.2 | 46.0 | 63.1 |

The median gap is about 12 points at every stage in every row; only the widths change.

## What could make these numbers misleading

- **Simulation noise.** The chain-to-chain error on Bradford's win probability is at most about
  0.75 points per fit. The head-to-head, 6% and one-poll 3% differences from the controls are
  inside that. The 1% series and the three-poll 3% case are well outside it.
- **Firm effects.** The synthetic polls come from Liaison, Mainstreet and Forum. All three had
  Alexander near 9–10%, so a low reading from them cannot be passed off as a house effect. Nanos
  had him at 4.0%; a low Nanos reading would be partly read as house effect, and the movement
  scale should rise less. This was not tested.
- **Speed of the fall.** The first synthetic poll comes five days after the last real Liaison poll,
  so the drop looks sudden. A decline spread over more polls and days implies less movement per
  week, and probably less widening.
- **A fixed Chow–Bradford split.** Real post-exit polls will also carry transfers. This design
  isolates the model's mechanical response; it is not a forecast of what new polls will show.
- **Paired comparisons are not truly paired.** Every fit uses the same seed, but the samplers
  follow different paths, so the differences carry the noise of two independent fits.
- **Whether the widening is wrong is a judgement for the decision ticket.** An exit is a one-time
  event, not evidence that Chow and Bradford supporters are switching faster. Still, a race that
  loses a candidate may really be less settled. Under ADR 0030, any fix to the fitted model needs a
  held-out test.

## Setup

**Inputs.** These are the production pins of `backend-2026-10-06.1`: `polling-2026-10-06.2` and
`results-2026-09-30.2`, downloaded fresh. Their manifest hashes match the ones the backend release
manifest records (`7759f602…` and `e03cea31…`), and so does every Polling asset hash. The model code
is Backend `20f4c11`, the released commit.

**Baseline.** Refitting the 14 production polls with the production settings reproduces the published
feed exactly: Chow 75.375%, Bradford 24.4125%, Alexander 0.2125%; Chow − Bradford +11.64 points
(80%: −11.60 to +34.17); Alexander 6.66% of the full ballot on election day (1.98–13.47). The
diagnostics are identical too (0 divergences, worst R-hat 1.0012, minimum ESS 3,751).

**Fits.** Every scenario uses the production joint model: seven historical campaigns, population
hyperpriors and the Dirichlet election day. It runs 4 chains, 1,000 warmup and 4,000 retained draws
per chain, seed 20260921, through the production gate (`_qualified_fit`: 0 divergences, R-hat below
1.01, ESS at least 400, one retry at target acceptance 0.99). The chain-to-chain simulation error on
Bradford's win probability is about 0.75 points per fit, so differences under about 1.5 points
between two fits are noise.

**Synthetic polls.** Each scenario appends one, two or three polls to the production campaign:

| Poll | Fieldwork ends | Days out | Firm |
| --- | --- | ---: | --- |
| 1 | Fri Oct 9 | 17 | Liaison Strategies |
| 2 | Mon Oct 12 | 14 | Mainstreet Research |
| 3 | Thu Oct 15 | 11 | Forum Research |

Each poll has an effective named base of 800, the same as the Oct 2 scenarios; the 14 real polls'
median is 780. Chow and Bradford are always at the latest average's ratio. That average is the simple
mean of the 14 modelled polls, renormalized among the three names: Chow 51.25, Bradford 39.56,
Alexander 9.19, so Chow takes 56.4% of the two. The baseline model's own current estimate of that
split is 56.7% (80%: 53.3–60.1), so the synthetic polls carry almost no news about Chow against
Bradford, and any movement comes from what they say about Alexander and from their timing.

- **Head-to-head:** Chow 56.4, Bradford 43.6; Alexander not offered.
- **Control (no news):** Alexander at the 9.19% average, Chow and Bradford at the ratio. This
  separates the effect of simply adding later polls (a shorter horizon to election day) from the
  effect of Alexander's drop.
- **Alexander at 1%, 3% and 6%:** Chow and Bradford share the rest at the ratio.

**The production rule drops a head-to-head poll (observed).** `run.py` writes a two-name reading
(Liaison, Oct 8–9, decided plus leaners, base 800) into a copy of the Polling bundle and runs the real
reading selection (`current_campaign`). With the production default (`require_full_field=True`), the
campaign is unchanged: the same 14 polls. With `require_full_field=False`, the rule the
pre-certification sensitivity refit uses, the reading enters with only Chow and Bradford offered. So
under today's rule a head-to-head poll leaves the forecast exactly at the baseline. The head-to-head
rows below admit only the new polls under the two-of-three rule. The existing sensitivity refit would
also bring in 14 pre-certification polls, which is a different question.

## Reproduction

From the Backend root, with the three releases downloaded into `<pins>/polling` and `<pins>/results`:

```bash
uv run python docs/research/alexander-post-exit-polls-2026-10-06/run.py --pins <pins> --workers 3
uv run python docs/research/alexander-post-exit-polls-2026-10-06/summarize.py
# mechanism refits (same fits; also record movement scale and gap by stage)
uv run python docs/research/alexander-post-exit-polls-2026-10-06/run.py --pins <pins> --workers 3 \
    --out docs/research/alexander-post-exit-polls-2026-10-06/mechanism --only baseline \
    --only control-n3 --only head-to-head-n3 --only alexander-1pct-n3 \
    --only alexander-3pct-n3 --only alexander-6pct-n3
```

`run.py` refuses bundles whose manifest hashes differ from the pins. It caches one JSON file per
scenario in `scenarios/`; pass `--force` to refit. `--smoke --draws 50 --warmup 50` checks the plumbing
without the gate. `scenarios/inputs.json` records the model package hashes, the average, the schedule
and the head-to-head check. `results.csv` holds every row with its diagnostics.
`scenarios/baseline-draws.npz` holds the baseline's election-day draws (`named_result`,
`full_ballot`) for the transfer-assumption view. The main 15 fits took 29 minutes with
three workers on a 14-core Mac. The six mechanism refits took 12.5 minutes.
