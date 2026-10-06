# Existing mayoral measurements: design classification

Completed 2026-09-12. **Design annotations, not forecast eligibility rules.**
The user has taken Borealis out of this work. This classification uses the
normalized measurements already present in the repositories; it does not depend
on retrieving another dataset or changing the live forecast.

## What was classified

Every one of the **327 retained reading rows** now has a question-role
classification, denominator interpretation, explanation and review notes in the
[complete classification register](mayoral-measurement-classification-2026-09-12.json).
The register also includes all **146 parent sample records**. Of these, 145 have
readings; the blocked Abacus January 2026 sample has none and remains an explicit
gap, not an invented measurement.

There are 311 citywide mayoral readings, five ward-level mayoral readings and
11 council readings. Multiple rows from one survey are not additional independent
polls. Separate sample identifiers also do not prove absence of respondent reuse.

| Question role | Historical citywide | Current-cycle citywide | Ward mayoral | Council | Total |
|---|---:|---:|---:|---:|---:|
| Campaign vote intention | 146 | 38 | 5 | 5 | 194 |
| Alternative offered ballot | 105 | 11 | 0 | 6 | 122 |
| Conditional leaning follow-up | 2 | 0 | 0 | 0 | 2 |
| Routed subgroup | 1 | 0 | 0 | 0 | 1 |
| Context only | 0 | 1 | 0 | 0 | 1 |
| Question scope unresolved | 6 | 1 | 0 | 0 | 7 |
| **Total** | **260** | **51** | **5** | **11** | **327** |

The **184 citywide campaign readings belong to 116 parent samples**: 97 historical
and 19 current-cycle samples. This is a useful starting body of trajectory
evidence, not a claim that there are 116 independent, directly interchangeable
observations. Some samples also have alternative questions or unresolved rows.
The 116 citywide alternative readings belong to 38 samples; those sample counts
overlap and must not be added.

## Meaning of the classifications

**Campaign vote intention** means the retained source describes an ordinary
campaign preference question or a reporting version of it. It does not certify
that the field matches today's candidates, that every offered choice is known,
or that a denominator is fully documented. Early questions involving potential
candidates remain measurements of their specified fields. A later withdrawal
does not retrospectively turn an ordinary contemporary question into a hypothetical.

**Alternative ballot** means source evidence establishes a deliberately different
offered field, restricted match-up, addition or replacement. Such a reading may
be particularly relevant to the current field. It needs an observation model for
that field and its question context; the label is not a rejection. Neither a
two-candidate published table nor the phrase “if the election were held today”
alone establishes a forced head-to-head question.

**Conditional follow-up** measures leaning among respondents initially unsure.
**Routed subgroup** measures responses among a specified preceding-answer group.
Neither is an unconditional citywide preference distribution. A combined
decided-and-leaning topline remains a campaign or alternative-field reading, not
an isolated conditional follow-up just because leaning was asked.

**Context only** currently applies to the CanadaPulse consideration question.
It describes consideration rather than a direct vote choice. **Unresolved**
preserves a specific ambiguity about question scope; it does not invalidate
companion readings or prevent progressing with the model design.

Geography is a separate axis. Ward mayoral questions could inform a geographic
extension with explicit population relationships, but are not citywide samples.
Council questions concern different contests and candidate sets; they are not
extra mayoral trajectory observations.

## Denominators and dependence

| Interpreted denominator | Readings |
|---|---:|
| All respondents, within the stated population | 172 |
| Decided only | 55 |
| Decided plus leaners | 57 |
| Another explicitly source-defined base or transformation | 7 |
| Not reported | 36 |

These annotations preserve literal denominator text alongside the interpretation.
For example, the historical EKOS and Angus Reid rows are stored under the broad
`decided_respondents` type but explicitly include leaners. Conversely, a table
after leaners are allocated can still retain undecided respondents and therefore
use an all-respondent denominator. “All” means the stated population, which may
already be turnout-screened; it does not always mean everyone originally recruited.

Each row retains its parent sample, sibling count, reported question ordering,
fieldwork and publication timing, bases, population, offered-choice status,
coverage, rounding precision and source locator. The sample is the minimum known
dependence group. Repercentaging one table or asking another question of the same
respondents must not create independent sampling information. Different question
bases do not establish independent recruitment.

The archive also has overlapping EKOS October 2010 fieldwork windows. Until the
recruitment relationship is established, separate IDs must not be taken as proof
of independence. The register preserves this issue without inventing a correlation.

## Cases that matter to this design

| Existing measurement | Classification and implication |
|---|---|
| Forum July 29, 2026: original question and Alexander-added question | Campaign and alternative-ballot readings from one sample. The Alexander question can inform the three-candidate field. Their difference describes a same-survey question contrast, not a separate new poll or identified individual voter transfers. |
| Pallas August 2026: all-voter, leaner-adjusted and decided/leaning tables | Two campaign reporting views and one unresolved wording conflict. Preserve the sample and companion evidence; the issue concerns interpretation of one table. |
| Liaison July 2025: with/without Tory questions | Explicit paired alternative fields. They can inform field sensitivity; neither is automatically a measurement of the eventual 2026 field. |
| 2014 prospective fields and candidate replacements | Many explicit alternatives account for 100 of that cycle's 148 reading rows. Rich scenario coverage is not 148 independent time observations. |
| Nanos July 2014 and Ipsos 2023 leaning-only questions | Conditional evidence among initially unsure respondents; dependent combined toplines retain their own denominator semantics. |
| Mainstreet April 13, 2023 no-Chow question | Routed among preceding Chow voters, with a base of 112. It is not the city's unconditional no-Chow vote. |
| DART October 2018 | Explicit Tory–Keesmaat head-to-head; the source itself cautions against treating it as the actual voting-day outcome. |
| Decima and Léger 2006 partial reporting | Campaign measurements with incomplete reporting, and for Léger an unknown denominator. Old “descriptive only” notes do not settle their use in a new model; missing responses must not be manufactured. |

The current five production samples remain five samples. These design annotations
do not remove Forum's Alexander question or Pallas's survey from the forecast,
change current weights, or create a new publication gate.

## Specific issues retained for source interpretation

Seven question-scope flags are narrow and individually identified:

- Forum June 23 and July 2, 2014: Rob Ford appears in table labels/responses while
  Doug Ford appears in printed question wording.
- Forum August 26, 2014: the three-way table omits Soknacki while its printed
  question includes him.
- Forum January 22, February 9 and February 24, 2014: the retained context does
  not firmly identify the ordinary baseline among the early alternative fields.
- Pallas August 21, 2026 decided/leaning: wording introduces “different candidates”
  while the published names match companion tables. The register does not
  silently assume a template error or invent an unreported candidate field.

Separately, **19 Mainstreet rows** (six in 2014, three in 2018, ten in 2023) explicitly label a
decided denominator while generic extraction notes say including-undecided.
The explicit denominator is provisionally retained and the conflict flagged.
Resolving it can refine the observation likelihood without changing the question's
campaign classification.

The register preserves **31 numeric zero response values** and **20
offered-but-unpublished candidate entries** as distinct states. Some earlier
historical rows also contain residual or combined “other” categories created in
normalization. These are not all independently source-published Other responses.
The new likelihood must distinguish them rather than infer precise observed
counts or treat the entire residual as unmeasured election-day candidates.

Unknown tested-choice completeness, unavailable design effects, incomplete
question wording and date proxies remain source limitations, not automatic
grounds to throw out the whole campaign. They require explicit treatment at the
relevant observation or parameter level.

## Consequence for the next design discussion

We have enough classified evidence to specify the observation model now. The next
decision is how a latent candidate-support vector produces each reported table:
its offered field, undecided/leaning treatment, population and denominator, with
one coherent sampling contribution per recruitment group.

The ordinary campaign readings provide the initial basis for learning trajectories
and firm deviations. Alternative fields provide different observations and may
inform candidate substitution, but aggregate contrasts cannot identify a detailed
person-level transfer matrix. Seven election outcomes remain seven outcomes for
learning shared election discrepancy, however many within-campaign tables exist.

We should next settle a small set of observation relationships and the parameters
they require, distinguishing relationships supported by the archive from those
that need pooling or assumptions. Classification does not itself settle the
likelihood, produce new forecast odds or qualify a model.

## Provenance and verification

Primary local evidence is the Polling repository's
`data/raw/polls/historical_mayoral/` and `data/raw/polls/` sample, reading, response,
document and linkage tables. Historical Backend copies are not counted again.
The JSON register records SHA-256 hashes for all ten input tables and retains
every original reading row plus response summaries and notes. Source documents
are traceable through each row's document ID and locator and the
[existing evidence index](mayoral-data-index-2026-09-12.md).

Question classifications were reviewed against stored wording, scenario labels,
denominator text, provenance notes and companion readings. This pass did not
reopen every source PDF or reconcile the flagged conflicts, so it is a documented
design classification rather than a fresh extraction certification.

Component annotation records:
[2014](mayoral-measurement-annotations-2014-2026-09-12.json),
[2023](mayoral-measurement-annotations-2023-2026-09-12.json),
[other historical cycles](mayoral-measurement-annotations-other-history-2026-09-12.json),
[current cycle including wards](mayoral-measurement-annotations-current-2026-09-12.json).

Checks: every retained reading has exactly one annotation; every annotation joins
to its parent sample; all class, scope and denominator totals reconcile; the
blocked sample has no invented reading; zero and unpublished counts match the
source tables. No production code or source data was changed, and no model was fit.


## September 14 source-recovery update

The live design register now contains 332 readings: five newly recovered middle
Mainstreet 2023 publications, each attached to its existing sample. Historical
canonical readings increase from 260 to 265 and responses from 1,531 to 1,581;
no respondents, sample dates, candidate identities or existing response values
change. The new publications are campaign vote intention on the full respondent
base, with an explicitly inferred combined initial-plus-leaning interpretation.
The earlier summary above describes the original September 12 inventory.

The [source decision](mayoral-mainstreet-source-target-decision-2026-09-14.md)
records the evidence. The [integration checkpoint](mayoral-mainstreet-recovery-results-2026-09-14.md)
records the migration and revised model mappings. Original classifications and
canonical input rows are preserved in the checkpoint's before directory.
