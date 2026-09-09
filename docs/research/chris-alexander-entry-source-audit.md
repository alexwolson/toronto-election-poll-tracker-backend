# Chris Alexander's 2026 entry: chronology and paired-ballot evidence

**Research date:** 2026-09-09
**Purpose:** Assess whether Alexander's entry informs vote-source assumptions in the [Tory endorsement scenarios](john-tory-2023-endorsement-evidence.md). Source audit only; no production inputs changed.

## Finding

Alexander publicly launched his campaign **July 28, 2026** and filed his nomination **July 29**. Forum interviewed on July 29 and asked a ballot question followed by a similar question explicitly adding Alexander. This is better evidence about the immediate association between candidate naming and support than comparing unrelated polls across several weeks. It is **not** an observed individual transfer matrix, a randomized experiment, or a clean measurement of the effect of announcing his candidacy.

The detailed tables show Bradford's aggregate share declining more than Chow's when Alexander is named, while the largest decline is in **Someone else**. This supports examining asymmetric competition between the challengers. It does not justify assuming all Alexander voters came from Bradford, assigning precise donor fractions, or reversing the comparison to predict where voters would go under a Tory endorsement.

## The dates represent different events

| Event | Verified date and evidence | Implication for a before/after analysis |
|---|---|---|
| Public consideration of a run | A July 10 CP24/CTV report quotes Alexander confirming by email that he was seriously considering running. His own website republishes that report, with its own page dated July 21. [Campaign-hosted report](https://chrisalexander.ca/in-the-news/https/wwwcp24com/local/toronto/2026/07/10/former-immigration-minister-chris-alexander-considering-run-for-toronto-mayor) | Late-July pre-launch polling was already conducted after public discussion of a potential candidacy. July 28 was not necessarily voters' first exposure. |
| Public campaign launch | **July 28** is the dateline and stated launch date of Alexander's own announcement. [Campaign release](https://chrisalexander.ca/updates-press-releases/chris-alexander-launches-campaign-for-mayor-of-toronto) | Use July 28 for the announcement event; the release does not establish each respondent's exposure time. |
| Nomination filed | The City's public candidate JSON returns `dateNomination: "29-Jul-2026"` for `firstName: "Chris"`, `lastName: "Alexander"`. Freshly read September 9. [City registry](https://www.toronto.ca/data/elections/candidate_list/mayorCandidates_2026.json) | July 29 is the official filing date, not the first public announcement date. |
| Forum interviews / report | **July 29 fieldwork; July 30 release dateline.** [Forum report, pp. 1–2](https://www.forumresearch.com/news/attachments/fb26f543-8af1-44fa-b85b-3e7592b84b8d.pdf) | Both ballot readings come from interviews after the public launch. The ballot omitting Alexander is not an actual pre-entry survey. |

The campaign-hosted July 10 article is a republication of reporting about Alexander's email, not an independently retained copy of the email. The original CTV/CP24 page was not retrievable in this audit. It establishes documented pre-launch discussion with that provenance limitation. The formal launch and nomination dates have separate first-party campaign and City confirmation.

The City's current candidate page loads its list dynamically; the JSON endpoint supplied the actual nomination record. The retained ingestion also records `Chris,Alexander,Active,2026-07-29` in [mayor_registered.csv](../../../toronto-election-poll-tracker-data/data/raw/candidates/mayor_registered.csv), fetched August 26 according to its sidecar. The fresh City lookup agrees.

## What Forum actually published

The report describes one **1,011-person IVR sample**, 78% cellphone and 22% landline. Published mayoral readings are labelled **Decided/Leaning** and weighted by age and gender. The report quotes ±4.0 points for its full sample, not a confidence interval for the difference between the paired questions. [Forum methodology and tables, pp. 2–4](https://www.forumresearch.com/news/attachments/fb26f543-8af1-44fa-b85b-3e7592b84b8d.pdf).

| Detailed table | Chow | Bradford | Alexander | Someone else | Unweighted decided/leaning n | Weighted base |
|---|---:|---:|---:|---:|---:|---:|
| Initial ballot, p. 3 | 48% | 36% | Not individually named | 17% | 887 | 888 |
| Additional-candidate ballot, p. 4 | 47% | 32% | 11% | 10% | 889 | 890 |
| Raw displayed difference | −1 pp | −4 pp | +11 pp as a named option | −7 pp | +2 | +2 |

These figures are transcribed from the detailed tables and visually checked against the retained PDF. **The prose differs:** page 1 says Bradford 35% on the initial ballot and Someone else 11% on the expanded ballot. The detailed table has 36% and 10%, respectively. The [existing reading extraction](current-mayoral-reading-extraction.md) and canonical response records already preserve the table figures. A calculation must not mix prose and table values to manufacture a balanced flow.

The initial table totals 101%, while the expanded table totals 100%. Rounded marginal percentages and changing eligible bases are not exact counts that can be subtracted person by person. Alexander's initial entry is **not observed zero support**: people preferring him could have selected Someone else or remained undecided before hearing his name explicitly.

## Sequential wording, not documented randomization

The second question begins: **“Now I'd like to ask a similar question with one additional candidate in the race.”** It then repeats the current-vote and leaning questions with the expanded field. This supports classification as sequential ballot questions in a shared interview sample. The report does not describe a randomized split sample, randomized question order, counterbalancing, or a randomized endorsement message. [Forum questionnaire, pp. 3–4](https://www.forumresearch.com/news/attachments/fb26f543-8af1-44fa-b85b-3e7592b84b8d.pdf).

A fixed prompt that highlights a newly added candidate can create awareness or salience within the interview. The common sample removes much between-poll sampling variation, but it does not remove possible question-order effects. Moreover, the two decided/leaning bases differ, so the published marginals are not even explicitly restricted to respondents giving a decided/leaning answer to both questions.

For the before/after calendar analysis, classify July 29 as **post-launch, immediately around official filing**, with unknown individual exposure. For the ballot comparison, classify both readings as **dependent readings from one post-launch sample**. They must not count as two independent polls or as an actual pre/post campaign time series.

## What the cross-tabs do and do not show

The nine-page report provides each ballot by age, gender, former municipality, and household income, followed by Chow approval questions. It does **not** publish initial choice × expanded-ballot choice, choices among the same continuously decided respondents, second choices of Alexander supporters, or individual response records. [Complete Forum report](https://www.forumresearch.com/news/attachments/fb26f543-8af1-44fa-b85b-3e7592b84b8d.pdf).

Even its subgroup marginals resist a universal Bradford-to-Alexander story. In East York, Bradford is 30% then 31% while Alexander registers 11%; among ages 18–24, Bradford is 12% then 15% while Alexander registers 17%. Those are small and changing subsets, not statistically established subgroup effects. They illustrate why a candidate gaining in a marginal table does not reveal another candidate's individual losses. [Forum subgroup tables, pp. 3–4](https://www.forumresearch.com/news/attachments/fb26f543-8af1-44fa-b85b-3e7592b84b8d.pdf).

Net marginals leave gross movements unidentified. Bradford could lose respondents to Alexander while gaining others from Chow or Someone else; new decided respondents could enter while others become undecided. The same net changes can be produced by many such combinations. With respondent-level paired data, one could estimate **observed conditional transitions under this questionnaire sequence**, but those would still not be randomized effects of entry or a Tory endorsement.

## Consequences for endorsement scenarios

- **Use the pairing as a qualitative and descriptive constraint.** It makes scenarios in which Alexander competes more with Bradford than Chow worth examining, alongside recruitment from the residual/undecided pool. Preserve that pool instead of forcing Alexander's entire support to come from the other two named candidates.
- **Treat normalized losses only as arithmetic.** Scaling the first table to sum to 100 resolves its rounding total for a scenario calculation. It does not recover missing joint responses, equalize the two decided bases, or estimate donor probabilities. Dividing Bradford's net decline by Alexander's share would conflate a net change with gross recruitment.
- **Keep entry, withdrawal, and endorsement distinct.** Naming Alexander in an interview is not a signal from Tory. Reversing an entry comparison also need not describe a withdrawal: exposure, preferences, candidate viability, and the campaign can change after entry.
- **Use independent same-firm pre/post polls as corroboration with their own limitations.** Actual temporal changes contain campaign trends and sample changes as well as any effect of entry. They can constrain plausible stories, but adding them to the paired ballot does not by itself identify individual flows or the effect of Tory's endorsement.

The present evidence supports an evidence-informed sensitivity analysis with multiple vote sources. It does not supply a defensible fixed transfer matrix.

## Retained source and verification

- Primary [release page](https://www.forumresearch.com/news/2026/07/chow-leads-bradford-maintains-advantage-with-alexander-added-to-ballot) and [nine-page PDF](https://www.forumresearch.com/news/attachments/fb26f543-8af1-44fa-b85b-3e7592b84b8d.pdf).
- Retained [Forum PDF](../../../toronto-election-poll-tracker-data/data/source_documents/current_mayoral/forum_2026-07-29_full.pdf), SHA-256 `3e00274591e7db0191b71b3ffe05c4733a2d6e48b630459bf58d0f09e62bdad9`.
- Text extraction inspected across all nine pages; ballot pages 3–4 rendered and visually checked. Canonical reading IDs: `forum_20260729_mayor_primary` and `forum_20260729_mayor_alexander`.
