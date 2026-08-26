# Does the Council Defeatability Index predict anything? — validation notes

*Backtest of Matt Elliott's CDI on 153 incumbent-councillor races, 2006–2022
(18 actual defeats, an 12% base rate). Evaluated leave-one-election-out;
uncertainty is 95% bootstrap. The faithful CDI itself is unchanged — this only measures it.*

## Bottom line

The CDI carries a **weak but real** structural signal, and **the simple equal-weight
version is as good as it gets** — combining the three metrics barely beats the best single
one, and *fitting* weights makes out-of-sample prediction **worse than a coin flip**. It's
best read as a **screening tool** (who deserves a closer look), not a forecaster. Predicting
the *size* of an incumbent's vote change is numerically easier, but that turns out to be
**mechanical** (more candidates + regression to the mean), not the index's structural content.

## Item 1 — does it predict who loses?

The three metrics are near-duplicates (vote share ↔ elector share correlate 0.91), so as
predictors of defeat they perform almost identically, and the combined index barely leads:

| index | AUC (all years) | 95% CI |
|---|---|---|
| equal-weight CDI | 0.641 | [0.494, 0.784] |
| vote share only | 0.631 | [0.492, 0.765] |
| elector share only | 0.637 | [0.489, 0.773] |
| new-voter margin only | 0.612 | [0.474, 0.746] |
| two-signal (drop vote share) | 0.635 | [0.485, 0.781] |
| **fitted logistic (out-of-fold)** | **0.317** | [0.183, 0.461] |

![variant AUCs](../figures/item1_variant_auc.png)

Two things stand out. First, **combining doesn't help**: the full index (0.64)
is within noise of the best single component. Second, **tuning actively hurts**: a logistic
regression that *fits* the weights scores 0.32 out-of-fold — worse than chance —
because with only 18 defeats across five very different elections, the fitted relationship
flips from one election to the next. **Equal weighting is the robust choice**, which vindicates
Matt's original design.

### Where to set the alarm

Treating the score as a screen, at each cutoff:

| defeatability_100 ≥ | incumbents flagged | precision | recall | F1 |
|---|---|---|---|---|
| 40 | 92 | 15% | 78% | 0.25 |
| 55 | 69 | 17% | 67% | 0.28 |
| 60 | 65 | 18% | 67% | 0.29 |

![operating point](../figures/item1_operating_point.png)

The best trade-off (Youden-J) is a cutoff around **60**: it flags
~65 incumbents to catch **67%** of eventual losers, at
**18%** precision — roughly 1.6× the base rate.
Useful for triage, not a prediction.

## Item 2 — does it predict the *size* of the vote change?

Modelling each incumbent's Δ vote share (this election minus their prior win; excluding 2018,
where the ward map changed) is better-powered — 122 races instead of 18 defeats —
and the CDI does explain out-of-sample variance:

- full CDI + field control: **CV R² = 0.23**, Spearman(pred, actual) = 0.51
- two-signal + field control: CV R² = 0.20
- with 2018 included (sensitivity): CV R² = 0.20

**But that predictive power is mechanical, not structural.** Decomposing it:

| model | out-of-fold CV R² |
|---|---|
| candidate-count change only | 0.096 |
| + regression to the mean (prior vote share) | 0.232 |
| + ward growth | 0.228 |
| full CDI + field | 0.225 |

![decomposition](../figures/item2_decomposition.png)

Almost all of it is **(a) vote-splitting** — more candidates on the ballot mechanically lower an
incumbent's share — and **(b) regression to the mean** — a narrow prior winner tends to rebound,
a dominant one to slip. Once those are in, the CDI's *distinctive* content (support depth, ward
growth) **adds essentially nothing** (0.23 → 0.23). Standardized
coefficients (full model):

| predictor | coef (Δ vote share, SD units) | 95% CI |
|---|---|---|
| `p_vote_share` | +0.089 | [+0.017, +0.157] |
| `p_elector_share` | -0.036 | [-0.100, +0.026] |
| `p_new_voter_margin` | +0.011 | [-0.025, +0.052] |
| `delta_n_candidates` | -0.059 | [-0.099, -0.032] |

## Turning it into flags: incumbent triggers

For the 2026 watch list we surface a few **pre-specified** structural triggers (never
threshold-tuned — that overfits). To readers each is **directional only**, in the house
voice — e.g. *“↑ Raises vulnerability — won with under 35% of the vote”* — and it
extends the existing `RACE_REASON` trigger set, never a new red/yellow scheme.

**The quantified track record below stays internal (Matt-facing), and it must be read with
the caveat that it is barely calibratable:** 2026 runs on stable boundaries, so the
ex-2018 column is the honest analog — and there it rests on 0–4 defeats per trigger. The
all-years lift is largely the 2018 ward merger, which will not recur.

| trigger | reader-facing copy | all-years | ex-2018 (2026 analog) |
|---|---|---|---|
| **Narrow prior win** | won with under 35% of the vote, below the range where incumbents typically feel safe | 4/15 lost (27%, 2.3×) | 1/12 lost (8%, CI 0%–25%) |
| **Ward growth exceeds cushion** | the ward has added more electors since the win than the incumbent's margin of victory | 8/48 lost (17%, 1.4×) | 3/40 lost (8%, CI 0%–18%) |
| **High structural exposure** | among the most structurally exposed wards on the combined index | 12/69 lost (17%, 1.5×) | 4/56 lost (7%, CI 2%–14%) |

Baselines: 12% of incumbents lose across all years, 6% in a normal (ex-2018) election. So a fired trigger means *elevated attention*, not *likely to lose* — and on the 2026 analog the honest read is that these are watch-list cues, not odds.

## Honest caveats

- **Small N.** 18 defeats total (7 outside 2018); the AUC CIs above straddle 0.5. Read
  directionally, not as precise estimates.
- **2018 dominates.** The mid-cycle 44→25 ward cut produced 11 of the 18 defeats and is
  where the index looks strongest — partly because forced incumbent-vs-incumbent races *are* what
  the metrics pick up. Outside 2018 the signal is thinner.
- **Structural, not idiosyncratic.** The index measures a seat's standing exposure; it cannot see
  scandals, star challengers, or ward mergers, which drive many real upsets. That caps its ceiling
  by design.
- **Mean reversion.** The Δ-vote-share result must be read against the mechanical rebound above,
  not as independent forecasting skill.

## Recommendation

Keep the CDI as Matt built it — **equal-weight, three metrics, as a screen**. The data say don't
tune it (tuning overfits) and don't oversell it (it flags exposure, it doesn't call races). If a
sharper forecast is ever wanted, the gains would have to come from **new signal** — challenger
strength, fundraising, open-seat status — not from reweighting the three metrics we have.
