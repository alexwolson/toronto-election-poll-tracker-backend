# Candidate-history watch-list review

Date: 2026-08-21

## Decision

Approve the two Returning-councillor Open-contest patterns with the explicit
`consistent_small_sample` evidence tier. Keep the Incumbent-facing-prior-council-loser pattern as
suggestive and method-sensitive. Withhold the weaker Challenger pattern.

The publication standard is a clear, multiple-testing-corrected historical association stated as
descriptive context. A separate conditional coefficient after adding correlated history measures
is not required.

## Supplemental method

The review uses the same 2010, 2014, and 2022 stable-boundary sample, election and Candidate-regime
adjustment, field-size control, and Contest-clustered bootstrap as the main screen. It adds:

- 20,000 Contest-clustered bootstrap replicates;
- removal of each triggered Contest in turn; and
- 50,000 within-election label permutations, preserving each election's trigger count.

The screen's Benjamini-Hochberg correction remains the publication correction. Permutation results
are robustness checks, not replacements selected to obtain a preferred result.

## Incumbent facing a prior unsuccessful council candidate

- Adjusted association: -8.24 Vote-share points.
- High-precision bootstrap interval: -15.78 to +0.07; p=.0517.
- Within-election permutation p=.0341.
- Twenty triggered Contests; leave-one-Contest-out estimates range from -9.67 to -6.98, all negative.

The clustered interval narrowly crosses zero while the permutation test clears it. Because the
publication conclusion changes with the uncertainty method and the family-adjusted screen result
does not clear q<.05, this is not a clear corrected association. Retain it as a near-miss in the
audit rather than publishing it.

## Returning councillor in an Open contest

- Adjusted association: +36.43 Vote-share points.
- High-precision bootstrap interval: +26.59 to +50.21; p=.0001.
- Within-election permutation p=.00022.
- Four triggered Contests across three elections; leave-one-Contest-out estimates range from
  +31.65 to +40.09, all positive.

The original five-Contest cutoff is missed by one, but the association remains clear under every
influence check and the independent-Contest limitation is easy to state. Approve with the
`consistent_small_sample` tier and expose the four-Contest sample size.

## Facing a Returning councillor in an Open contest

- Adjusted association: -6.41 Vote-share points.
- High-precision bootstrap interval: -12.92 to -3.79; p=.00051.
- Within-election permutation p=.0156.
- Four triggered Contests across three elections; leave-one-Contest-out estimates range from
  -7.28 to -5.45, all negative.

This is the Opponent-field view of the same four historical Contests. It also survives every
influence check. Approve with the `consistent_small_sample` tier and expose the four-Contest sample
size.

## Challenger facing another prior unsuccessful council candidate

The adjusted association is -1.49 points, its interval includes zero, its corrected screen result
does not clear q<.05, and its election direction reverses slightly in 2022. It remains withheld.
