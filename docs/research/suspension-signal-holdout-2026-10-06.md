# Suspended Campaign signal: pre-registered held-out test

October 6, 2026. Task for backend issue 43, "Test a fitted Suspended Campaign signal against the
held-out record". The design, order and pass rules were decided in issue 31, "Decide how
post-exit polls enter the current fit", and are written out in issue 43's body. This note adds only
the implementation readings below. They were fixed and committed before any fold ran. Nothing
here changes a feed, release or deployment.

## Implementation readings (fixed before any run)

1. **Where the signal acts (S1).**
   - The kept fraction multiplies the suspended candidate's latent named support on election day,
     before the Dirichlet election-day reading (`model.py`, `election_support_suspended`).
   - The freed share goes to the other named candidates in proportion to their support.
   - The residual pool is modelled separately in the compact model (its own logit, independent of
     the named composition), so it keeps its fitted share.
   - The difference from a full-ballot reallocation is the pool's proportional slice of the freed
     share. It cannot move the named margin or the winner.
2. **No poll-level hook is needed.** No modelled reading dated on or after a suspension names the
   suspended candidate. In 2023, Forum's June 23 decided reading, the one selected, leaves Davis
   blank. `check_no_post_suspension_offer` asserts this in every S1 fit.
3. **Cutoff.**
   - A campaign whose result is observed uses its election day as the cutoff, so all its
     suspensions apply.
   - The held-out campaign at horizon H uses election day minus H days.
   - In these folds the signal therefore fires only for Thomson in 2010 at 14 days (27 days out).
     Rossi (12), Davis (6) and Mammoliti (2) fall after every cutoff, and nothing fires at 39 days.
4. **2026 gets no signal inside these fits.** The table holds the ten recorded historical cases.
   The 2026 forecast every fit carries stays sealed and is not part of the decision.
5. **S1 prior.**
   - One shared kept fraction: `log keep_fraction ~ Normal(mu, sigma)`, where mu and sigma are the
     mean and sample standard deviation (n−1) of log kept fractions over the non-Toronto rows that
     have a positive last share.
   - The values come from five cases: mu = −1.5172, sigma = 0.1277, median 0.219, 80% 0.186–0.258.
   - The draw is capped at 1.
6. **S2.**
   - The fits are the baseline's.
   - For a held-out campaign with a suspension known at its cutoff, each election-day named draw is
     multiplied by a kept fraction drawn from the table's log-normal (NumPy seed 20260921), with
     Toronto 2010's rows excluded when 2010 is held out.
   - For the 2010 fold that is the same five cases as the S1 prior. With all seven usable cases
     (production use): mu = −1.8382, sigma = 0.7132, median 0.159.
   - Folds with no suspension known at the cutoff are the baseline fold unchanged.
7. **Kept fraction per case.**
   - It is the final share divided by the last pre-suspension poll share.
   - "Last" means the poll with the latest fieldwork end before the announcement. Within that
     poll, the reading follows ADR 0057's denominator rank (decided-plus-leaners, then decided,
     then all respondents); turnout screens rank last.
   - A last share of 0, or no poll, gives no ratio. That excludes Davis (Forum June 9, 0%),
     Mammoliti (Forum June 23, 0%; the 1% was June 9) and Bigger (no poll).
   - Calgary's last poll is Léger (fieldwork to Oct 11, published Oct 14), not Ipsos (to Oct 6).
     Fortier's is the 5% decided figure, not 3% of all respondents.
   - Table: `data/raw/elections/mayoral_suspended_campaigns.csv`, with a source per row from the
     issue 29 record.
8. **Settings.**
   - The 2026-09-22 comparison's settings: `run_holdouts.sh` with variant `dirichlet`, population
     hyperpriors, seed 20260921, target acceptance 0.95, 4×(1000+1000), corpus `all`, and
     `evaluate.fold_metrics` unchanged.
   - S1 adds `--suspension-signal joint` (run suffix `_joint`).
   - The baseline is re-run in this session on data repo `main` c7c965e, which includes Ipsos Reid
     Sept 24–26, 2010.
   - The decision is computed by `suspension_compare.py`.
9. **Known caveat, recorded before the runs.** The five-case prior is tight (sd 0.13 in logs), and
   Thomson kept 0.033, far below it. S1's estimate will therefore sit near the prior. Any value in
   the recorded range (0.03–0.25) removes most of the penalty Thomson's and Rossi's collapse puts on
   the election-day term, and that relief is the mechanism under test.
10. **Pre-existing state.** Two research tests fail on `origin/main` before any change here
    (`test_current_2026_*`). They pin an older 2026 poll list, and the 2026 polls do not enter the
    held-out folds.

**Expectation, from issue 43, recorded beforehand (INFERRED).** S1 fails rule 1 at both horizons.

## Input correction before the decision of record (2026-10-06, 20:50 UTC)

The first sweep (runs `runs/`, 20:15–20:42 UTC) read the 2026 campaign from a stale local
hydrate: 8 polls from the Sept 23 archive instead of the 14 in production. Every fold fits 2026
jointly with the history, so the shared scales and fold scores depend on it. Baseline and S1 used
the same stale input, so that comparison was internally consistent.

The first sweep's verdict was S1 failing rule 1 (+0.12 at 39 days, +0.19 at 14) and S2 passing.
The S1 failure at 39 days is narrow, so the sweep was rerun with the production 2026 inputs:
`polls.csv` and `mayoral_candidates.json` from `polling-2026-10-06.2` and `results-2026-09-30.2`,
the pins of `backend-2026-10-06.1`.

**Committed before the rerun:** the rerun is the decision of record, whatever it shows. Both
sweeps are reported.
