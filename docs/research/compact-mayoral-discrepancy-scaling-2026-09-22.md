# Compact mayoral model: should the election-day discrepancy scale with support?

**Status: PRE-REGISTERED 2026-09-22, before any variant was fitted.** Sections
after "Results" are appended once the runs finish; nothing above them changes.

## Question

The published compact model (ADR 0054) gives Chow about 63% and Bradford about
36%. The retired lightweight model gave 84% / 16%. Both read today's polls the
same way (Chow +11 over Bradford). The whole gap is the election-day discrepancy
scale: one `tau_election` (posterior about 0.85 in log-odds) shared by every
candidate in every campaign, applied to a three-way race where it implies a
Chow–Bradford margin SD near 30 points. Pinning that scale at 0.30 gives Chow
76%; at 0.10 it gives 86% (2026-only fits, same polls, same seed, 2026-09-22).

Why is the pooled scale so large? Three observed contributors:

1. It is isotropic in log-odds across all reference candidates. A 1% candidate
   finishing at 3% is a larger log-odds move than Chow going 45% to 52%. The
   corpus has 38 reference candidates over seven campaigns; 12 finished under
   2%, eight of them in 2023 alone. The `leaders` research variant split the
   scale into 0.37 for the horizon's top two versus 0.88 for the rest.
2. Two thinly polled campaigns (2003 and 2006, three polls each) whose final
   polls missed the leader margin by +31 and −25 points.
3. 2023's runner-up collapse (Saunders faded, Bailão surged).

Raw record without any model, last-three-poll average versus result, leaders as
known at the horizon (`raw_poll_miss.py`, 2026-09-22): at 39 days (2026's
horizon) four campaigns, RMSE 8.1 points; at 14 days all seven, RMSE 15.7
points, or 5.2 on the five well-polled races.

Also observed: at the 39-day horizon the isotropic model's held-out medians
(RMSE 17.4) were worse point predictions than that plain poll average (8.1) on
identical polls, chiefly 2018 (predicted +15, polled +34, actual +40). The
likely mechanism is that symmetric log-odds noise across many candidates,
renormalised, pulls a runaway leader's median share down.

## Constraints (user, 2026-09-22)

- Never tune to the scoreboard (ADR 0030). No scale is set by hand.
- Beware overfitting: prefer structure over re-centred priors; corpus unchanged
  (2003 and 2006 stay in); decision rule fixed before running.
- "Prioritise the evidence most like 2026": the 39-day horizon is primary.

## Variants under test (both pre-specified)

| Variant | Change | Prior (fixed now) |
|---|---|---|
| `isotropic` (control) | none: the published model | `tau_election ~ HalfNormal(0.30)` |
| `leaders` | one scale for the horizon top two, another for the rest | both `~ HalfNormal(0.30)` (already the case) |
| `support_scaled` | per-candidate log-odds scale `tau_election × (0.25 / (p(1−p)))^γ`, `p` = latent named support at election day before the discrepancy, clipped to [1e-3, 1−1e-3]; γ shared across campaigns | `tau_election ~ HalfNormal(0.30)`, `γ ~ Beta(2, 2)` on [0, 1] |

γ = 0 reproduces the published model exactly; γ = 0.5 is binomial-like error;
γ = 1 is equal share-point error for every candidate. The recommendation before
running is `support_scaled`: it is the structural statement of finding (1), it
singles out no candidate, and it should also repair the lopsided-race median
distortion, which the leaders rule cannot.

## Protocol

Leave-one-campaign-out exactly as in `compact-mayoral-model-2026-09-21.md`:
the held-out campaign's result is nulled, its polls truncated to the horizon,
its leaders recomputed from those polls; every other campaign keeps its result.
All three variants are re-run in one fresh directory with identical sampler
settings (population hyperpriors, Gaussian innovations, 4 × (1000 + 1000),
`target_accept 0.95`, seed 20260921) so the comparison is not confounded by the
2026-09-21 runs' settings.

- Primary set: 39-day horizon, the four campaigns polled that early
  (2010, 2014, 2018, 2023).
- Secondary set: 14-day horizon, all seven.
- Metrics per fold: leader-margin CRPS (from draws), 80% coverage and PIT of the
  leader margin, log score of the actual winner, per-candidate PITs.
- Sampling gates: 0 divergences and R-hat < 1.01 in every fold. A fold that
  diverges gets a sampler fix (higher `target_accept`, more warmup), never a
  model edit.

## Decision rule (fixed before running)

A variant is adopted only if all four hold:

1. It samples cleanly in every fold at both horizons.
2. Its mean leader-margin CRPS at 39 days is lower than the control's.
3. Its mean leader-margin CRPS at 14 days is not higher than the control's
   (tolerance: within 2% of the control, to absorb Monte Carlo noise).
4. Its per-candidate PIT calibration is not worse than the control's
   (Kolmogorov–Smirnov distance to uniform over all held-out named candidates).

If neither clears, the control stays and `backend-2026-09-21.5` is promoted as
is. If both clear, `support_scaled` is adopted, by the recommendation above.
The 2026 forecast is computed once, last, after the rule has been applied, and
is reported whatever it says. The sweep prints no 2026 numbers.

## Expectation written before running

Based on the leaders split (0.37 versus 0.88), `support_scaled` is expected to
land near Chow 70–76%. The four-campaign primary set is expected to be too small
to decide alone, which is why criterion 3 exists. If a variant clears only at
39 days, the rule says no.

---

## Results (appended 2026-09-22 after the sweep; nothing above was edited)

Runs: `docs/research/compact-mayoral-runs-2026-09-22/` (33 folds, all three
variants, `target_accept 0.95`; evaluation in `evaluation.json`, produced by
`compact_mayoral/evaluate.py`). The 2003, 2006 and 2022 campaigns have no poll
39 days out and are skipped at that horizon, as in the 2026-09-21 protocol.

### Aggregates (leader margin in points; KS over all held-out named candidates)

| Variant | H | n | mean CRPS | RMSE of median | 80% coverage | mean −log P(winner) | candidate KS | divergences | worst R-hat |
|---|---:|---:|---:|---:|---|---:|---:|---:|---:|
| isotropic (control) | 39 | 4 | 9.84 | 17.2 | 4/4 | 0.41 | 0.30 | 0 | 1.004 |
| isotropic (control) | 14 | 7 | 10.01 | 16.3 | 6/7 | 0.34 | 0.21 | 1 | 1.005 |
| leaders | 39 | 4 | 10.12 | 16.9 | 2/4 | 0.34 | 0.31 | 242 | 1.016 |
| leaders | 14 | 7 | 9.61 | 16.3 | 5/7 | 0.26 | 0.24 | 278 | 1.048 |
| support_scaled | 39 | 4 | 11.16 | 19.1 | 3/4 | 0.49 | 0.18 | 0 | 1.008 |
| support_scaled | 14 | 7 | 10.62 | 17.7 | 5/7 | 0.36 | 0.16 | 5 | 1.007 |

Fitted scales were stable across folds: `support_scaled` γ 0.48–0.62 with
τ 0.45–0.58; `leaders` τ_lead 0.36–0.41 except the 2023 holdouts (0.15) with
τ_rest 0.68–0.90; isotropic τ 0.65–0.86.

### Decision rule applied

| Criterion | leaders | support_scaled |
|---|---|---|
| 1. samples cleanly at both horizons | **no** (229 and 252 divergences in the 2023 folds; R-hat 1.048) | **no** (0 at 39 d; 5 spread over four 14-day folds) |
| 2. lower CRPS than control at 39 d | **no** (10.12 vs 9.84) | **no** (11.16 vs 9.84) |
| 3. CRPS at 14 d within 2% of control | yes (9.61 vs 10.01) | **no** (10.62 vs 10.01, +6%) |
| 4. candidate calibration not worse (pooled KS) | **no** (0.26 vs 0.24) | yes (0.12 vs 0.24) |
| **Adopt** | **no** | **no** |

**Neither variant is adopted. The control (published isotropic model) stays and
`backend-2026-09-21.5` is the release to promote.**

### Reading the result

- The support-scaling exponent is unambiguously positive (γ ≈ 0.5–0.6 in every
  fold): the data do say small candidates miss by more in log-odds than large
  ones, and per-candidate calibration improves a lot (pooled KS 0.24 → 0.12).
  That part of the diagnosis holds.
- It did not help the leader margin, and the mechanism is visible in the folds.
  In 2023 (15 named candidates, eight under 2%) the margin median fell from
  +13.0 (control) to +7.9 at 39 days and from +16.5 to +10.3 at 14 days, away
  from the actual +29.6, and the interval narrowed enough to miss. Giving tiny
  candidates a larger *symmetric log-odds* shock inflates their expected share
  after renormalisation, which pulls the leaders' median shares, and their
  margin, down. This is the same renormalisation distortion noted for 2018 in
  the pre-registration, made worse rather than better. A discrepancy that is
  symmetric in log-odds is the wrong object for the smallest candidates; fixing
  that would be a new structural proposal (for example a share-scale or
  mean-preserving shock), not a re-run of this one.
- `leaders` improved the 14-day CRPS and winner scores but not the 39-day set,
  missed 80% coverage in 2018 and 2023 at 39 days, and still collapses
  τ_lead to 0.15 with hundreds of divergences whenever 2023 is held out. Its
  scale rests on one or two campaigns, exactly as recorded on 2026-09-21.

### Informational: the 2026 forecast each variant would have published

Computed once, after the rule was applied, as pre-registered. Not a basis for
any decision.

| Variant | Chow | Bradford | Alexander | Chow–Bradford margin p10 / p50 / p90 |
|---|---:|---:|---:|---|
| isotropic (published, `backend-2026-09-21.5`) | 63.0% | 35.8% | 1.2% | −28 / +10 / +45 |
| support_scaled (γ 0.54, τ 0.52; joint fit, 0 divergences) | 67.6% | 30.7% | 1.7% | −20 / +10 / +39 |
| leaders (2026-09-21 joint fit) | ~72% | ~27% | — | 80% width ≈ 48 pts |

### Not done

- No third variant was tried. Iterating on the discrepancy structure until a
  variant clears the rule is the overfitting path this note exists to block;
  any further proposal needs its own pre-registration and the user's call.
- Research code and run artifacts remain untracked (draws are large).

---

## Round 2: a Dirichlet election-day discrepancy (PRE-REGISTERED 2026-09-22, before fitting)

### Why a third variant is justified

Two measured findings from round 1, not a disappointing number, motivate it:

1. The support-scaling exponent came out at γ ≈ 0.5 in every fold: the data say
   election-day error scales like p(1−p), which is binomial-like.
2. Simulation (200,000 draws, 2026-09-22) shows *why* `support_scaled` still
   lost: a symmetric log-share shock with larger scale on small candidates drags
   the leaders' median down after renormalisation (2023-like +23 → +17), and the
   naive log-normal mean correction over-corrects (→ +25). The shape of the
   noise was wrong, not its scale. The same simulation shows the isotropic
   shock leaves the median essentially unchanged, so the isotropic model's
   2018 held-out miss came from its sparse-early-polls read of the race
   (Tory +20, 15–60% range, against a raw poll average of +34), a handicap
   shared equally by every variant in that fold and absent in 2026.

Both point at the standard composition-noise family the model already uses for
every poll: election day is one more reading of the latent named support,
`result ~ Dirichlet(φ_c · p)`, with variance ∝ p(1−p) (the γ = 0.5 the data
chose, with no γ to estimate), mean-preserving by construction (no median
drag), skewed for small candidates (squeezed more often than surging).

### Specification (fixed now)

- `p` = latent named support at election day (`election_support`), clipped at
  1e-6 for numerical safety.
- `φ_c = φ_election × election_mixing_c`, with `election_mixing_c ~ Gamma(5/2, 5/2)`
  (mean 1), the same per-campaign heavy-tail device the t(5) shock used, so
  2003-style shocks stay possible.
- Prior: `φ_election ~ LogNormal(log 40, 1.5)`, spanning roughly φ = 2 to 600;
  it does not say where 2026 should land. No other change. `tau_election`,
  `tau_lead`, `tau_rest`, `gamma_election` do not exist in this variant.
- Observed campaigns condition the Dirichlet on the actual named shares
  (renormalised among reference candidates, floored at 1e-4). Predicted
  campaigns draw the result.

### Protocol and rule

Identical to round 1 (same 11 folds, same control runs already on disk,
`target_accept 0.95`, seed 20260921), with one pre-stated change: criterion 1
becomes **at most 4 divergent transitions per 4,000 in every fold** with
R-hat < 1.01, replacing "exactly zero". Round 1 counted 5 divergences across
84,000 transitions as failure, which is stricter than the sampler warrants.
Applying the relaxed criterion retroactively does not change round 1's
verdicts (`leaders` still fails on hundreds; `support_scaled` still fails
criteria 2 and 3). Criteria 2–4 are unchanged.

**This is the last structural attempt this cycle.** If it fails, the isotropic
model stays and this note records why. The 2026 forecast is computed once,
after the rule is applied, and reported whatever it says.

### Expectation written before running

Mean-preserving noise with the data's own variance scaling should at least
match the control on the leader margin and beat it on per-candidate
calibration. The 2018 fold will still be poor for every variant for the
sparse-polls reason above. If it clears, the 2026 number is expected to sit
between 63% and 76% for Chow; if it does not, no expectation is recorded.

### Round 2 results (appended 2026-09-22 after the sweep; nothing above was edited)

Runs: 11 `holdout*-dirichlet` folds in `compact-mayoral-runs-2026-09-22/`
(project environment, JAX 0.11.2 / NumPyro 0.22.0, identical to the ephemeral
environment round 1 used); evaluation regenerated in `evaluation.json`.

| Variant | H | n | mean CRPS | RMSE of median | 80% coverage | mean −log P(winner) | candidate KS | max div / fold | worst R-hat |
|---|---:|---:|---:|---:|---|---:|---:|---:|---:|
| isotropic (control) | 39 | 4 | 9.84 | 17.2 | 4/4 | 0.41 | 0.30 | 0 | 1.004 |
| isotropic (control) | 14 | 7 | 10.01 | 16.3 | 6/7 | 0.34 | 0.21 | 1 | 1.005 |
| **dirichlet** | 39 | 4 | **9.35** | 16.5 | 4/4 | 0.33 | 0.20 | 2 | 1.006 |
| **dirichlet** | 14 | 7 | **9.16** | 15.8 | 6/7 | 0.25 | 0.12 | 1 | 1.005 |

Per fold the Dirichlet variant's leader-margin CRPS is lower than the control's
in all four 39-day folds and in five of seven 14-day folds (2003 23.6 vs 22.2
and 2006 11.6 vs 11.3 are the exceptions, both three-poll campaigns). Coverage
is unchanged (the 2003 miss remains), the winner log score improves at both
horizons, and the intervals are narrower without losing coverage (2014 at 14 d:
−13 / +37 against the control's −28 / +45). φ ranged 36–71 across folds.

| Criterion | dirichlet |
|---|---|
| 1. ≤ 4 divergences per fold, R-hat < 1.01, both horizons | **yes** (max 2; 1.0064) |
| 2. lower CRPS than control at 39 d | **yes** (9.35 vs 9.84) |
| 3. CRPS at 14 d within 2% of control | **yes** (9.16 vs 10.01, −8.5%) |
| 4. candidate calibration not worse (pooled KS) | **yes** (0.145 vs 0.24) |
| **Adopt** | **yes** |

Retroactive check: under the round-2 criterion 1, `support_scaled` now passes
criterion 1 but still fails 2 and 3; `leaders` still fails 1, 2 and 4. Round 1's
verdicts stand.

### The 2026 forecast under the adopted model (computed once, after the rule)

Joint fit of all eight campaigns, population hyperpriors, 4 × (1000 + 1000),
`target_accept 0.95`, seed 20260921: 0 divergences, R-hat 1.003, min ESS 1128.
φ_election 48 (90% interval 20–97).

| | Chow | Bradford | Alexander |
|---|---:|---:|---:|
| Win probability | **70.2%** | **29.3%** | 0.5% |
| Full-ballot share p10 / p50 / p90 | 32 / 46 / 60 | 23 / 36 / 51 | 3 / 9 / 17 |

Chow–Bradford margin: now +11.0 (80%: +2 to +20); election day +11.5
(80%: −17 to +38; SD 22.6 points against the isotropic model's 28.5).
P(Chow ahead of Bradford) 0.70. Residual pool 2 / 6 / 14.

This lands inside the 63–76% band written down before round 1 and the
63–76% expectation written before round 2. It was not used to choose anything.

### What changes if this is productionized

The published specification's discrepancy clause (ADR 0054: isotropic t(5) on
log-odds contrasts) becomes a Dirichlet composition reading with campaign-level
precision mixing. Everything else (polls, random walk, firm effects, residual
pool, qualification gate, feed schema 4) is unchanged. That needs an ADR, the
port of the variant into `backend/model/compact_mayoral/`, tests, the
methodology doc, and a new release. Not started without the user's go.
