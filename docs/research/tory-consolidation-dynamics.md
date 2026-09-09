# Tory endorsements as challenger consolidation

Research date: September 9, 2026. [Interactive consolidation view](tory-endorsement-scenarios/index.html#consolidation) · [Source audit](tory-2023-consolidation-source-audit.md) · [Reproducible inputs](tory-consolidation-inputs.json).

The useful question is how much support an endorsement could concentrate behind one challenger, and whether it could also expand the challengers' combined support. These mechanisms have different ceilings. The 2023 evidence supports examining both, but does not identify a Tory-specific transfer rate.

## What concentrated in 2023?

Define the selected pool as **Bailão + Saunders + Furey + Bradford**. This is an explicit candidate grouping for comparing competition around Bailão. It does not establish the ideology of those voters, imply that everyone opposing Chow belongs to one bloc, or assume that every rival supporter would consider Bailão. Hunter is included in a separate sensitivity calculation; Matlow and the unmeasured field are not silently added to a “right-wing” total.

Let `B` be Bailão's citywide share, `R` the three selected rivals' combined share, `P = B + R` the pool, and `q = B/P` her fraction of that pool. Both `P` and `q` can change.

| Comparison | Bailão | Selected rivals | Combined pool | Bailão / pool |
|---|---:|---:|---:|---:|
| Forum, June 16 → 23 | 13 → 20 | 32 → 29 | 45 → 49 | 28.9% → 40.8% |
| Liaison, June 17–18 → 22–23 | 12 → 17 | 30 → 31 | 42 → 48 | 28.6% → 35.4% |
| Liaison, June 17–18 → 24–25 | 12 → 22 | 30 → 27 | 42 → 49 | 28.6% → 44.9% |

Candidate and pool levels are published percentage points; `q` is our calculation. Sources: [Forum's trend table, p. 1](https://poll.forumresearch.com/data/cb12c41a-8453-40e6-90f1-7558d098f7e1Chow%20lead%20narrowing%20in%20final%20days%20of%20campaign_June%2024%202023.pdf), [Liaison before](https://press.liaisonstrategies.ca/chow-steady-as-she-goes-while-rest-of-field-has-minor-ups-downs/), [first subsequent poll](https://press.liaisonstrategies.ca/chow-leads-in-final-days-of-campaign/), and [final poll](https://press.liaisonstrategies.ca/bailao-surging-but-chow-remains-in-lead/). Bailão's first subsequent Liaison value is 17, resolving the release's contradictory 12 (+5) line against its narrative and detailed table, as documented in the source audit.

The certified result allocates **68.7% of this pool to Bailão**: 235,175 of 342,495 votes. The pool itself receives 47.3% of valid candidate votes. This is substantial eventual concentration, but the endpoint includes pre-endorsement ballots and differs from a survey's sampled electorate. We cannot attribute the poll-to-result change to Tory. [City Clerk's final declaration](https://www.toronto.ca/wp-content/uploads/2023/06/8eef-Declaration-of-Results-for-the-2023-Toronto-By-Election-for-Mayor-Final.pdf).

The source audit reports roughly **51–54% net shrinkage in the rival pool** when pre-endorsement polls are compared with the result. Comparable pre/post polls show about **9–10% shrinkage** by each firm's last poll. Endpoint choice changes the apparent scale dramatically. Neither ratio measures individual switching.

## Separate concentration from pool growth

An exact, symmetric decomposition is:

`change in B = average(P) × change in q + average(q) × change in P`

| Comparison | Gain in Bailão share | Concentration component | Pool-growth component |
|---|---:|---:|---:|
| Forum, first subsequent poll | +7.00 pp | +5.61 pp | +1.39 pp |
| Liaison, first subsequent poll | +5.00 pp | +3.08 pp | +1.92 pp |
| Liaison, final poll versus before | +10.00 pp | +7.43 pp | +2.57 pp |

These are accounting components of the displayed rounded values, **not causal components or counts of voters who switched**. In particular, Liaison's first subsequent poll has a growing rival pool. A larger `q` can coexist with rivals losing no net support because the recipient attracts support from elsewhere. Gross transfers in either direction remain unidentified by repeated cross-sectional totals.

Another descriptive statistic is the fraction of the remaining concentration gap closed:

`g = (q_after − q_before) / (1 − q_before)`

This is **16.8% in Forum**, **9.6% in the first Liaison comparison**, and **22.9% through Liaison's final poll**. With Hunter added to the pool, the figures are 15.5%, 9.3%, and 21.5%. The qualitative concentration result survives this modest pool-definition change. Broader groupings would ask a different question.

Only under a fixed pool, no offsetting switches, and support moving solely from rivals to Bailão could `g` be interpreted as a rival-transfer fraction. Those assumptions are not established here. It can provide a transparent scale for scenarios, rather than a fitted endorsement coefficient.

## Was concentration already increasing?

Yes. A short pretrend calculation uses only observations in the 14 days before June 21, fits an unweighted line to `q` at fieldwork midpoints, and projects to each firm's first subsequent poll:

| Firm | Pre-event polls | Projected share of pool | Observed share of pool | Excess |
|---|---:|---:|---:|---:|
| Forum | 2 | 32.8% | 40.8% | +8.0 pool percentage points |
| Liaison | 3 | 31.1% | 35.4% | +4.3 pool percentage points |

Relative to those projected concentration levels, the remaining-gap closure is **12.0% and 6.3%**, respectively. These are highly fragile two/three-observation extrapolations, not confidence bounds. They use a different denominator from the earlier [citywide support pretrend](endorsement-identification/README.md); the two residual ranges must not be added together. Early Liaison readings are retained in the canonical historical source tables and identified in the input file; their publisher-hosted Scribd documents could not be retrieved afresh during this extension.

Tory and the Star endorsed Bailão on June 21. The residual combines their potential effects, interactions, other campaign developments, sampling variation and trend-model error. If Tory caused strategic coordination, that coordination is part of his total effect; it should not be automatically subtracted as an unrelated explanation. Independently occurring coordination is a competing explanation. The available data do not distinguish them. [Event chronology and campaign-primary evidence](john-tory-2023-endorsement-evidence.md).

## Application to Bradford and Alexander

Let `r` be a **chosen net fraction of the other challenger's baseline support** moving to the endorsed candidate:

`recipient_after = recipient_before + r × rival_before`

`rival_after = (1 − r) × rival_before`

Chow and the residual remain fixed in this scenario. The transfer is already net and realized; the separate point-shift and timing controls do not multiply it again. The common slider compares equivalent assumptions, without asserting that Tory endorsing either candidate would generate the same `r`.

| Baseline | Bradford's starting share of pair | Gain to Bradford if half of Alexander support moves | Gain to Alexander if half of Bradford support moves | Full-consolidation ceiling |
|---|---:|---:|---:|---:|
| Pallas, August 19–21 | 82.9% | +4.05 pp | +19.63 pp | 47.35% versus Chow 50.05% |
| Liaison, August 14–16 | 77.6% | +5.45 pp | +18.81 pp | 48.51% versus Chow 48.51% |

These are calculations from the explorer's **dated** [Pallas](https://pallas-data.ca/2026/08/25/pallas-toronto-poll-chow-50-bradford-39-alexander-8/) and [Liaison](https://press.liaisonstrategies.ca/toronto-chow-49-bradford-38-voters-want-balance-with-ford/) inputs, not September 9 estimates. The source-detail values and provenance remain in the export. Published totals of 100.1 and 101 are scaled to 100 for transfer arithmetic; ratios within the pair are unaffected by that scaling. Decimal precision displays the calculation, not polling accuracy.

Bradford already has a larger fraction of his two-candidate pool than Bailão had of the selected four-candidate pool even at the certified 2023 endpoint. Alexander needs **35.5–39.7% of Bradford's support just to tie him within the pair**. Reaching Bailão's final 68.7% concentration would require about **59.6–62.2%** of Bradford's support. These comparisons expose the difference between reinforcing an established leading challenger and replacing that challenger. They do not prove a common psychological response across candidates or years.

For a rough scale, applying a **10–17% assumed rival transfer** produces only about **0.8–1.9 points for Bradford**, versus **3.8–6.7 for Alexander**, across the two baselines. The historical gap-closure statistics motivate examining this scale; they do not identify it as Tory's likely effect. The explorer also includes zero through full consolidation without assigning probabilities.

**Pure consolidation has a hard ceiling conditional on these baselines.** It leaves either recipient 2.70 points behind Chow in Pallas and merely tied in Liaison's rounded figures. After full Pallas consolidation, a further 1.35 points switching from Chow would tie the lead: the recipient gains that amount while Chow loses it. A strict lead requires more. Additional support from Other, undecided voters or differential turnout has different arithmetic and cannot be substituted into that threshold without changing the model.

The [Alexander entry analysis](alexander-entry-dynamics.md) also cautions against treating the pair as a permanently closed pool: the largest net entry-period decline was in “someone else.” A fuller conditional model should allow both internal reallocation and changes in the combined pool. Strategic viability could also create feedback or different transfer rates depending on which candidate Tory endorses. This single historical event cannot estimate those feedback parameters, so the explorer shows the transfer fraction, resulting concentration and outside-pool requirement directly.

## Reproduction and boundaries

Run `.venv/bin/python scripts/analyze_tory_endorsement.py` from the backend repository. It reads the dated canonical 2026 inputs and the cited research-only historical transcription; the latter's SHA-256 is exported alongside its values. It emits the historical comparisons, pretrends, Hunter sensitivity, and **404 consolidation scenarios** in [JSON](tory-endorsement-scenarios/scenarios.json). Every emitted scenario is checked for nonnegative shares and conservation of 100 points. Tests cover asymmetric gains, exhausted pools, leading-challenger thresholds, common ceilings, and historical accounting identities; browser checks cover controls and mobile layout.

No causal effect, confidence interval or win probability is fitted. No canonical data, forecast feed or production model is updated. The repository's [validation requirement for political signals](../adr/0007-admit-political-signals-only-by-validation.md) still applies before any such variable could enter a forecast.
