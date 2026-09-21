# Compact mayoral model: design review, replication and held-out checks

September 21, 2026. Research note; nothing here changes the published forecast
(`backend-2026-09-21.3` ships the lightweight poll-average model). Code:
`docs/research/compact_mayoral/`. Runs: `docs/research/compact-mayoral-runs-2026-09-21/`
(53 fits, all regenerated from one code version with seeded, deterministic runs).

## Why: a bird's-eye review of the heavy model

The user asked for a step back from sampler repairs to a design review: is the
integrated model's complexity appropriate for the data, and is anything unneeded
for predicting the 2026 election specifically?

**Where the heavy model's 14,048 coordinates go** (from the 2026-09-16 fit's
initial state; OBSERVED):

| Component | Coordinates | Share |
|---|---:|---:|
| Field/context process (time-varying, per offered field) | 7,340 | 52% |
| Latent support path (innovations, t-mixing, starts) | 4,440 | 32% |
| Latent unrounded source tables (Gibbs) | 1,361 | 10% |
| Per-question response nuisances | 467 | 3% |
| Firm effects | 296 | 2% |
| Route/lean effects | 131 | 1% |
| Shared hyperparameters | 11 | <0.1% |

against 236 poll questions from about 137 samples and seven election outcomes.
2014 alone carries 4,969 coordinates for 135 questions; 2026 carries 1,817.

**Where the 2026 uncertainty comes from** (4,000 draws of the 09-16 fit; OBSERVED):

| Quantity | p10 / p50 / p90 | SD |
|---|---|---:|
| Chow–Bradford margin, current support | +3.7 / +10.4 / +16.9 | 5.2 pts |
| Chow–Bradford margin, election day (named-only) | −32.1 / +10.4 / +49.0 | 32.3 pts |
| Share of election-day margin variance added after "now" | | 97.4% |

The observation layer (tables, views, routes, fields, copula) determines the
first row. The second row is almost entirely two shared scalars: the pooled
election-day discrepancy `tau_election` (posterior 0.85 ± 0.15 against a
HalfNormal(0.30) prior) and the movement hierarchy. Every historical component
that failed to converge on 09-16 (2,104 coordinates) was a table, shape or route
coordinate, components that do not carry the forecast.

The heavy model's only channel from history to 2026 is those eleven shared
scalars: candidates, firm effects and paths are campaign-specific by design.

**Runtime correction.** The heavy model's "infeasible runtime" was a hardware
artifact, not geometry. The exact production sampler ran at ~3 s/iteration on
the Mac on 09-16 (2,000 iterations in 6,461 s per chain, four chains in under
seven hours, zero divergences, zero depth hits) and passed through the same
early-warmup depth saturation seen on the RunPod A100 (iteration 50: step
0.0042, 1,023 leapfrog steps) before recovering by iteration 125. The A100 was
~300× slower per iteration (INFERRED cause: launch-bound execution of the
unrolled per-question graph; 45% GPU utilisation with one CPU core pegged).

## The compact model

Keep the part that carries the forecast; drop the observation-layer machinery.

- **Data.** Historical polls are the classification register's
  `campaign_vote_intention` readings, one canonical reading per same-sample
  dependence group (decided-plus-leaners, then decided-only, then
  all-respondents), 97 polls across seven campaigns. Reference candidates follow
  the heavy model's rule (individually polled and on the final ballot) so
  comparisons are like for like. A reading offering a subset of the reference
  enters as a conditional composition over the names it offered. Effective base
  is the reported base times the offered names' summed share; three old readings
  with no base of any kind assume 500. 2026 uses the hydrated Polling release,
  certified three-name field only: six polls (Forum 07-29 to Mainstreet 09-17).
- **Model.** Per campaign: named log-odds contrasts (Helmert basis) on a random
  walk evaluated at poll dates and election day, campaign movement scale drawn
  from the population hierarchy; one firm effect per firm; Dirichlet poll
  likelihood with the heavy precision law phi = 1/(kappa/n_eff + tau_reference²/4);
  Student-t(5) election-day discrepancy on the contrasts, drawn non-centered for
  predicted campaigns (a standard-normal shock scaled by the covariance's
  Cholesky factor); Student-t logit for the ballot share outside the reference.
  Shared scales: `m_move, omega_move, tau_firm, tau_election, kappa,
  tau_reference, mu_tail, sigma_tail`.
- **Innovations.** `gaussian` (default) or `student_t`: the heavy model's
  variance-normalized t(5) scale mixtures, mix = (df−2)/Chi2(df), one per
  random-walk step and one per firm effect.
- **Variants.** `isotropic` = one discrepancy scale for every candidate (the
  heavy specification). `leaders` = `tau_lead` for the two candidates leading the
  latest polls available at the horizon, `tau_rest` for everyone else.
- **Hyperpriors.** `population` = the heavy model's priors (joint refit).
  `borrowed` = LogNormal/Normal summaries of the 09-16 posteriors, written from
  the draws to `compact_mayoral/hyperpriors_heavy_2026-09-16.json` (2026-alone fit).

Eleven tests cover the adapter rules, the horizon truncation, model sites and
shapes under both innovation families, hyperprior provenance and synthetic
recovery. Lint is clean. Win probabilities carry a Monte Carlo standard error of
about one point at 4,000 draws; differences of that size between runs are noise.

## Results

### v1: 2026 alone with borrowed hyperpriors (isotropic, Gaussian)

Four chains × (1,000 + 1,000) in **2 seconds**; 0 divergences; worst R-hat
1.003; min ESS 1,813.

| Quantity | Compact v1 | Heavy 09-16 |
|---|---|---|
| Chow–Bradford margin now, p10/p50/p90 | +4.4 / +11.0 / +17.5 (SD 5.1) | +3.7 / +10.4 / +16.9 (SD 5.2) |
| Election-day margin (named-only) | −32.0 / +10.5 / +49.7 (SD 32.4) | −32.1 / +10.4 / +49.0 (SD 32.3) |
| Win probability Chow / Bradford / Alexander | .610 / .374 / .016 | .619 / .366 / .015 |
| Residual pool p10/p50/p90 | 2.0 / 5.4 / 14.1 | 2.0 / 5.2 / 13.1 |

The components dropped were inert for 2026, as predicted.

### v2: joint refit of all eight campaigns with population priors

Eight to nine seconds per fit. Shared-scale posteriors (mean ± SD) against the
heavy fit:

| Scale | Compact isotropic (Gaussian) | Heavy 09-16 |
|---|---|---|
| m_move | 0.089 ± 0.026 | 0.107 ± 0.032 |
| omega_move | 0.51 ± 0.19 | 0.56 ± 0.17 |
| tau_firm | 0.207 ± 0.028 | 0.164 ± 0.040 |
| tau_election | 0.794 ± 0.158 | 0.849 ± 0.153 |
| kappa | 1.56 ± 0.62 | 1.83 ± 0.48 |
| tau_reference | 0.086 ± 0.019 | 0.040 ± 0.022 |
| mu_tail | −2.82 ± 0.27 | −2.88 ± 0.29 |
| sigma_tail | 0.82 ± 0.28 | 0.85 ± 0.28 |

`tau_reference` is higher because the compact likelihood folds rounding and
multi-view noise into per-poll excess variance rather than modelling them.
2026 under v2 isotropic: Chow .631 / Bradford .359 / Alexander .010, election
margin −29.1 / +10.9 / +48.5.

**Leaders variant:** `tau_lead` 0.37 ± 0.18 versus `tau_rest` 0.88 ± 0.19. The
leaders' discrepancy scale is under half the rest's. 2026 becomes Chow .725 /
Bradford .259 / Alexander .016, election-day margin −13.1 / +10.8 / +34.6 (80%
interval 48 points wide, versus 78 isotropic).

The only coordinates with R-hat above 1.01 in any baseline run were constants
(`named_result` and `full_ballot` of observed campaigns); `fit.py` excludes
zero-variance coordinates from the diagnostics.

### Held-out elections at the 2026 horizon (39 days)

Each historical campaign's result nulled in turn; predicted from the polls
available at least 39 days before its election, leaders recomputed from those
polls; all other campaigns keep their outcomes. Only four campaigns were polled
that early (2003, 2006 and 2022 were polled only in their final weeks). Gaussian
innovations; "div" is divergent transitions out of 4,000.

| Campaign | Leaders at horizon | n | Actual margin | Isotropic p10/p50/p90 | PIT | div | Leaders p10/p50/p90 | PIT | div |
|---|---|---:|---:|---|---:|---:|---|---:|---:|
| 2010 | Ford / Smitherman | 3 | +12.1 | −8.6 / +18.9 / +45.1 | .37 | 0 | −1.1 / +19.5 / +39.2 | .32 | 6 |
| 2014 | Tory / D. Ford | 16 | +6.7 | −18.2 / +18.4 / +51.3 | .32 | 3 | −3.3 / +18.6 / +40.7 | .24 | 16 |
| 2018 | Tory / Keesmaat | 5 | +42.9 | −8.6 / +15.1 / +51.0 | .85 | 3 | +0.2 / +16.5 / +41.9 | .91 | 3 |
| 2023 | Chow / Saunders | 21 | +29.6 | −2.2 / +13.6 / +31.4 | .87 | 0 | +3.1 / +12.7 / +23.1 | .97 | 157 |

Isotropic: 80% coverage 4/4, mean probability on the actual winner 0.67.
Leaders: 80% coverage 2/4 (2018 misses by one point at the p90; 2023 clearly),
mean probability on the actual winner 0.72. Holding out 2023 collapses
`tau_lead` to 0.16 (0.38–0.40 in the other holdouts) and that fit has 157
divergences, so its numbers are numerically unreliable as well as fragile:
with seven elections the leader scale is driven by one or two of them. 2023's
leaders at 39 days were Chow and Saunders; Bailão's late surge is a "rest"
candidate becoming the runner-up, which neither variant is built to see.

### Held-out elections at 14 days

All seven campaigns have polls two weeks out. Same protocol, Gaussian innovations.

| Campaign | Leaders at horizon | n | Actual margin | Isotropic p10/p50/p90 | PIT | div | Leaders p10/p50/p90 | PIT | div |
|---|---|---:|---:|---|---:|---:|---|---:|---:|
| 2003 | Miller / Hall | 2 | +35.6 | −23.0 / +2.9 / +29.4 | .93 | 1 | −13.5 / +2.9 / +20.1 | .98 | 15 |
| 2006 | Miller / Pitfield | 2 | +27.6 | −2.8 / +45.7 / +77.2 | .28 | 1 | +17.7 / +46.8 / +67.2 | .18 | 11 |
| 2010 | Ford / Smitherman | 4 | +12.1 | −19.0 / +9.6 / +35.8 | .55 | 2 | −9.4 / +10.2 / +29.0 | .55 | 3 |
| 2014 | Tory / D. Ford | 23 | +6.7 | −26.7 / +11.5 / +45.2 | .43 | 1 | −9.7 / +11.6 / +33.8 | .36 | 2 |
| 2018 | Tory / Keesmaat | 9 | +42.9 | −13.7 / +32.5 / +65.8 | .65 | 2 | +7.3 / +31.4 / +52.1 | .76 | 3 |
| 2022 | Tory / Peñalosa | 1 | +50.3 | −0.1 / +39.2 / +67.5 | .68 | 5 | +14.1 / +39.2 / +59.4 | .75 | 3 |
| 2023 | Chow / Saunders | 34 | +29.6 | +1.9 / +16.6 / +33.2 | .85 | 3 | +7.7 / +16.1 / +25.9 | .96 | 124 |

Isotropic: 80% coverage 6/7 (miss: 2003), PITs .28–.93 spread across the
range, mean probability on the actual winner 0.73. Leaders: 80% coverage 5/7
(misses: 2003 and 2023), mean probability on the actual winner 0.79. Both
leaders-variant misses are the same phenomenon: the horizon's runner-up
(Hall 2003, Saunders 2023) collapsed and a "rest" candidate (Tory, Bailão) took
second. The variant is built to expect that from the rest, not from a leader.

**Calibration of the leader margin (actual minus predicted median), Gaussian:**

| | n | RMSE of median | Mean 80% width | Implied SD | 80% coverage |
|---|---:|---:|---:|---:|---|
| Isotropic @ 39 d | 4 | 17.4 pts | 54 pts | ~21 pts | 4/4 |
| Isotropic @ 14 d | 7 | 16.1 pts | 62 pts | ~24 pts | 6/7 |
| Leaders @ 39 d | 4 | 17.1 pts | 36 pts | ~14 pts | 2/4 |
| Leaders @ 14 d | 7 | 16.5 pts | 39 pts | ~15 pts | 5/7 |

The realized leader-margin error on this record is about 16–17 points RMSE at
both horizons. The isotropic intervals are somewhat wider than that (mildly
conservative); the leaders intervals somewhat narrower (mildly overconfident).
The two variants bracket the realized dispersion. Seven elections cannot settle
it more finely than that, and the horizon's runner-up is not always the
eventual runner-up, which is part of what a 2026 forecast must carry.

### Sensitivity: admitting the pre-certification 2026 polls

`--include-pre-certification` admits every release poll naming at least Chow and
Bradford: 13 more samples back to June 2025, each entering as a conditional
Chow-versus-Bradford composition (Alexander, Tory, Furey, Ford and others not
modelled). That conditional split drifts from 83/17 (July 2025, Tory in the
field) to 55/45 by mid-2026, so this is the crude treatment the heavy model's
field process was built to avoid. Same seeds and settings otherwise.

| | 6 polls (baseline) | 19 polls (+ pre-certification) |
|---|---|---|
| v1 2026-alone: margin now p10/p50/p90 | +4.4 / +11.0 / +17.5 | +3.1 / +9.7 / +16.5 |
| v1: 2026 weekly movement | 0.055 ± 0.028 | 0.064 ± 0.016 |
| v1: election margin | −32.0 / +10.5 / +49.7 | −31.3 / +8.8 / +49.0 |
| v1: win Chow / Bradford / Alexander | .610 / .374 / .016 | .612 / .376 / .012 |
| v2 joint isotropic: margin now | +2.0 / +11.0 / +19.9 | +1.3 / +9.9 / +18.4 |
| v2 joint isotropic: win | .631 / .359 / .010 | .625 / .365 / .010 |
| v2 joint leaders: election margin | −13.1 / +10.8 / +34.6 | −15.0 / +9.3 / +32.5 |
| v2 joint leaders: win | .725 / .259 / .016 | .697 / .288 / .015 |

Effect: current Chow–Bradford margin 1.1–1.6 points lower (the 2026 trend is
Bradford rising, and the July two-way polls sit at 54/46); Chow's win probability
within Monte Carlo error for the isotropic fits and 2.8 points lower under the
leaders variant; election-day spread unchanged; shared scales unchanged; the
2026 movement scale unchanged in mean but twice as precise. The feared inflation
of the movement scale by field changes did not occur. The 13 pre-certification
polls, even treated crudely, shift the answer by about a point; the heavy model
spent 52% of its coordinates on modelling their fields. Diagnostics clean in all
three runs. **Decision: keep the certified-field-only default** (the target is
conditional on the final ballot, the crude treatment is mis-specified in a known
direction, and the effect is inside the noise); keep the flag as a sensitivity.

### Student-t versus Gaussian innovations

The design document had proposed variance-normalized t(5) innovations "with a
Gaussian comparison" that was never run; the heavy model always used t(5), and
its scale mixtures were a documented funnel source there. `--innovations
student_t` reproduces that construction on the compact model's steps and firm
effects. Every run above was repeated under it (same seeds).

| | Gaussian | Student-t |
|---|---|---|
| v1: win Chow / Bradford / Alexander | .610 / .374 / .016 | .610 / .374 / .016 |
| v1: election margin | −32.0 / +10.5 / +49.7 | −33.8 / +9.9 / +51.0 |
| v2 isotropic: win | .631 / .359 / .010 | .634 / .354 / .012 |
| v2 isotropic: margin now (SD) | +2.0 / +11.0 / +19.9 (7.1) | +3.3 / +10.8 / +17.6 (5.7) |
| v2 isotropic: tau_election | 0.794 ± 0.158 | 0.793 ± 0.166 |
| v2 isotropic: tau_firm | 0.207 ± 0.028 | 0.172 ± 0.036 |
| v2 isotropic: m_move | 0.089 ± 0.026 | 0.097 ± 0.028 |
| v2 leaders: tau_lead / tau_rest | 0.365 / 0.881 | 0.356 / 0.876 |
| v2 leaders: win | .725 / .259 / .016 | .739 / .248 / .013 |
| v2 isotropic: divergences, worst R-hat, min ESS | 1, 1.004, 1,127 | 10, 1.003, 1,030 |
| v2 leaders: divergences, worst R-hat, min ESS | 4, 1.007, 876 | 30, 1.014, 299 |
| Held-out isotropic, coverage 39 d / 14 d | 4/4, 6/7 | 4/4, 6/7 |
| Held-out isotropic, RMSE 39 d / 14 d | 17.4 / 16.1 | 17.4 / 16.0 |
| Held-out isotropic, total divergences 39 d / 14 d | 6 / 15 | 44 / 33 |
| Held-out leaders, coverage 39 d / 14 d | 2/4, 5/7 | 2/4, 5/7 |
| Held-out leaders, total divergences 39 d / 14 d | 182 / 161 | 145 / 383 |

Heavy-tailed innovations change nothing that matters: the 2026 forecast moves
within Monte Carlo error, the election discrepancy scales are identical, and
every held-out coverage and PIT is the same to the second decimal. Their only
effects are a lower firm-effect scale (an outlying firm can carry a large effect
without inflating the population scale), movement scales about 10% higher, a
slightly tighter current-support estimate in the joint fit, and more divergent
transitions everywhere, including 233 in one held-out leaders fit. The t(5)
mixtures are the funnel source here exactly as they were in the heavy model.
**Decision: Gaussian innovations stay the default.**

### Sensitivity: naming the two minor candidates Mainstreet reported

`--name-minor-candidates` adds Sarah McVie (Mainstreet 2.5%) and Odessa Paloma
Parker (1.9%) as named 2026 candidates; the other five certified-field polls
enter as compositions conditional on the three names they reported. Same
seeds; joint isotropic Gaussian fit, and the 2026-alone borrowed fit.

| Joint fit | Three named (baseline) | Five named |
|---|---|---|
| Win Chow / Bradford / Alexander | .631 / .359 / .010 | .631 / .357 / .011 (McVie .001, Parker .001) |
| Chow–Bradford margin, election p10/p50/p90 | −29.1 / +10.9 / +48.5 | −29.2 / +10.4 / +47.5 |
| Chow current support p10/p50/p90 | 45.7 / 50.3 / 54.9 | 43.3 / 47.9 / 52.2 |
| Chow election full-ballot p10/p50/p90 | 25.9 / 45.6 / 65.2 | 23.1 / 43.2 / 62.7 |
| McVie current; election | — | 1.6 / 2.8 / 4.3; 0.8 / 2.3 / 6.0 |
| Paloma Parker current; election | — | 1.2 / 2.2 / 3.6; 0.6 / 1.8 / 4.5 |
| Residual pool, election | 2.1 / 5.6 / 13.9 | 2.2 / 5.6 / 14.2 |
| Everyone outside the top three, election | 2.1 / 5.6 / 13.9 | 6.2 / 11.0 / 21.3 |

Diagnostics clean (2 divergences, R-hat 1.003, ESS 1,032). Findings:

- The Chow–Bradford question is untouched: margin and win probabilities move
  within Monte Carlo error.
- The two minors get tight current estimates from the single poll (about
  ±1 point) and election-day ranges of roughly 1–5% each, with win
  probabilities of 0.1–0.2% (a handful of draws in which the isotropic
  log-odds discrepancy lifts a 2% candidate past the field; displayed as <1%).
- The cost is a double count. The residual-pool prior is learned from history
  as "everyone outside the polled final-ballot names" and does not shrink
  when two names are pulled out of it, so the expected vote outside the top
  three rises from 5.6% to 11.0% and each of the top three loses about two
  points of full-ballot share. Mainstreet's own reading for everyone outside
  the top three is 6.8%: the three-name baseline matches it, the five-name
  fit overshoots it.
- **Decision: keep the three-name reference.** Naming the minors adds no
  information about the race and biases the headline shares unless the pool
  prior is first made consistent with the number of named candidates (or the
  2026 pool is informed by polled "other"), which is a design change, not a
  flag. The feed lists them by name inside "Other candidates" instead.

## Reading for 2026

- Under the heavy model's own specification, reproduced here, Chow is about a
  61–63% favourite with a Chow–Bradford margin interval of roughly −30 to +49
  points. That width is the pooled, isotropic election-day discrepancy learned
  from seven outcomes, applied one-for-one to a three-way race.
- Treating the two poll leaders' discrepancy as its own exchangeable quantity
  gives about 72%, but that scale rests on one or two elections, is fragile
  under held-out testing, and the fits that push it toward zero diverge.
- The production lightweight model's ~84% sits above both. It carries a
  Chow–Bradford margin SD of about 9 points, calibrated on three elections
  using the *eventual* runner-up. The pre-registered held-out record above
  (leader minus the runner-up known at the horizon, seven elections) shows a
  realized margin RMSE of 16–17 points at five weeks, and the two research
  variants bracket that. Read literally, the production number is more
  confident than the historical record supports; the counter-argument is that
  a certified three-way field with a stable runner-up is less exposed to the
  runner-up collapses that drive the historical misses. This is a finding for
  the user to weigh, not a tuning instruction (ADR 0030).

## Not done / caveats

- No ablation of the field process or tables inside the heavy model itself;
  the "inert" claim rests on the compact replication matching the heavy
  posterior to within a point on current support and election day.
- Reference sets follow the heavy rule; for 2023 that is 15 names, five of them
  polled at ≤1%, which is exactly the isotropic specification under test.
- Conditional compositions treat withdrawn candidates' voters as redistributing
  proportionally.
- The `leaders` variant has an unresolved funnel: when a held-out campaign
  pulls `tau_lead` toward zero, the observed campaigns' path ends must match
  their results almost exactly and the sampler diverges (120–160 transitions per
  4,000 in the 2023 holdouts even after the prediction was non-centered). A
  tighter prior on `tau_lead` or a different parameterization would be the next
  attempt; not pursued without direction.
- Research code only; not wired to any feed. Untracked, like `integrated_mayoral/`.
  Run artifacts (draws) are large and must not enter git.

## How to run

From the backend root (JAX/NumPyro are not project dependencies):

```sh
uv run --no-project --with numpyro --with jax --with pytest \
  python -m pytest docs/research/compact_mayoral -q \
  --import-mode=importlib -o consider_namespace_packages=true

uv run --no-project --with numpyro --with jax python -m docs.research.compact_mayoral.fit \
  --campaigns 2026 --hyperpriors docs/research/compact_mayoral/hyperpriors_heavy_2026-09-16.json \
  --variant isotropic --out <dir>

uv run --no-project --with numpyro --with jax python -m docs.research.compact_mayoral.fit \
  --campaigns all --hyperpriors population --variant leaders --innovations student_t \
  --holdout toronto_2023 --horizon-days 39 --out <dir>

bash docs/research/compact_mayoral/run_holdouts.sh <runs_dir> "39 14" "isotropic leaders" gaussian
uv run --no-project python -m docs.research.compact_mayoral.holdouts <runs_dir>
```
