# Reactive allocation of a departed candidate's support: C1, C2, C3 (2026-10-07)

Issue: [Test three reactive versions of learning where Alexander's support went](https://github.com/alexwolson/toronto-election-poll-tracker-backend/issues/51)
(map: [Handle Alexander's Suspended Campaign in the mayoral forecast](https://github.com/alexwolson/toronto-election-poll-tracker-backend/issues/27)).

## Pre-registration design (approved 2026-10-07; binding; committed before any held-out fit)

Code: `docs/research/compact_mayoral/reactive.py`, `model.py` (`reactive_support`, `prepare(extra_days=...)`),
`fit.py --reactive {c2,c3}`, tests `test_reactive.py`.

### Where it applies

Only the forecast-target campaigns: the held-out campaign of a fold, and 2026 in every fit. Every training
campaign is fitted exactly as in production rule P. P itself is unchanged: a stored P fold re-runs
bit-identically under the modified model.

- **Exits.** A target campaign's exits are its Suspended Campaigns announced on or before its cutoff, from
  `data/raw/elections/mayoral_suspended_campaigns.csv`, taken in date order.
  - 2026: Alexander, Oct 6, 20 days before election day.
  - 2010 at 14 and 20 days: Thomson only (day 27).
  - 2010 at 7 days: Thomson, then Rossi (day 12).
  - No other fold has an exit before its cutoff.
- **2026 readings.** Pre-exit readings are the three-way compositions production uses. Post-exit readings
  (fieldwork ending on or after Oct 6) are Chow–Bradford compositions, with any Alexander share set aside.
  Today that is Forum Oct 6.
- **Held-out readings.** A reading dated on or after an exit drops the departed candidate (renormalized,
  effective base scaled by the retained share). No 2010 reading after Thomson's exit offered him.
- **Time.** The latent random walk gains a node at the exit day. Pre-exit readings are modelled exactly as
  before.

### C2: the common machinery

Let `s(t)` be the latent named support (softmax of the Helmert contrasts) at each latent date `t`. For each
exit `j` (departed candidate `d`, remaining candidates `R`, exit node `E`):

| Parameter | Prior | Role |
|---|---|---|
| `log_keep_j` | Normal(mu, sigma): S2's log-normal over the suspension table's usable cases, leaving out the held-out campaign's own cycle (2026: all seven, mu -1.8382, sigma 0.7132; 2010 fold: five, mu -1.5172, sigma 0.1277, as S2 used) | keep fraction `k_j = min(exp(log_keep_j), 1)` |
| `allocation_j` | Dirichlet(4 · c), where `c = s_R(E) / sum(s_R(E))` is the proportional split at the exit node | how the freed share is divided over `R` |

On every latent date `t <= E` (on or after the exit), `s(t)` is replaced by:
- `s_d(t) -> k_j * s_d(t)`;
- `s_r(t) -> s_r(t) + (1 - k_j) * s_d(t) * allocation_j[r]` for each `r` in `R`.

Exits are applied in date order, so a later exit's `R` excludes earlier departed candidates.
- **Readings:** a reading at a post-exit date reads this transformed latent. Its log-probabilities are
  `log s(t)` plus the pollster's house effect, masked to the offered candidates.
- **Election day:** reads the transformed latent at day 0.
- **No post-exit reading:** `allocation_j` and `log_keep_j` keep their priors. `log_keep_j` is not informed
  by any reading, because post-exit readings exclude `d`.
- **Equivalence:** with a proportional allocation at the exit date, the transform equals S2's `suspend`
  (tested).

### C3: C2 plus a one-time shift at each exit

| Parameter | Prior |
|---|---|
| `shift_sigma_j` | HalfNormal(0.2263) |
| `shift_z_j` | Normal(0, 1), dimension `abs(R) - 1` (non-centred) |

- **The shift:** `shift_j = H_R @ (shift_sigma_j * shift_z_j)`, where `H_R` is the remaining candidates'
  orthonormal Helmert basis. It is a sum-zero log-ratio vector.
- **Where it applies:** on every date `t <= E` after the allocation. The remaining candidates' shares are
  multiplied by `exp(shift_j)` and renormalized to their unshifted total. The departed share is unchanged.
- **Why 0.2263:** for two remaining candidates at even support, a share shift is
  `0.25 * sqrt(2) * shift_sigma * z`. So with `E[shift_sigma^2]^(1/2) = 0.2263`, one prior standard deviation
  is 0.08: an 8-point move in the two-way share, the size of 2010's same-firm Ipsos jumps.

### C1: not distinct from C2 as specified

Production and the research model already have pollster house effects in every campaign:
- `firm_z ~ Normal(0, 1)` per pollster per campaign (non-centred), scaled by `tau_firm / sqrt(2)`, with
  `tau_firm ~ HalfNormal(0.15)` shared across campaigns;
- added to the Helmert contrasts of every reading, keyed on the pollster field.

So C2 already reads a firm's post-exit poll against that firm's own lean, estimated from its pre-exit polls.
"C2 plus house effects" adds nothing. A distinct C1 needs a different definition (see the phase 1 report).

## Decisions and rules (copied from the issue, 2026-10-07)

### Decisions before the run (maintainer, 2026-10-07)

Both come from the phase 1 build. No held-out fit had run.
- **C1 is dropped.** The model already has pollster house effects in every campaign (`firm_z`, scaled by `tau_firm`), so C2 already reads a firm's post-exit poll against that firm's own lean. "C2 plus house effects" was the same model. Cross-cycle leans were offered and declined.
- **The kept fraction stays where it was built:** inside the latent support, before the election-day reading. So Alexander's election-day share comes out at about 0.5% (0–4.2) under C, against about 1% (0.2–3.4) under S2.
  - S2's check against the ten past cases does not carry over to C.
  - The approved "about 1% today" copy would need to change if C is adopted.

### Rules (approved by the maintainer 2026-10-07; binding)

**Do-no-harm (binding):** each of C2 and C3 against the production rule P.
- **Horizons and seeds:** 20 and 14 days, seeds 20260921 to 20260925.
- **P's fits:** reused from the seed-replicate test, which are bit-identical on these inputs.
- **The rules:**
  1. at each horizon, the mean leader-margin CRPS over seeds is no worse than P's by more than 0.10;
  2. a fold counts as covered when 3 of 5 seeds cover it, and the version covers at least as many folds as P;
  3. sampling: changed from the uniform-rule test. Every fit that fails the research bar (more than 4 divergences, or R-hat at or above 1.02) gets production's one retry (target acceptance 0.99, seed + 1), in every arm including P. After that, the version has no more failing fits than P. Production does this retry, and the diagnosis showed the bar without it is mostly seed luck.

**Target check (report only):** 2010, the one campaign with an exit before polling ended.
- Leader-margin CRPS, centre and width, at 14 days (one post-exit poll) and at 7 days.
- Compared against P, A (P plus S2) and U (the uniform rule).

**7-day horizon (report only):**
- every arm, all folds, 5 seeds (3 if the budget forces it);
- the forecast will be in use 7 days out before the forecast-only window closes.

**Current inputs (report only):** 2026 with and without Forum Oct 6. Report:
- win probabilities, and Chow's election-day share of the Chow–Bradford vote;
- Alexander's share, the allocation posterior, C3's shift posterior and C1's house effects;
- the movement scale and the diagnostics.

**Budget and records.**
- A preflight extrapolation comes first; stop and report if it projects more than 4 hours of compute.
- The pre-registration (exact parameterization and these rules) is committed on `research/uniform-rule` before any held-out fit runs.
- The research note is `docs/research/reactive-allocation-2026-10-07.md`.

## Phase 1 checks (2026-10-07; no binding held-out fold run)

Runs: `research-runs/reactive-allocation-2026-10-07/` (workspace root). Inputs: the same as issue 48 (Polling
`poll/forum-2026-10-06` `polls.csv` with 30 rows, `results-2026-09-30.2`).

- **Tests:**
  - `test_reactive.py`: 8 pass. With the uniform-rule and suspension tests, 27 pass.
  - `test_compact_mayoral.py`: 2 pre-existing failures, both stale 2026 poll-list pins, not this change.
- **Harness (OBSERVED):** P's seed 20260922, 14-day 2010 fold, re-run under the modified model, is
  bit-identical to the seed-replicate test's stored fold (124 arrays).
- **Smoke fits** on current inputs with Forum Oct 6, at production settings (4 x (1,000 + 4,000), target
  acceptance 0.95, seed 20260921) (OBSERVED):

| | P (issue 48) | A1 (decided + S2) | U1 (uniform) | C2 | C3 |
|---|---|---|---|---|---|
| Win: Chow / Bradford | 75.5 / 24.3 | 70.4 / 29.6 | 71.1 / 28.9 | 70.1 / 29.9 | 63.4 / 36.6 |
| Chow two-way, median (80%) | 57.0 (43.1-70.0) | 55.5 | 55.6 | 55.2 (41.9-68.1) | 53.4 (40.0-66.8) |
| Alexander, full ballot | 6.6 | 1.0 (0.2-3.4) | (pool) | 0.5 (0.0-4.2) | 0.5 (0.0-4.2) |
| Divergences / worst R-hat / min ESS | 1 / 1.0009 / 2,982 | 0 / 1.0008 | 1 / 1.0008 | 0 / 1.0009 / 2,984 | 3 / 1.0014 / 2,199 |

- **C2 allocation of Alexander's freed share to Chow:** 0.450 (0.19-0.76), against a prior centred on the
  proportional split, about 0.57. Keep fraction 0.161 (0.064-0.394), which is the prior.
- **C3:**
  - allocation to Chow 0.513 (0.22-0.82);
  - shift sigma 0.129 (0.025-0.316), against a prior median of 0.152;
  - Chow-minus-Bradford log-ratio shift of about -0.074, roughly 1.8 points of two-way share toward Bradford.
  - Its 3 divergences sit in 2 chains and are not at an extreme of the shift scale (ranks 0.52, 0.06, 0.63).
- **House leans** on the Chow two-way (C2, points): Ipsos +3.8, Canada Pulse +1.9, Forum -0.6,
  Liaison -1.9, Mainstreet -1.8, Pallas -1.1, Nanos -0.3.
- **Alexander's election-day share is about half of S2's** (median 0.5 against 1.0, with a wider band).
  - C applies the keep fraction to the latent support before the election-day Dirichlet reading. Its tiny
    concentration (about 0.4) puts much of the mass near 0. S2 applies the keep fraction after the reading
    (INFERRED).

**2010 14-day feasibility fold** (seed 20260921, diagnostics only; the margin and CRPS were not read):

| | Divergences | Worst R-hat | Min ESS |
|---|---|---|---|
| C2 | 0 | 1.0065 | 1,052 |
| C3 | 0 | 1.0028 | 1,084 |

- In this fold Thomson's exit (day 27) applies with the post-exit Ipsos Oct 8 reading.
- The κ prior leaves out 2010 (log-normal(-1.517, 0.128), five cases), as S2 did.
- The 7-day 2010 build (Thomson, then Rossi) traces correctly. All seven campaigns have a 7-day fold
  (2022 has one poll).

**Wall-time extrapolation** (INFERRED from measured per-fit times):
- A held-out fit (4 x (1,000 + 1,000)) takes about 2.2-2.7 minutes per worker at 4 workers, about 0.55
  minutes of wall time per fit.
- The issue-48 sweep measured 0.49 minutes per fit.

| Plan | Fits | Wall time |
|---|---|---|
| Binding: C2 and C3 x 13 folds x 5 seeds | 130 (195 if C1 runs as a separate arm) | about 72 minutes (107) |
| Retries, production's one retry for every research-bar failure in every arm, at the 2-6% failure rates seen | about 10-12 | about 6 minutes |
| 7-day report: P, C2, C3, U x 7 folds x 5 seeds (A is P plus S2, computed on P's draws) | 140 (175 with C1) | about 77 minutes (96) |
| Current inputs: C2 and C3 without Forum | 2 | about 3 minutes |
| **Total** | about 285 (about 385 with C1) | **about 2.6 hours (3.5 hours)** |

Both totals are under the 4-hour budget.
