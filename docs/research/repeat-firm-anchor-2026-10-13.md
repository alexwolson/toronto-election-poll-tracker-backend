# Anchor house effects on repeat pollsters (2026-10-13)

**Status: pre-registration approved as written by the maintainer, 2026-10-13. Binding. Committed on
`research/repeat-firm-anchor` before any code change or held-out fit.**

## Question

Every campaign's pollster house effects are drawn around zero, so the "unbiased" frame is the average of all
the firms polling that campaign, including firms with a single poll. A single poll cannot separate a firm's
lean from that poll's sampling noise, yet the firm counts in the anchor as much as a firm measured six times.

Variant V asks one question: should only firms with repeat polls in the campaign define the anchor?

**Why now (disclosed so the test is read in context):**
- On 2026-10-13 the maintainer asked why the published forecast (`backend-2026-10-13.1`, current Chow–Bradford
  two-way margin about +9.2) sits above the three post-suspension polls (+3 to +5).
- Read-only diagnostics that day (not committed) found it is mostly anchoring:
  - Ipsos (+7.6) and Canada Pulse (+3.8), each with one 2026 poll, pull the zero.
  - Against that zero, Liaison (−3.8) and Mainstreet (−4.3) read as Bradford-leaning.
  - Refit without Ipsos and Canada Pulse: +6.3, Chow win 63.5%.
- The same day's check of past campaigns' final-three-week polls (raw firm errors against the result) is
  partly the record this test's target check reads (see Target check). It was seen before this rule was
  written.
- **The motivation is a 2026 number.** That is why the rule, criteria and horizons are fixed here and bind
  either way.

## Arms

- **P (baseline):** production as released in `backend-2026-10-13.1`, source b3e30c6:
  - `backend/model/compact_mayoral/`, Dirichlet election day (ADR 0055);
  - C2 exits (ADR 0061);
  - Excluded Polls (ADR 0062).
- **V (repeat-firm anchor):** P plus the rule below, in every campaign of every fit (training, held-out
  and 2026). Nothing else changes.

### V: the rule

For each campaign in a fit:
- **Repeat firms:** let `M` be the pollsters with at least two polls in that campaign's fitted data. A poll
  is one sample, as in production. Count up to the fold's cutoff for a held-out campaign, all polls for a
  training campaign, and up to the analysis cutoff for 2026.
- **Raw effects:** `raw_k = firm_z_k * tau_firm / sqrt(2)`, as in P, for every firm `k`.
- **If `M` has at least two firms:** `firm_k = raw_k - mean_{j in M} raw_j` for every firm `k`, in contrast
  space. The repeat firms' effects then sum to zero. Single-poll firms keep a free effect in the same
  frame. Every poll stays in the fit.
- **Otherwise** (`M` has fewer than two firms): `firm_k = raw_k`, unchanged from P.
- **Unchanged:** the effects enter readings exactly as in P (added to the Helmert contrasts, or to the log
  support after an exit). `tau_firm`, its prior and every other site are as in P.

**Code (to be written after approval, before any held-out fit):**
- `build_model(..., house_anchor="prior" | "repeat_firms")`, default `"prior"`, and `prepare()` gains the
  per-campaign repeat-firm mask;
- a held-out runner `docs/research/compact_mayoral/anchor_holdouts.py` that uses the production package, so
  P is exactly what is published;
- tests:
  - (a) `"prior"` reproduces P bit-identically, both a stored held-out fold and the 2026 fit that reproduced
    `backend-2026-10-13.1` (Chow 0.691438);
  - (b) under `"repeat_firms"`, `M`'s effects sum to zero;
  - (c) a campaign with fewer than two repeat firms is unchanged.

### Where V changes anything (computed from the inputs before writing the criteria)

| Campaign | Repeat firms | Single-poll firms | Held out at 14 d | Held out at 7 d |
|---|---|---|---|---|
| 2003, 2006, 2022 | none | all | unchanged | unchanged |
| 2010 | Angus, EKOS, Ipsos, Nanos (full data) | Pollara | unchanged (1 repeat firm) | **changes** (single: EKOS, Pollara) |
| 2014 | Forum, Ipsos, Mainstreet, Nanos | Maple Leaf | **changes** | **changes** |
| 2018 | Forum, Mainstreet | Probit | **changes** | **changes** |
| 2023 | Forum, Liaison, Mainstreet, Viewpoints | Ipsos | **changes** | **changes** |
| 2026 | Forum, Liaison, Mainstreet | Canada Pulse, Ipsos, Nanos, Pallas | n/a | n/a |

The test has little power:
- the rule touches 3 held-out folds at 14 days and 4 at 7 days;
- in 2014 and 2018 the single-poll firm is a minor early poll;
- 2023 (a single late Ipsos poll) is the one fold resembling 2026.

The likely outcome is no detectable difference, and then P stands.

## Settings and inputs

- **Inputs:**
  - Results `results-2026-10-07.1` and Polling `polling-2026-10-13.1`, hydrated exactly as for
    `backend-2026-10-13.1`;
  - the historical corpus from that Polling release (ADR 0060).
- **Fits:**
  - production settings: 4 chains × (1,000 warmup + 4,000 draws), target acceptance 0.95;
  - production's one retry (0.99, seed + 1) for any fit with more than 4 divergences or R-hat ≥ 1.02, in
    both arms.
- **Folds:** each of the seven historical campaigns held out in turn at each horizon:
  - polls on or after the cutoff are removed and the outcome is withheld;
  - 2026 and the other six campaigns are fitted jointly, as in previous tests.
- **Horizons:** 14 days (today is 13 days out) and 7 days (the forecast will be in use then).
- **Seeds:** 20260921–20260925.
- **Scoring:** leader-margin CRPS and 80% coverage as in `docs/research/compact_mayoral/evaluate.py`. The
  leader pair is the top two by the latest polls at the cutoff (pre-outcome information), as in previous
  tests.

## Criteria (binding once approved)

### Do-no-harm (binding)

At each of 14 and 7 days:
1. V's mean leader-margin CRPS over all folds and seeds is no worse than P's by more than 0.10 points;
2. a fold is covered when 3 of 5 seeds cover it, and V covers at least as many folds as P;
3. after the retry, V has no more sampling failures than P.

### Target check (binding)

The quantity V changes is the current-state estimate when single-poll firms disagree with repeat firms.

- **Metric (anchor error):** on the folds V changes (3 at 14 d, 4 at 7 d), the absolute difference between
  the median latent two-way leader margin at the cutoff and the actual result's two-way margin. Take the mean
  over those folds and seeds.
- **Rule:** V's anchor error is lower than P's at 14 days.
- **Reported, not binding:** 7 days.
- **Caveat stated in advance:** late real movement contaminates this error equally in both arms, and 2023
  dominates the 14-day reading.

### Model-free record (report only)

- **Comparison:** for every campaign with at least two repeat firms and at least one single-poll firm in the
  final 21 days, compare the repeat-firm average's two-way error against the result with the all-firm
  average's.
- **Not binding,** because this record was partly seen on 2026-10-13 before the rule was written.

### Adoption

V is recommended for adoption only if both binding checks pass. In any other case P stands, with no re-runs,
added criteria or alternative anchors in this test.

### 2026 (report only, computed last, once)

V against P on current inputs:
- win probabilities and the current and election-day two-way margins;
- house effects by firm, the movement scale, and diagnostics.

## Budget and records

- **Fit count:** 2 arms × 2 horizons × 7 folds × 5 seeds = 140 fits, plus retries.
- **Preflight:** one fold at production settings comes first, with a total-time extrapolation, on the Mac
  and/or the Linux box.
  - Stop and report if it projects more than 4 hours of wall time.
  - The fallback then is 3 seeds per arm, with coverage at 2 of 3. The maintainer decides; this file is not
    edited after the fact.
- **Runs:** `research-runs/repeat-firm-anchor-2026-10-13/` (workspace root, never in git).
- **Results:** appended below this line, dated, without editing anything above it.

## If V is adopted

- An ADR amending ADR 0054's house-effect specification.
- The production default changes.
- Any edit to `compact_mayoral/*.py` invalidates the history cache, so the next build is about 45 minutes
  cold. Then a release, a preview and the maintainer's go.
- The Deploy Freeze starts Oct 23, 18:00 EDT.

---

## Run record (appended; nothing above this line is edited)

### Preflight (2026-10-13)

- **Commits:**
  - b47ba99: the harness;
  - 2c899fd: `repeat_firms` used a boolean mask index, which fails under jit. The fix uses static
    positions and adds a compile-and-sample test. P's code path is untouched.
- **Identity:**
  - P on the 2023/14-day fold, seed 20260921, matches main (b3e30c6) in every recorded field at full
    precision;
  - the default 2026 fit reproduces `backend-2026-10-13.1` (Chow 0.6914).
- **Timing on the Mac:**
  - P: 160 s per fit;
  - V: 279 s per fit, 1 divergence, R-hat 1.001;
  - projected 8.5 h for 5 seeds, over the 4 h stop.
- **Scores:** the preflight fold's scores were saved and not read before the decision below.

### Maintainer decision (2026-10-13)

- 3 seeds per arm (20260921–20260923).
- A fold is covered when 2 of 3 seeds cover it. Every other criterion is as written.
- Speed-test the Linux box before splitting the run across machines.

### Run setup (2026-10-13)

- **Machines:** Linux box (12 cores, CPU JAX) at commit 5e7d268, with `data/upstream` byte-identical to the
  Mac (sha256 of the sorted file hashes matches).
- **Speed:** P on the preflight fold took 420 s on the box against 160 s on the Mac (2.6×).
- **Units:** a unit is P then V for one (seed, horizon, campaign), so each pair shares a machine. Draws
  differ by CPU, so arms are never split across machines.
- **Order:** the box runs the 42 units in seed-major order, starting with 20260921 at 14 days, folds in
  campaign order. At the maintainer's request (heading to work) the Mac's share is held. When the Mac joins,
  it takes the remaining units from the end, and the box's `limit` file caps its share.
- **Fits scored:** the queue's outputs only. The Mac preflight copies of the 2023/14-day/20260921 fold are
  not scored. The box's speed-test pair for that unit (same commit, same inputs) is adopted as the queue's
  unit.
- **Disclosure:** while checking the box's speed, its log printed that fold's P score (CRPS 7.04). No V
  score was seen, and no comparison.

### Mac joins (2026-10-13, 09:35, maintainer: "go for local too")

- **Split:** the box is capped at units 1–15 (`limit` = 15) and the Mac runs units 42 down to 16. Both are
  projected to finish around 12:40.
- **Rates:** the box measured about 16 min per unit (P 420 s, V 441 s); the Mac about 7.3 min.
- **Mac setup:** `/private/tmp/backend-anchor`, whose code is identical to the box's 5e7d268 (later commits are
  docs only), on AC power under `caffeinate`.
- **Rebalance at 11:55:** the box was running at about 20 min per unit, so its cap was lowered to 14. Unit 15
  (20260922, 14 d, 2003) runs on the Mac after the Mac's queue, P then V on the same machine. The scorer
  refuses duplicates and missing fits.

## Results (2026-10-13, scored once by `score_anchor.py` at 4589246; 84 of 84 fits)

**Verdict: V is not adopted. P stands.** The do-no-harm checks pass at both horizons. The binding target
check fails at 14 days: V's anchor error on the changed folds is higher than P's.

| | 14 d P | 14 d V | 7 d P | 7 d V |
|---|---|---|---|---|
| Mean leader-margin CRPS (pts) | 9.26 | 9.27 (within +0.10) | 6.32 | 6.42 (within +0.10) |
| Folds covered (2 of 3 seeds) | 6/7 | 6/7 | 7/7 | 7/7 |
| Sampling failures after retry (retries) | 0 (1) | 0 (0) | 1 (2) | 0 (0) |
| Anchor error on changed folds (pts) | 12.92 | **13.15** (target fails) | 12.68 | 13.27 (report only) |

**Per fold, changed folds only.** Anchor error is the |median latent two-way leader margin at the cutoff −
actual two-way margin|, as the mean over 3 seeds.

| Fold | P | V |
|---|---|---|
| 2014, 14 d | 6.99 | 7.25 |
| 2018, 14 d | 11.37 | 11.04 |
| 2023, 14 d | 20.40 | 21.16 |
| 2010, 7 d | 6.54 | 8.14 |
| 2014, 7 d | 10.99 | 11.19 |
| 2018, 7 d | 11.43 | 11.14 |
| 2023, 7 d | 21.77 | 22.63 |

Unchanged folds agree to within seed noise (largest CRPS gap 0.05).

**2026 on current inputs (report only, computed once after scoring):**

| | P (`backend-2026-10-13.1`) | V |
|---|---|---|
| Chow win | 69.1% | 63.4% |
| Current two-way margin, median (80%) | +9.2 (+2.2 to +16.1) | +6.0 (+1.6 to +10.2) |
| Election-day margin, median (80%) | +8.4 (−14.6 to +32.1) | +5.5 (−17.4 to +28.7) |
| Liaison house effect | −3.8 | −0.8 |
| Mainstreet house effect | −4.3 | −1.3 |
| Ipsos house effect | +7.6 | +10.8 |
| Canada Pulse house effect | +3.8 | +6.9 |
| Movement scale | 0.05 | 0.05 |
| Divergences / worst R-hat / min ESS | 0 / 1.003 / 1,997 | 0 / 1.003 / 1,874 |

**Not run:** the model-free record (report only) was not computed; the binding result already settles the
decision.
