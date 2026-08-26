# Score 2018 with a 2014→2018 electorate crosswalk, not a reduced index

## Context

2018 is the only in-scope election whose incumbents' prior win (2014) sits in a
different ward map — Toronto went from 44 wards to 25. The two vote-based components
(vote share, elector share) come from each incumbent's own 2014 old-ward result and
are unaffected. But the growth component's "electors added since the win" needs a
like-for-like 2014 baseline on 2018 boundaries: `electorate(2018 ward) −
electorate(2014 old ward)` is meaningless because a 2018 ward is ~1.76× an old ward,
so the raw difference is dominated by the boundary merge, not real new voters.

The simpler option was to drop the growth component for 2018 (a two-component index),
but we chose to keep all three via a spatial crosswalk, because 2018 is the most
policy-relevant backtest (it forced incumbents to run against each other) and a
partial index there would undercut the comparison.

## Decision

Reproject 2014 ward electorate onto 2018 ward boundaries at the subdivision (poll)
level:

1. Re-parse `data/raw/voter_stats/2014-voter-statistics.xls` keeping the `Sub` column
   (the shipped pipeline groups it away) to get per-subdivision `Total Eligible
   Electors`.
2. **Raking for the ~8% with no geometry**: 560 of 1767 subdivisions are
   special/advance polls (sub 97/99 + institutional) carrying ~145k electors (8.0%)
   with no polygon. Scale each 2014 ward's *polygonized* subdivisions up so their sum
   equals that ward's true total, preserving every ward's full electorate before the
   crosswalk. (Assumes advance/institutional voters distribute like the ward's
   regular-poll voters.)
3. Join the raked electorate to 2014 subdivision polygons
   (`subdivision_boundaries.parquet`, `election_year==2014`) on
   `area_code = f"{Ward:02d}{Sub:03d}"`.
4. Dissolve 2018 subdivision polygons by `ward_number` → the 25 target wards.
5. **Area-weighted overlay** (reproject to EPSG:32617 first): intersect 2014 subs with
   2018 wards, apportion each sub's electorate by overlap-area fraction, sum to each
   2018 ward → `baseline_2014(W)`.
6. `new_electors(2018 W) = eligible_electors(2018 W) − baseline_2014(W)`; per incumbent
   `new_voter_margin = new_electors(W) − their 2014 winning margin`.

## Consequences

- 2018 rows are flagged `cross_era`; the crosswalk conserves citywide electorate
  (raking removes the 8% undercount that would otherwise manufacture ~8% fake growth).
- Area-weighting assumes uniform density within a subdivision; residual edge error is
  small because subdivisions are tiny relative to wards. Documented, not eliminated.
- A future reader will ask why 2018's growth term is computed differently from every
  other year; this ADR is why.
