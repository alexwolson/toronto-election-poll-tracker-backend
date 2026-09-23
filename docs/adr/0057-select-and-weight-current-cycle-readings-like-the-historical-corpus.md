# 0057. Select and weight current-cycle readings like the historical corpus

Date: 2026-09-23. Status: accepted.

## Context

Until this decision the 2026 campaign entered the compact model through the
public archive (`polls.csv`): one editorially selected reading per sample,
weighted by the archive's `sample_size`, which is the recruited sample. The
historical corpus enters through the classification register: one reading per
same-sample group chosen by denominator rank (decided-plus-leaners, then
decided-only, then all-respondents), weighted by that reading's own base.

Two consequences surfaced when the Ipsos poll of September 4-8, 2026 was added
(published September 23). First, the model input depended on the display
selection, so an editorial choice for the archive silently chose the model's
data. Second, decided-type readings were over-weighted by 14-31%: their
recruited samples of about 1,000 stood in for cut bases of about 800, while the
one all-respondents reading was weighted correctly. Measured effect on the
forecast: 0.3 points of win probability. The composition itself was found to be
handled consistently: renormalising an all-respondents reading over the named
candidates reproduces the pollster's own decided reading within half a point on
the six 2026 samples that publish both.

## Decision

1. Every poll reading in the Polling schema carries `denominator_semantics`
   (`decided_plus_leaners`, `decided_only`, `all_respondents`, `other`), entered
   at ingestion and validated against `denominator_type`. It replaces the
   register for the current cycle; the register's derived table now covers only
   the historical corpus.
2. The 2026 campaign is built from the bundle's samples, readings and responses
   with the historical rule: per citywide extracted sample, the best-ranked
   general vote-intention reading whose published candidates cover the certified
   three (ties to more named candidates, then id), renormalised over the named
   candidates it reports, weighted by that reading's own base (weighted, then
   reported, then unweighted, then recruited) times the named share. `other`
   (turnout screens, leaner tables that keep undecideds, unreported denominators)
   is used only when a sample publishes nothing else.
3. The public archive remains the display layer. It gains a `denominator` label
   per poll so the page can say which cut it shows, and it no longer feeds the
   model.
4. The feed's model record lists the reading chosen per sample with its
   semantics, base and named share.

## Consequences

- Ipsos enters as its all-respondents reading, the same way the 2014
  all-respondents-only polls enter the historical corpus, at an effective base
  of about 614 rather than 1,006.
- The seven decided-type 2026 polls lose 14-31% of their weight; Chow moves by
  about a third of a point.
- Adding a poll now requires classifying each reading's denominator by hand in
  the Polling repository; the loader refuses a reading without it.
- The denominator rank remains a stated rule. A pre-registered held-out check of
  the reversed rank (all-respondents first) on 2026-09-23 was not adopted:
  CRPS +0.11 at 39 days, −0.33 at 14 days, narrower bands; recorded in
  `docs/research/compact-mayoral-width-defence-2026-09-22.md`.
