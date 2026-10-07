# 0061. Learn where a Suspended Campaign's support goes

Date: 2026-10-07. Status: accepted.

This ADR amends ADRs 0054, 0056 and 0057. It records how the mayoral forecast
handles Chris Alexander's Suspended Campaign: how post-exit polls enter the fit,
the model adopted, the alternatives tried, the feed contracts, and the views not
built. The work was planned on [Handle Alexander's Suspended Campaign in the
mayoral forecast][map], and each decision below is recorded on a ticket linked
from it.

## Context

Alexander ended his campaign on Tuesday, October 6, 2026, after the withdrawal
deadline. He stays on the Final Ballot and can still receive votes. The compact
model (ADRs 0054, 0055 and 0057) had no way to represent this, and ADR 0056 said
a withdrawal "is not modelled and is not shown".

On the production release `backend-2026-10-06.1` the model failed in two ways
([Measure how the production model responds to post-exit polls][response]):

- **It froze.** The main fit drops any 2026 reading that does not name all three
  candidates. Pollsters stop naming a candidate after an exit, so every later
  poll would have been ignored.
- **When such polls were admitted, it misread them.** Alexander stayed at 6.7% on
  election day (80%: 2.0–13.5). A poll that still named him at 1% was read as fast
  campaign movement: the movement scale rose fivefold, and Bradford's chance rose
  by up to 8.5 points with no change between Chow and Bradford in the polls.

The record points the other way ([Suspended campaigns in the record: retained
share, transfers, pollster practice][record]). Ten Canadian mayoral candidates
have ended a campaign after the ballot deadline and stayed on the ballot: Toronto
2010 (Thomson, Rossi), Calgary 2010 (three), London 2014, Montreal 2017, Sudbury
2022 and the Toronto 2023 by-election (Davis, Mammoliti). Each finished with
0.05–1.3% of the vote. The seven whose last poll gave them a measurable share
kept 3–25% of it. No poll in the record isolates where their supporters went.

Post-exit polls arrived at once. Forum polled on October 6 (decided and leaning:
Chow 46, Bradford 42, someone else 12), against Chow 46, Bradford 35, Alexander 6,
someone else 13 on September 23.

One standing rule from the maintainer governs all of it: how the fitted model
moves is learned from data, never chosen by us. There is no hand-set break at the
exit.

## Decision

### 1. How post-exit polls enter the fit

From [Decide how post-exit polls enter the current fit][poll-rule]:

- A **Post-Suspension Reading** is a Poll Reading whose fieldwork overlaps or
  follows the public start of a Suspended Campaign. For Alexander that start is
  October 6, read from the Results release (section 4).
- It enters as a Chow–Bradford composition, whether or not it names Alexander.
  Any share it reports for him is set aside, and the reading is renormalised over
  Chow and Bradford. This is how 2010's post-exit polls already enter the
  historical fit.
- In a poll that asks both, the full-field question beats a Head-to-Head Reading,
  whatever their denominators. A Head-to-Head Reading counts only when it is the
  poll's only general vote-intention reading. Otherwise ADR 0057's selection and
  weighting apply unchanged.
- This amends ADR 0054's "certified-field 2026 polls only" and ADR 0057's
  selection order, for Post-Suspension Readings alone. The six 2026 polls that
  named only Chow and Bradford before Alexander entered stay out.

Backend tells a Head-to-Head Reading from a full-field question by the
`alternative_ballot` measurement class in the Polling release's 2026
`reading_classification.csv`, the class the historical corpus already uses.

### 2. The model: C2, a learned Exit Allocation

The model is C2, pre-registered in [Test three reactive versions of learning
where Alexander's support went][reactive] and adopted in [Decide whether every
2026 poll treats Alexander the same way][one-model]. It is the only model. S2,
adopted earlier the same day, is retired, and none of the alternatives below is
built.

At the exit date the latent random walk gains a node. From that node on:

- **Kept Fraction.** Alexander's latent support is multiplied by a Kept Fraction.
  It is drawn from a log-normal fitted to the seven usable cases of the ten-case
  record (log mean −1.838, log sd 0.713; median 0.159, 80% 0.064–0.397) and
  capped at 1. Post-Suspension Readings do not inform it, because they set his
  share aside.
- **Exit Allocation.** The rest of his support divides between Chow and Bradford.
  The split's prior is a Dirichlet with concentration 4, centred on their
  proportional split at the exit node. Post-Suspension Readings update it, each
  read against its pollster's existing house effect.
- **Everything else stays.** The residual pool is untouched. Alexander stays a
  named candidate in the model and in `candidate_win`.

Where it applies:

- **Only in the campaign being forecast.** The seven training campaigns are
  fitted exactly as before.
- **In every fit whose analysis cutoff falls on or after the exit.** That covers
  the main fit, both sensitivity refits, and forecast-history points from
  October 6 on. Earlier fits are the same model with no exit to apply, so the
  history chart up to October 6 is unchanged.

The Kept Fraction sits inside the latent support, before the election-day
Dirichlet reading of ADR 0055. That reading spreads a share this small widely,
with much of its mass near zero, so Alexander's election-day share comes out at
about 0.5% (80%: 0.0–4.2). S2, which applied the fraction after that reading,
gave about 1.0%. S2's check against the ten past cases therefore does not carry
over to C2.

On the research fit of 2026-10-07 with Forum's October 6 poll, C2 gives Chow
70.1% and Bradford 29.9% (75.3% and 24.7% without that poll). It sends 45% of
Alexander's freed support to Chow (80%: 19–76%), against a prior centred on 58%.

### 3. The standard: a target check plus a do-no-harm check

Set when S2's basis was corrected ([Run the seed-replicate test of the Suspended
Campaign signal][replicates]). A change that targets a known failure gets two
checks, both written down before any run:

1. a **target check** on the quantity it fixes, scored against the record that
   bears on it;
2. a **do-no-harm check** on the leader margin, against the production rule, on
   the held-out record.

The do-no-harm check for C2, C3 and the uniform rule ran at 20 and 14 days out
over five paired seeds (20260921–20260925). The 39-day horizon was dropped: later
held-out tests follow the point the forecast is actually used from. The rules:

1. At each horizon, the mean leader-margin CRPS over seeds is no more than 0.10
   points worse than production's.
2. A fold counts as covered when its 80% band holds the result in at least 3 of
   5 seeds, and the version covers at least as many folds as production.
3. Sampling: every fit that fails the research bar (more than 4 divergences, or a
   worst R-hat of 1.02 or above) gets one retry, at target acceptance 0.99 with
   seed + 1, in every arm including production's. After that, the version has no
   more failing fits than production.

Rule 3 changed twice in this work:

- **The baseline bar (2026-10-07).** As first written, any failing fit failed an
  arm. About 1 fit in 90 lands at R-hat 1.02 or above, so an arm of 65 fits fails
  about half the time, and the production rule itself failed (1 of 65) in the
  seed-replicate test. The maintainer applied the principle the coverage rule
  already used: when the baseline falls short, a variant passes by doing no
  worse.
- **The retry.** The failures were then diagnosed ([Diagnose how the uniform rule
  fails in 2010 and 2023][diagnosis]). They were mostly seed luck in a fragile
  2023 fold: 3 of 30 fits against 5 of 30 over 15 seeds (p = 0.71). One retry at
  production's retry settings cleared all four of the uniform rule's failing fits.
  The retry was added to the rule before C2's test ran. It uses production's
  retry settings, but it is broader than production's retry: production
  retries only a fit that has divergences, while the rule also retries a fit
  that fails on R-hat alone.

### 4. Feed contracts

From [Decide the feed shapes for the Suspended Campaign][feeds], as amended in
[Decide whether every 2026 poll treats Alexander the same way][one-model].

**Forecast feed: schema 4 → 5.** The policy stays `margin-first-joint-draws-v1`.

- `election_day.other_candidates` is always present:
  `{label: "Other candidates", median, lower, upper, includes: [{candidate_id, display_name, campaign_suspended_on}]}`.
  - Its range is the residual pool plus each included candidate's full-ballot
    share, summed draw by draw before the quantiles are taken.
  - It has no win probability. With an empty `includes`, it equals the pool.
  - It is a display grouping, not the Unmeasured Candidate Tail.
- `model.suspended_campaigns` is new:
  `[{candidate_id, campaign_suspended_on, kept_fraction: {distribution, log_mean, log_sd, median, lower, upper}, allocation: {prior_concentration: 4, by_candidate: [{candidate_id, prior_mean, median, lower, upper}]}}]`.
  Its ids must equal `other_candidates.includes`.
- `model.kept_fraction_cases` lists the ten recorded cases once.
- `model.specification` gains `exits: "learned_allocation"`. Its `polls` value
  changes from `certified_field_only` to `certified_field_with_post_suspension`.
- Each `model.current_readings[]` entry gains `post_suspension` and `set_aside`
  (the candidates whose reported share was not used).
- `final_field_samples` counts Post-Suspension Readings, so the "N polls" line
  includes them.
- `residual_pool`, Alexander's `election_day.candidates` entry and `candidate_win`
  keep their shapes.

**Results candidates feed: schema 5 → 6.**

- Every candidate carries a required `campaign_suspended_on`, a date or null. It
  is curated in the Results repository with evidence for each row. The City's
  roster cannot supply it, because it lists Alexander as Active.
- Backend reads the date from its pinned Results release. The date starts the
  exit, marks Post-Suspension Readings, and fills `includes` and
  `model.suspended_campaigns`. Backend refuses a Results release older than
  schema 6.

**Polling feed: stays at schema 2.** It gains a derived `head_to_head` array and
a `head_to_head` flag for display. The release also ships the 2026 classification
from section 1.

**Why the forecast version changes,** unlike ADR 0056's additive change with no
version bump: Alexander's numbers now mean something different, and the site
built for schema 5 removes the interim notice. A mismatched pair would publish
something false, either the notice over a post-exit forecast or no notice over a
pre-exit one. The validators accept exact versions, so either pairing fails the
build. The Backend release and the Frontend deploy go out, and roll back,
together.

### 5. What the site shows, and two views not built

The site follows variant D from [Prototype how the site presents the forecast and
the suspended campaign][presentation], with the copy as amended in [Decide whether
every 2026 poll treats Alexander the same way][one-model]:

- the interim notice is removed and the hero is unchanged;
- Alexander is folded into Other candidates in the vote ranges and named in the
  "What is behind these numbers" note;
- his own share reads "less than 1%" while its median is below 1%, otherwise
  "about N%", read from the release;
- the candidates page labels him "Campaign suspended Oct. 6".

Head-to-Head Readings appear as polls only. They are never averaged as separate
samples, because they share respondents with their poll's full-field question.

Two planned views were dropped:

- **No head-to-head view** ([Define the head-to-head view][h2h]). The main
  forecast's Chow–Bradford margin is the head-to-head. Explicit head-to-head
  questions are too few to fit or gate ([Inventory the Chow–Bradford
  head-to-head evidence][inventory]). There are three in 2026, each sharing its
  sample with a full-field question, and none since the exit. The historical
  corpus has none after a field change.
- **No transfer view** ([Define the transfer-assumption view][transfer]). It was
  designed in full: a pre-exit base, with Alexander's freed share split by
  Mainstreet's September 28–29 forced choice (50.85% to Chow). On that evidence it
  equalled the main forecast (Chow 75.7% against 75.5%), so it was not built. C2
  now learns the split from polls instead of assuming one. An endorsement by
  Alexander changes the fit only through later polls.

### 6. ADR 0056's withdrawal line is retired

ADR 0056 said a withdrawal by a named candidate "is not modelled and is not
shown". At the time the model had no mechanism for it, and the evidence was one
two-month-old paired question. A Suspended Campaign is now modelled (section 2)
and shown (section 5). A withdrawal before the deadline is a different event: it
changes the Final Ballot itself.

## Tried and not adopted

Do-no-harm differences are mean leader-margin CRPS against production at 20 and
14 days out, in points; the tolerance is 0.10.

| Version | What it did | Result | Why not adopted |
|---|---|---|---|
| S1, joint signal | One shared Kept Fraction fitted inside the model, acting on election-day support (prior from the five non-Toronto cases, median 0.219) | Passed the first test's run of record (−0.01 and +0.01 at 39 and 14 days) but failed on stale 2026 inputs (+0.12, +0.19). Over five seeds: +0.17 at 20 days, worse in every seed | Failed do-no-harm ([Test a fitted Suspended Campaign signal against the held-out record][signal], [Decide whether to adopt the joint Suspended Campaign signal][signal-decision]). It narrowed election day by roughly doubling `phi_election` (Chow 75.5% → 80.3%), and its Kept Fraction stayed at the prior (0.211–0.222). It covered 3 of 7 past cases |
| S2, forecast side | Alexander's election-day draws scaled by a Kept Fraction from the seven usable cases; the freed share to Chow and Bradford in proportion | Do-no-harm +0.09 and +0.04. Target check (leave one case out): 6 of 7 cases covered, mean absolute log error 0.53 against 1.84 for the unchanged model | Adopted on 2026-10-07 on the ten-case record, then retired by C2 the same day. Its fixed proportional split cannot learn from Post-Suspension Readings, and it cost the 2010 fold (CRPS 3.95 → 4.49 at 20 days) |
| Uniform rule | Alexander in Other candidates in every 2026 poll, before and after the exit | +0.128 and +0.019; 4 failing fits against production's 1 | Failed do-no-harm ([Test treating every 2026 poll the same way, with Alexander in Other candidates][uniform]). Folding Thomson out of 2010 stretched the margin by 1/(1 − 7.7%). The pool stayed at 5.6%, so Alexander's leftover support vanished |
| C3 | C2 plus a learned one-time Chow–Bradford shift at the exit | +0.163 at 20 days | Failed do-no-harm. It moved 2010's 14-day centre the wrong way (+9.4 against the actual +12.1) and lowered Chow's chance with no post-exit poll at all (71.5% against C2's 75.3%) |
| C1 | C2 plus pollster house effects | Not run | The model already has a house effect per pollster per campaign, so C1 was C2 |

**C2's record.**

- **Do-no-harm:** +0.057 at 20 days and +0.010 at 14. It covered 4 of 6 and 6 of
  7 folds, as production did. It had 2 failing fits before the retry and none
  after; production had 1 and none. All three failures were on R-hat alone, with
  no divergences, so production's own retry would not have retried them. Counted
  without retries, C2 had 2 failing fits against production's 1, a gap the
  diagnosis found to be within seed luck.
- **Target check (report only).** The check used 2010, the one past campaign with
  an exit before polling ended. At 14 days C2 was the best of the exit-handling
  versions (CRPS 3.77, against 3.92 for S2 and 3.65 for production, which ignores
  the exit). At 7 days it was the best of every version (4.52 against
  production's 4.67).
- **Seven days out, all folds (report only):** C2 had the lowest mean CRPS, 6.30
  against production's 6.36.

## Consequences

- **The forecast responds to each Post-Suspension Reading** through the Exit
  Allocation. Forum's October 6 poll alone lowers Chow's chance by about
  5 points.
- **The first release under this ADR** is the Backend release after
  `backend-2026-10-06.1`. It also carries the held 2010 Ipsos Reid addition
  ([Add the missing Ipsos Reid Sept 24–26, 2010 poll to the historical
  corpus][ipsos]), which moves Chow by about −1 point. It ships with the matching
  Frontend after a preview ([Decide the release order against the Deploy
  Freeze][release]).
- **The do-no-harm check is coarse for a change to the fit.** Between two sweeps
  that differed only in the 2026 inputs, S1's 14-day difference moved by 0.18.
  Across seeds the 20-day difference varies by 0.10 (sd) for S1 and about 0.15
  for the uniform rule, against a 0.10 tolerance. S2, which left the fit alone,
  varied by about 0.002. The gate is unchanged. The target check is where a fix
  shows its benefit.
- **Proportional reallocation hurt 2010.** It made the 2010 forecast worse in
  every version that used it, and no fixed reallocation beat ignoring the exit at
  both horizons. Where a Suspended Campaign's support goes is learned from
  Post-Suspension Readings, not assumed.
- **What the model still cannot learn.** No poll informs the Kept Fraction, which
  rests on seven cases. Until more Post-Suspension Readings arrive, the Exit
  Allocation stays wide.
- **Records.** The ten-case table is
  `data/raw/elections/mayoral_suspended_campaigns.csv`, with a source for each
  row. The research notes are [suspension-signal-holdout-2026-10-06.md][note-signal]
  (S1, S2 and the target check), [uniform-rule-2026-10-07.md][note-uniform] (the
  uniform rule and its diagnosis) and
  [reactive-allocation-2026-10-07.md][note-reactive] (C1–C3). Run artifacts stay
  outside every repository.

[map]: https://github.com/alexwolson/toronto-election-poll-tracker-backend/issues/27
[record]: https://github.com/alexwolson/toronto-election-poll-tracker-backend/issues/29
[response]: https://github.com/alexwolson/toronto-election-poll-tracker-backend/issues/28
[ipsos]: https://github.com/alexwolson/toronto-election-poll-tracker-backend/issues/35
[poll-rule]: https://github.com/alexwolson/toronto-election-poll-tracker-backend/issues/31
[signal]: https://github.com/alexwolson/toronto-election-poll-tracker-backend/issues/43
[signal-decision]: https://github.com/alexwolson/toronto-election-poll-tracker-backend/issues/44
[replicates]: https://github.com/alexwolson/toronto-election-poll-tracker-backend/issues/45
[inventory]: https://github.com/alexwolson/toronto-election-poll-tracker-backend/issues/30
[h2h]: https://github.com/alexwolson/toronto-election-poll-tracker-backend/issues/32
[transfer]: https://github.com/alexwolson/toronto-election-poll-tracker-backend/issues/33
[presentation]: https://github.com/alexwolson/toronto-election-poll-tracker-backend/issues/34
[feeds]: https://github.com/alexwolson/toronto-election-poll-tracker-backend/issues/46
[uniform]: https://github.com/alexwolson/toronto-election-poll-tracker-backend/issues/48
[diagnosis]: https://github.com/alexwolson/toronto-election-poll-tracker-backend/issues/50
[reactive]: https://github.com/alexwolson/toronto-election-poll-tracker-backend/issues/51
[one-model]: https://github.com/alexwolson/toronto-election-poll-tracker-backend/issues/49
[release]: https://github.com/alexwolson/toronto-election-poll-tracker-backend/issues/47
[note-signal]: https://github.com/alexwolson/toronto-election-poll-tracker-backend/blob/research/suspension-signal/docs/research/suspension-signal-holdout-2026-10-06.md
[note-uniform]: https://github.com/alexwolson/toronto-election-poll-tracker-backend/blob/research/uniform-rule/docs/research/uniform-rule-2026-10-07.md
[note-reactive]: https://github.com/alexwolson/toronto-election-poll-tracker-backend/blob/research/uniform-rule/docs/research/reactive-allocation-2026-10-07.md
