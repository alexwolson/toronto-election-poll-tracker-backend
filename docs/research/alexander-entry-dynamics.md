# What Alexander's entry tells us about vote-source dynamics

Research and calculations: September 9, 2026.

**The entry evidence improves the scenario model by separating three sources: Chow, Bradford and the “someone else” response.** The largest net decline around Alexander's entry was in “someone else,” while the two strongest comparisons disagree about the balance between the named candidates. Entry patterns therefore support multiple allocation assumptions and an explicit limit on the remaining Other pool. They do not identify individual switching probabilities or the sources of a future Tory endorsement gain.

The [interactive scenario report](tory-endorsement-scenarios/index.html) now includes these comparisons and a separate illustration of further Alexander growth. It uses the selected August baseline, effect and retention assumptions, allowing Other to decline. The original named-candidate transfer scenarios remain separate.

## Timing and the best comparisons

Alexander's [campaign launch was July 28](https://chrisalexander.ca/updates-press-releases/chris-alexander-launches-campaign-for-mayor-of-toronto), and the [City registry records July 29 nomination](https://www.toronto.ca/data/elections/candidate_list/mayorCandidates_2026.json). Public discussion of a possible run preceded those dates. The [source audit](chris-alexander-entry-source-audit.md) distinguishes consideration, announcement, nomination and survey dates.

| Comparison | Chow | Bradford | Alexander | Someone else |
|---|---:|---:|---:|---:|
| Forum July 29, initial ballot | 48% | 36% | Not named | 17% |
| Forum July 29, Alexander added | 47% | 32% | 11% | 10% |
| **Displayed difference** | **−1 pp** | **−4 pp** | **11% as a newly named option** | **−7 pp** |
| Liaison July 24–26, before launch | 49% | 41% | Not named | 10% |
| Liaison August 4–5, after launch | 47% | 40% | 10% | 3% |
| **Displayed difference** | **−2 pp** | **−1 pp** | **10% as a newly named option** | **−7 pp** |

Sources: [Forum detailed tables, pages 3–4](https://www.forumresearch.com/news/attachments/fb26f543-8af1-44fa-b85b-3e7592b84b8d.pdf), [Liaison July release](https://press.liaisonstrategies.ca/toronto-chow-49-bradford-41-city-split-on-direction/), [Liaison August release](https://press.liaisonstrategies.ca/toronto-chow-47-bradford-40-alexander-10/). All rows are the relevant decided/leaning presentations. Canonical source locators, reported bases and hashes are retained in the [JSON export](tory-endorsement-scenarios/scenarios.json), under `alexander_entry`.

Forum's questions were sequential within one survey, both after the launch. The second explicitly added Alexander. This helps control differences between separately recruited samples, but is not a randomized experiment; its decided/leaning bases also differ (887/888 unweighted/weighted initially, 889/890 subsequently). Detailed tables govern the numbers above because release prose has two one-point discrepancies. The first table sums to 101%, the second to 100%. No direct choice-by-choice transition table was published. See the [source audit](chris-alexander-entry-source-audit.md) for the full verification.

Liaison supplies a calendar before/after comparison from two separate 1,000-person samples. Those contain ordinary sampling and campaign changes as well as the effect of explicitly naming Alexander. Its July survey preceded the launch but followed public speculation about his candidacy. An unnamed option is not an observation of zero underlying Alexander preference: someone already favoring him could have answered “someone else.”

## Check the denominator and the next observation

Liaison's all-voter comparison is:

| Fieldwork | Chow | Bradford | Alexander | Other | Undecided |
|---|---:|---:|---:|---:|---:|
| July 24–26 | 39% | 33% | Not named | 8% | 20% |
| August 4–5 | 38% | 32% | 8% | 3% | 20% |
| August 14–16 | 39% | 30% | 9% | 2% | 19% |

Sources: July and August releases above, and [Liaison's August 20 release](https://press.liaisonstrategies.ca/toronto-chow-49-bradford-38-voters-want-balance-with-ford/). Printed totals are 100%, 101% and 99%, respectively; they are preserved rather than silently balanced. The unchanged initial 20% undecided total does not imply nobody moved from undecided into Alexander: offsetting movements can leave the total unchanged.

The next decided/leaning observation is also informative: **47/40/10/3 becomes 49/38/11/3** in Chow/Bradford/Alexander/Other order. Bradford falls while Chow and Alexander rise and Other stays at 3. The raw movement is different from the entry pattern. It does not show how many Bradford voters switched to either rival, and modest differences remain subject to survey error. A permanent one-way allocation from Other would fail to describe this observed sequence.

Pallas's August survey is useful as an alternative current baseline in the explorer, but it is not substituted for a missing nearby Pallas pre-entry sample. Comparing pollsters across the entry date would add house effects to the other changes.

## Net changes do not reveal gross transfers

Consider Liaison's decided/leaning margins. Both of these hypothetical transition stories produce exactly the same 49/41/10 initial and 47/40/10/3 final totals:

- **Only switches into Alexander:** 2 points from Chow, 1 from Bradford, 7 from Other.
- **All Alexander's named support from Bradford:** 10 points from Bradford to Alexander, offset by 2 points from Chow to Bradford and 7 from Other to Bradford.

They are mathematical examples, not claims about voters. Even if the two polls represented the same fixed population perfectly, the margins alone would not distinguish them. In reality they are different samples and the choice field changes. This is why a one-point net Bradford decline does not prove that only one point of Alexander's support came from him.

## A transparent allocation assumption for the scenario explorer

For an illustrative accounting allocation, impose **no switches between the existing options and no changes in who is decided**. Separately scale each rounded decided/leaning reading to 100, then assign its existing-category net losses to the newly named Alexander category:

`weight[source] = (normalized before share − normalized after share) / Alexander's newly named share`.

This fits the two initial comparisons by construction. The zero used for Alexander in the initial response vector means the option is absent, not zero latent preference. Normalization solves arithmetic rounding, not changing respondents or question-order effects. It is one analyst convention; precise small fractions, especially Forum's Chow fraction, are sensitive to rounding.

| Assumed accounting profile | Chow | Bradford | Other |
|---|---:|---:|---:|
| Forum ballot comparison | about 5% | about 33% | about 62% |
| Liaison entry interval | 20% | 10% | 70% |

**These percentages allocate an assumed gain; they are not measured origins of Alexander voters.** The disagreement about Chow versus Bradford is retained as two separate profiles, not averaged into a supposedly stable transition parameter. The much more consistent feature is a large net reduction in the Other response when Alexander becomes named.

For further growth of Δ points, the illustration applies:

`Alexander' = Alexander + Δ; source' = source − weight[source] × Δ`.

The maximum feasible Δ is `min(source share / source weight)` over positive weights. This is a fixed-denominator response-share calculation. The Other category is not a candidate, an undecided pool, a nonvoter pool or a known collection of transferable ballots. The alternative assumption simply permits its poll share to decline as more respondents choose a named candidate.

## Why this changes the dynamics

The August baselines contain only 2.6% Other in Pallas's published table and 3% in Liaison's. After their disclosed rounding normalization, repeating a profile that allocates 62–70% of every gain to Other exhausts that category quickly:

| August baseline | Forum profile: maximum additional gain | Liaison profile: maximum additional gain |
|---|---:|---:|
| Pallas | 4.18 pp | 3.71 pp |
| Liaison | 4.78 pp | 4.24 pp |

These are **limits of the copied allocation under a fixed baseline**, not upper bounds on Alexander's support or Tory's effect. A larger gain could involve a different mix, changes in who is decided, or turnout. The illustration marks an exhausted source as infeasible instead of silently sourcing the shortfall elsewhere. Select +3 and then +6 with full retention in the explorer to see the constraint operate. With half retention, the net shift is halved before checking it.

For a six-point gain, for example, the Liaison entry allocation would require 4.2 points from Other. Neither August baseline has that much. Treating the entire entry boost as repeatable would conceal that constraint.

## What this supports for Tory scenarios

The model should distinguish **recognition of a newly named candidate**, **competition among named candidates**, and **changes in undecided participation or turnout**. Those mechanisms need different denominators and cannot all be represented as Bradford-to-Alexander transfers.

The existing explorer now tests the first two within their stated assumptions. Its original scenarios hold Other fixed and transfer between named candidates. The additional Alexander-only illustration tests a copied entry allocation including Other. It does not reverse entry to predict a withdrawal, apply Alexander's profile to Bradford, or interpret either entry comparison as Tory endorsement response. Negative shifts are unavailable in the new illustration; the original adverse endorsement scenarios remain available.

A stronger dynamic model would update the full response vector over time, constrain nonnegative shares, allow offsets between candidate categories, and model undecided respondents separately before deriving decided shares. Respondent-level Forum cross-tabs would directly improve observed transition estimates under its questionnaire sequence. Those estimates would still need uncertainty about how a Tory endorsement differs from candidate naming and how the campaign changes after entry. No messages were sent to request private data.

## Reproduction and verification

Run `uv run python scripts/analyze_tory_endorsement.py` from the backend repository. The [analysis module](../../backend/analysis/alexander_entry.py) reads existing canonical readings through the report builder; no canonical input is changed. The JSON contains five descriptive comparisons and 120 additional growth illustrations, alongside the original 360 endorsement scenarios. The CSV still contains the original named-candidate scenario grid.

Tests cover source values and changing bases, preservation of the absent Alexander option, the two alternative transition stories, category conservation, invalid inputs, exhausted source pools and refusal to infer reverse flows. The generator verifies every feasible output. No production model, forecast probabilities, ingestion, release pin or deployment was changed.
