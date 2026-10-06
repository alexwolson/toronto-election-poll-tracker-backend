# Historical evidence for ward-poll uncertainty

**Research date:** October 2, 2026. **Status:** evidence audit and research proposal;
no production model, ADR or source-data change. Scope: the five September 25–27
Forum Council polls in Wards 3, 4, 13, 19 and 23, and what can support uncertainty
charts resembling the mayoral home page.

## What is actually retained

The current normalized source tables contain 41 respondent samples. Twelve are
ward samples, all Forum Research, covering eight Council contests in the 2026
cycle. They contain 16 Council readings and 10 ward-level mayoral readings:
26 readings and 112 published response rows in total. Four additional Council
readings are alternate questions within respondent samples, not independent
polls. These counts were recomputed from `poll_samples.csv` and
`poll_readings.csv`, joining on parent sample ID. See the
[initial acquisition audit](../../../toronto-election-poll-tracker-data/docs/research/current-council-source-acquisition.md)
and [October 2 ingestion audit](../../../toronto-election-poll-tracker-data/docs/research/forum-ward-polls-2026-10-02.md).

The five target wards have 1, 1, 2, 3 and 1 parent Council samples respectively
(Wards 3, 4, 13, 19 and 23). The older Ward 13 sample includes a dependent,
hypothetical Wong-Tam question; the two older Ward 19 polls described an
Erskine-Smith entry scenario. Repetition does not turn different candidate
fields into an exchangeable final-field time series. The September polls are
the only post-nominations-closed Council samples in these five wards.

The separately retained historical normalized tables contain **117 citywide
mayoral samples, 260 mayoral readings and zero Council readings**. Historical
Council election results are plentiful, but outcomes without a corresponding
pre-election poll cannot identify poll-to-election errors. Candidate records
within a contest likewise are not separate election-level calibration trials.

## The six-contest 2022 probe

The [closed September 23 probe](../../../toronto-election-poll-tracker-data/docs/research/council-open-seat-and-ward-poll-probe.md)
previously acquired six Forum ward polls, matched them to official outcomes,
and then reverted all ingested records and scratch code. Its evidence remains
in a note, not an admitted production calibration dataset. Its independent
units were **six respondent samples, six contests, one election cycle and one
pollster**, fielded September 13–15, 2022, 39–41 days before October 24.
Each sample also supplied a ward mayoral question; those six dependent mayoral
readings do not double the Council calibration sample.

| Ward | Fieldwork | Recruited n | Council table base | Published Council shares (%) |
|---|---|---:|---:|---|
| 4 | Sep 13 | 228 | 162 | Perks 52; Agrell 21; Lhamo 6; Gorham 10; Other 11 |
| 5 | Sep 13 | 211 | 153, recorded by prior probe | Nunziata 52; Padovani 28; remaining rows require re-acquisition |
| 10 | Sep 14 | 208 | 105 | Malik 52; Nation 13; Engelberg 8; Achampong 5; Other 22 |
| 13 | Sep 14 | 217 | 90 | Moise 41; Ward 26; Lester 10; Other 23 |
| 20 | Sep 15 | 216 | 165, recorded by prior probe | Crawford 39; Berardinetti 21; Kandavel 9 in prior probe |
| 22 | Sep 15 | 207 | 118, recorded by prior probe | Mantas 43; Khatchadourian 23; Wu not separately reported |

First-party releases: [Ward 4](https://poll.forumresearch.com/data/0f87336b-4a32-498e-8411-70b1dd986581Ward%204%20News%20Release.pdf),
[Ward 5](https://poll.forumresearch.com/data/74bddea4-50a4-4c53-a017-52dabdd9cb43Ward%205%20News%20Release.pdf),
[Ward 10](https://poll.forumresearch.com/data/b390026c-ece7-475d-85f0-9cc0e050e9e0Ward%2010%20News%20Release.pdf),
[Ward 13](https://poll.forumresearch.com/data/a199cd17-a268-43ac-a464-8c75787e2657Ward%2013%20News%20Release.pdf),
[Ward 20](https://poll.forumresearch.com/data/00bd353b-b4c5-4efc-ba8a-7e75d5abb630Ward%2020%20News%20Release.pdf),
and [Ward 22](https://poll.forumresearch.com/data/2fc49a81-6baf-49bc-ad01-f22449099fb4Ward%2022%20News%20Release.pdf).

In this audit, web-parsed complete PDFs independently confirmed the Council
tables for Wards 4, 10 and 13. The other three first-party sources were available
as indexed release text but direct retrieval failed with 502/503; their bases
and full tables above remain explicitly attributed to the prior probe. Ward 4
prose says 160 decided/leaning respondents while its table says 162. Ward 5
indexed prose says 112 while the prior extraction recorded 153. Any formal
re-acquisition must preserve and adjudicate these conflicts using table images;
it should not substitute the recruited sample or publicity prose for a table base.

The probe reported named-candidate share error around 11 percentage points,
with large misses for eventual challengers. That is useful evidence that
sampling error alone is inadequate, but its 26 named candidate pairs remain
clustered within six contests. Its claimed six-for-six leader accuracy also
has very little resolution and says nothing about calibration of 70%, 80% or
95% winning chances.

**The reported margin-error SD of 18.5 points must not be imported as a fixed
candidate-pair Gaussian error scale.** The probe compares the gap between the
poll's first and second names with the eventual winner/runner-up gap. Those
challengers differ in several wards. In Ward 4, the poll's second candidate was
Agrell at 21%, whereas the eventual runner-up was Lhamo at 31.6%, polled at 6%.
For the Perks–Lhamo pair the poll margin was 46 points, not the probe's 31-point
poll-top-two gap. Ward 10 similarly changes from Nation to Engelberg. A valid
margin calibration must hold candidate identities fixed or model the complete
joint vote vector and then derive the winner's margin in each draw.

The original PDFs describe random IVR and explicitly limit their sampling
accuracy claim to a point-in-time survey. They have small Council bases and
very sparse young-age cells. September 2026 uses a mixed random-IVR/non-random
online-panel design, larger bases, and unpublished effective sample size/design
effect. Mode change is a real transfer limitation even within the same firm.
The 2022 horizon is also about ten days earlier than the current September 27
poll end (29 days before October 26, 2026). Six observations at a nearly identical
historical horizon cannot estimate a daily campaign-drift curve.

## Six is not an exhaustive historical inventory

The bounded source search found additional first-party 2022 evidence. These are
**acquisition leads, not newly ingested or scored calibration rows**:

| Source | What is confirmed | Remaining work |
|---|---|---|
| [Ward 1 October release](https://poll.forumresearch.com/data/c33fd6af-e9e0-4f30-a67d-5f1c5a335e44Ward%201%20News%20Release%20%282%29.pdf) | Indexed Forum PDF: fielded Oct 17; n 211; Crisanti 53; Genser 12; Minhas 10; Ozzoude 9 | Recover full PDF/table base and compare final ballot/results |
| [Ward 5 October release](https://poll.forumresearch.com/data/4a391231-3daa-4e46-bf07-b2969a3d8998Ward%205%20News%20Release%20%282%29.pdf) | Indexed Forum PDF: fielded Oct 17; n 217; Nunziata 54 | Recover full PDF and decide whether latest sample or full time series is the scoring unit |
| [Ward 10 October post](https://poll.forumresearch.com/post/3134/despite-slight-decrease-in-support--malik-maintains-lead/) | Forum's own post dated Oct 21, with Oct 19 release prose: n 208; Malik 35; Nation 15; undecided 30 | Recover source attachment; establish fieldwork and denominator before using these numbers |

Together with the six September samples, these establish **at least nine
historical Council samples across seven contests**, still **one firm and one
cycle**. Multiple polls of Ward 5 or 10 provide within-contest change, not new
independent election outcomes. This lower bound should replace any claim that
only six historical Council polls exist.

Further original Forum URLs were recovered by following contemporaneous links;
the source bodies were unavailable and their values are not admitted here:
[Ward 3 October](https://poll.forumresearch.com/data/39f8b538-ba12-41bd-949b-9fe053591addWard%203%20News%20Release%20%282%29.pdf),
[Ward 13 October](https://poll.forumresearch.com/data/1fd427fb-bc3a-467e-9799-b06249743aa1Ward%2013%20News%20Release%20%282%29.pdf),
[Ward 16 October](https://poll.forumresearch.com/data/49ae2b2d-076c-4e6b-b5c6-5f00b1f55858Ward%2016%20News%20Release%20%282%29.pdf),
[Ward 23 October](https://poll.forumresearch.com/data/a97b9d54-6e26-4c61-85f1-e424f292559dWard%2023%20News%20Release%20%282%29.pdf),
[Ward 11 September](https://poll.forumresearch.com/post/3118/saxe-leads-slightly-ahead-of-potts-in-ward-11/),
and [Ward 18 October](https://poll.forumresearch.com/post/3136/cheng%27s-support-dipped--o%27brien-ahead-in-willowdale/).
These six distinct-source leads must not simply be added to the nine confirmed
samples without checking for reposts and fieldwork identity. Ward 23 needs an
explicit candidate-availability check before comparison with official outcomes.

A potentially valuable second-firm/second-cycle acquisition is Mainstreet's
September 24–25, 2018 five-ward report, retained on
[Scribd under uploader QuitoMaggi](https://www.scribd.com/document/389640124/Mainstreet-Toronto-28sept2018).
Its report names Wards 5, 7, 13, 19 and 22, IVR landlines/cellphones, recruited
bases 593, 452, 566, 614 and 625, and dependent all-voter/leaner/decided tables.
However, uploader identity and original bytes are not independently authenticated
in this audit, so this is a primary-document recovery lead rather than admitted
first-party calibration evidence. Original pollster publication or an archived
first-party copy should be sought. The Ward 19 question names only three people
and groups everyone else, illustrating why a full-ballot join matters. The 2018
boundary/candidate-pool disruption requires explicit comparability classification:
[Ontario's August 15, 2018 ward regulation](https://www.ontario.ca/laws/regulation/r18408)
establishes the 25-ward system, so pre-change field tests cannot silently be paired
with the final contests.

## Evidence implications

There is enough existing evidence to justify investigating a conservative ward
uncertainty model; there is not yet a retained, validated dataset supporting the
mayoral front page's calibrated predictive claims for Council. Wide bands do not
by themselves solve unidentified error scales, unknown tail allocation, campaign
change or one-cycle transfer. The current five polls cannot provide those answers
because their outcomes are still in the future.

A bounded next step is to re-acquire the six known September 2022 releases,
recover the later 2022 releases above, and authenticate the five 2018 Mainstreet
samples. Match every named option to its final contest and sum official shares
of unnamed candidates only for residual comparisons. Preserve original
percentages and denominator/base metadata. Then pre-register a small joint-share
model and evaluate held-out **contests and cycles**, with repeated samples kept
inside the same fold. Joint outcome draws must sum to 100%; marginal interval endpoints need not. Winner
probabilities must allow an unreported individual candidate to beat reported
names, rather than treating `Other` as a fictitious single candidate or silently
conditioning on only the published names.

Until that work is complete, any exploratory bands should be described as
assumption-based scenarios, not calibrated election-day probabilities or the
pollster's margin of error. No production presentation or model decision is
made by this evidence note.


## Proposed model and presentation

The most useful first target is the home page's **vote-range chart**, scoped to
these five poll-supported wards. A polling-to-election model addresses a different
question from the failed history-only incumbent-defeat models behind
[ADR 0043](../adr/0043-council-v1-is-a-descriptive-race-card-not-a-forecast.md).
That old negative result is not evidence that direct polls cannot improve
prediction. Conversely, a useful poll-supported model would not justify forecasts
for unpolled wards.

Keep the first experiment small: estimate a joint election-day vote distribution
from the latest comparable ward reading, with pooled historical poll-to-result
error. Integrate uncertainty in the error parameters rather than treating the
six-contest error estimate as known. More detailed firm effects, daily drift and
incumbent/open-seat-specific dispersions would need evidence they cannot currently
estimate separately. Additional readings from the same firm must not average away
common polling error; candidate rows and repeated polls stay clustered by contest,
and whole cycles stay together for cross-cycle evaluation. Compare the simplest
joint model with reasonable simpler error specifications and assess vote-share
and fixed-pair margin predictive performance, omitted-candidate outcomes, and
sensitivity to removing individual contests or a cycle. Do not tune the widths to
produce preferred 2026 odds or widen them arbitrarily until historical results fit.

The missing-ballot mapping is essential. The released Results field has 4, 10,
11, 13 and 8 candidates in Wards 3, 4, 13, 19 and 23 respectively. The September
polls name 4, 4, 4, 4 and 5, retaining Other shares of 12%, 16%, 25%, 12% and 7%.
Even Ward 3, naming all four certified candidates, has 12% Other. Thus Other is a
poll-response category, not automatically the eventual votes of an unnamed
candidate group. A forecast needs a defensible observation-to-final-ballot
mapping; the published descriptive reading remains unchanged. Splitting Other
uniformly, assigning it zero, or treating it as one rival would invent evidence.
Sources: [September ingestion audit](../../../toronto-election-poll-tracker-data/docs/research/forum-ward-polls-2026-10-02.md),
Results `results-2026-09-30.2` as pinned in Backend `backend-2026-10-02.2`, and
[Poll Residual / Unmeasured Candidate Tail definitions](../../CONTEXT.md).

If the experiment qualifies, reuse the front-page visual component with a median
and central 80% election-day range, plus the latest raw poll as a separate point.
Use a clear heading such as "What the vote could look like" and identify the
poll date. Do not draw a trend from a single final-field poll. Keep the raw reading
below the chart. A chart of win chances is a separate publication decision and
requires demonstrated robustness of the full-ballot winner calculation; it is not
obtained by checking whether two marginal intervals overlap. Existing Council
publication policy remains unchanged until a new decision is made.

## Why ordinary sampling bars would mislead

The five Council questions have **unweighted** decided/leaning bases 406, 307,
362, 417 and 298, smaller than the recruited sample sizes displayed on the site.
Their weighted bases (416, 331, 370, 395 and 293) are weighted totals, not effective
sample sizes. As a scale illustration only, under an unweighted multinomial
simple-random-sample assumption, the latest top two named candidates' 95% margin
half-widths would be about 7.9, 8.5, 7.6, 7.9 and 9.3 percentage points. Formula:
`1.96 * sqrt((p_a + p_b - (p_a - p_b)^2) / n)`. These are **not valid margins of
error for these mixed-mode surveys**, nor election-day predictive ranges. The
unknown weighting/design effects, selection and nonresponse biases, eventual
voter composition and campaign changes are missing from that calculation.
[AAPOR's disclosure standards](https://aapor.org/standards-and-ethics/disclosure-standards/)
require model-based precision claims for non-probability samples to explain their
assumptions and validation; weighting adjustments also matter for probability
samples. This is why simply attaching conventional binomial bars to the current
site would not satisfy the requested forecast uncertainty.
