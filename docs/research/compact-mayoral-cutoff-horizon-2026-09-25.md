# Compact mayoral model: measuring campaign movement from the analysis cutoff

**Research date:** 2026-09-25
**Status:** closed, not adopted. The pre-registration was written before any fit and the results appended below it. Exploratory, no commitment to adopt (maintainer: "build and test with no commitment to adopt it"). **Disposition (2026-09-25):** the maintainer decided not to adopt ("Nah let's not adopt this"). ADR 0021 stands. This note is the only artifact retained: the research-package option, the production branch and the runs directory were removed.
**Question:** should the mayoral odds firm up as election day approaches when no new polls arrive? Today they cannot: the model's timeline is the poll fieldwork dates plus election day, so the run date never enters, as ADR 0021 requires.

## Design

The random walk already runs from the last poll to election day, so adding a "today" node alone would split that movement without changing its total, and the odds would not move. The only way for the calendar to matter is to drop the movement between the last poll's fieldwork and the analysis cutoff: the latest poll is treated as describing the race on the cutoff date, and only the days from the cutoff to election day carry future movement.

Implementation (research model, since removed): `CampaignPolls.cutoff_days` (days before election of the analysis cutoff, default none). In `prepare`, when set and earlier than the last poll, the cutoff becomes a latent date and the step from the last poll's date to it has zero length (for `--late-movement`, its late-days entry is zeroed too). Nothing else changes. The fit driver took `--cutoff-days`, applied to the held-out campaign or, without `--holdout`, to 2026. About 20 lines in total; re-derivable from this paragraph.

## Pre-registered test (fixed before running)

- **Model:** the production variant `dirichlet`, population hyperpriors, all campaigns, target accept 0.95, 4 × (1000 + 1000).
- **Control:** today's model, no cutoff. **Variant:** cutoff set.
- **Natural folds:** each historical campaign held out at horizons 39 and 14 days, using the polls published by then; the cutoff equals the horizon. This is exactly the real-world situation on a given run date.
- **Quiet-stretch folds:** the same, but admitting only polls at least 14 days before the horizon (`--horizon-days H+14`, cutoff H), for H = 39 and 14. This mimics two weeks with no new poll, the case the change is meant for.
- **Score:** leader-margin CRPS against the actual result (lower is better), 80 % interval coverage, PITs, divergences, per fold, via `evaluate.fold_metrics`.
- **Rule (the lenient standard from the width-defence note):** the variant is adoption-eligible only if, in **both** fold sets and at **each** horizon, its mean CRPS is no worse than the control's plus 0.10 points, its 80 % coverage count is no lower, and every fold has at most 4 divergences. Otherwise it is not adopted.
- **Reporting order:** the 2026 effect (odds today and at 14, 7 and 1 days out with today's polls) is computed only after the held-out verdict is recorded.

## Results (appended after the runs)

A correction to the spec agreed before building: the spec also described keeping the pre-cutoff movement as uncertainty about today. That version cannot shift the odds, because the random walk's total variance from the last poll to election day is the same however it is split. The tested design drops that movement, as described above.

Runs: 36 held-out fits (control and cutoff lanes, one fold per campaign, horizon and fold set, scored with `evaluate.fold_metrics` against the rule above) plus five 2026 fits; the runs directory (2.9 GB) was deleted at close. Folds with no polls by the admission date were skipped: 2003, 2006 and 2022 at 39 days; 2003, 2006, 2010 and 2022 for the 39-day quiet set; 2003, 2006 and 2022 for the 14-day quiet set.

| fold set | cutoff | folds | mean CRPS control → cutoff | 80 % coverage | max divergences (variant) | rule |
|---|---|---:|---|---|---:|---|
| natural | 39 d | 4 | 9.49 → 9.39 | 4/4 → 4/4 | 4 | pass |
| natural | 14 d | 7 | 9.16 → 9.13 | 6/7 → 6/7 | **7** (2006) | **fail** (sampler) |
| quiet (+14 d gap) | 39 d | 3 | 11.11 → 11.10 | 3/3 → **2/3** | **25** (2023) | **fail** |
| quiet (+14 d gap) | 14 d | 4 | 6.43 → 6.21 | 4/4 → 4/4 | 1 | pass |

**Verdict under the pre-registered rule: not adopted.** Predictive accuracy is never worse: CRPS improves or ties in all four cells, and most in the quiet-stretch folds (−0.22 at 14 days), which is the case the change is for. The failures are two sampler-cleanliness breaches (7 and 25 divergences against a limit of 4) and one coverage loss: in 2023 with a 15-day quiet stretch at 39 days, the variant's 80 % interval tops out at +29.0 against an actual Chow–Bailão-horizon-pair margin of +29.6, where the control's reached +29.7. Natural gaps are small (0–7 days) because historical campaigns were polled frequently, so the natural folds say little either way.

Adversarial reading: the improvements are small and rest on 3–4 folds per quiet cell; "never worse" at this n is weak evidence of "better". The coverage loss is 0.7 points at the edge of one interval. The divergence failures might clear with production's retry at higher target acceptance, but applying that after seeing the result would move the goalposts; it would need its own pre-registration.

## 2026 effect (computed after the verdict)

Current polls (8, latest fieldwork 36 days out); research model with the production variant and settings. The no-cutoff row reproduces production (Chow 73.8 %).

| analysis cutoff | Chow wins | Bradford wins | Chow–Bradford margin, 10th / 50th / 90th percentile | 80 % width |
|---|---:|---:|---|---:|
| none (today's model) | 74.0 % | 25.7 % | −13.8 / +13.1 / +38.6 | 52.5 |
| 31 days out (2026-09-25) | 74.0 % | 25.5 % | −14.3 / +12.8 / +37.8 | 52.2 |
| 14 days out | 75.6 % | 24.1 % | −12.2 / +12.7 / +36.5 | 48.7 |
| 7 days out | 76.4 % | 23.3 % | −11.3 / +12.8 / +35.9 | 47.2 |
| 1 day out | 77.1 % | 22.6 % | −10.8 / +12.7 / +35.7 | 46.5 |

With no further polls, the change would move Chow from 74 % to 77 % by election eve. The effect is small because the election-day term, not campaign movement, carries most of the width.

## Build

A production version was built and tested on a local branch (never pushed) and then deleted: `CampaignPolls.cutoff_days`, the zero-length step in `prepare`, a `with_analysis_cutoff` helper applied to the main, sensitivity and widened-field fits, and each forecast-history point carrying its publication date as its cutoff. Three tests covered it and all 23 compact-model tests passed. Turning it on would also need scheduled rebuilds, because the odds only change when the forecast is rebuilt.

## Disposition

Not adopted. Asked whether two cells being better meant it should pass, the answer recorded was: yes on accuracy (every cell's mean CRPS equal or better, two cells passing outright), but the rule required all four cells, and the two failures were sampler reliability (7 and 25 divergences) and a 0.6-point coverage miss; four individual folds were slightly worse. The open next step, if ever wanted, is a separately pre-registered re-run using production's divergence retry.
