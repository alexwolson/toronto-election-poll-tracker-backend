# Can we separate Tory's contribution to Bailão's 2023 surge?

Research and calculations: September 9, 2026.

**We can construct an assumption-dependent approximation. The strongest current numerical anchor is about four percentage points of movement above Bailão's recent trend in the first post-endorsement polls.** That residual includes the Star endorsement, Tory's endorsement, any interaction, other campaign developments and extrapolation/survey error. It is not a measured Tory effect.

Council endorsements expand the comparison set substantially. An initial calculation across the full recorded 2022 Star council slate does **not** reveal a consistent positive advance-to-election-day shift. It exposes why a voting-mode contrast needs adjustment before it can inform the newspaper component.

## 1. Remove the momentum already visible before June 21

Fit a straight line separately within each pollster using only observations in the 14, 21 or 28 days before June 21. Use fieldwork midpoints and published shares, with equal weight per poll. Project that line to the first wholly post-event poll. Do not pool firms, use rival candidates as untreated controls, or include post-event data in the baseline fit. These windows are exploratory sensitivity choices, not a preregistered design.

| Firm | Pre-event window | Number of pre-event polls | Projected support | First post-event support | Excess over projection |
|---|---:|---:|---:|---:|---:|
| Forum | 14 days | 2 | 16.0% | 20% | **4.0 pp** |
| Forum | 21 days | 3 | 15.3% | 20% | **4.7 pp** |
| Forum | 28 days | 4 | 13.5% | 20% | **6.5 pp** |
| Liaison | 14 days | 3 | 13.4% | 17% | **3.6 pp** |
| Liaison | 21 days | 4 | 13.0% | 17% | **4.0 pp** |
| Liaison | 28 days | 5 | 11.8% | 17% | **5.2 pp** |

Forum's decided/leaning inputs are May 26: 9%; June 2: 8%; June 9: 10%; June 16: 13%; first post-event June 23: 20%. They are all printed in its [final primary trend table, page 1](https://poll.forumresearch.com/data/cb12c41a-8453-40e6-90f1-7558d098f7e1Chow%20lead%20narrowing%20in%20final%20days%20of%20campaign_June%2024%202023.pdf). June 16 is a research transcription from that table; its standalone report is missing from the canonical corpus.

Liaison's decided-voter inputs are [May 26–27: 10%](https://press.liaisonstrategies.ca/chow-continues-lead-as-saunders-hunter-tied-at-second/), [June 3–4: 9%](https://press.liaisonstrategies.ca/chow-holds-21-point-lead-over-saunders/), [June 10–11: 10%](https://press.liaisonstrategies.ca/untitled/), [June 12–13: 11%](https://press.liaisonstrategies.ca/june-15/), [June 17–18: 12%](https://press.liaisonstrategies.ca/chow-steady-as-she-goes-while-rest-of-field-has-minor-ups-downs/) and first post-event [June 22–23: 17%](https://press.liaisonstrategies.ca/chow-leads-in-final-days-of-campaign/). The last release has a list typo resolved against its detailed pollster table in the [original evidence memo](../john-tory-2023-endorsement-evidence.md#comparable-before-and-after-readings).

The shorter windows give **3.6–4.7 points** of excess movement; the 28-day windows give **5.2–6.5**. This sensitivity range is not a confidence interval. Two observations define a line exactly and say little about whether it will continue. More elaborate regression does not identify the missing counterfactual. Published values are rounded and the surveys contain sampling, coverage and weighting error. We do not have known effective decided-voter sample sizes for all waves, so no inverse-variance fit or formal statistical interval is claimed.

Mainstreet is not silently treated as confirming the same trend: its surviving pre-event toplines show falling Bailão support and would imply a larger excess. Recent waves have unresolved timing and source comparability issues, documented in the [Mainstreet audit](../john-tory-2023-endorsement-evidence.md#subsequent-movement-and-mainstreet-corroboration). This two-firm result is a transparent calculation on the most consistently recoverable recent series, not an all-poll estimate. It measures the first response window, not the accumulated effect through June 26.

## 2. What the historical Star comparisons actually add

The [mayoral comparator audit](../star-mayoral-endorsement-comparators.md) finds a useful 2014 bracket: Tory moved **43% to 44% in Forum** and **43% to 42% in Mainstreet's decided reading** around the Star endorsement. Those windows also contain other endorsements. They show that a large late newspaper-associated rise is not automatic; they do not estimate a zero or one-point Star effect.

The upstream corpus contains **65 Star council endorsements: 43 in 2010 and 22 in 2022**, plus five mayoral endorsements. These are recovered records, not a complete historical census. They cluster in two council election cycles, so 65 records do not provide 65 independent citywide campaign shocks. The 2010 slate includes Bailão herself in Ward 18. The recorded vote outcomes are not estimates of support added by the endorsement. Source: the [upstream endorsement and outcome audit](../../../research/defeatability-index/docs/research/endorsement-data-audit.md), with exact joins and hashes in this analysis's [results](results.json).

The [council polling audit](../star-council-endorsement-comparators.md) identifies actual ward polls but no verified same-firm, same-ballot pre/post-Star pair. Publication after an endorsement does not make interviews taken before it a post-treatment poll. A concrete example is Chiara Padovani: Forum measured 28% in September and 34% on October 17, already a six-point increase before the October 19 Star endorsement. Her 47.2% final result cannot all be attributed to the Star. The [October primary report](https://poll.forumresearch.com/data/4a391231-3daa-4e46-bf07-b2969a3d8998Ward%205%20News%20Release%20%282%29.pdf) has only 185 decided respondents (217 parent sample); its 34% is also below her share of advance votes already cast, illustrating the hazards of treating polls and voting-mode results as one trajectory.

### A completed check using the official 2022 vote records

Advance voting took place **October 7–14**, before the recorded **October 19–21 Star council endorsements**. Election day was October 24. Sources: [City advance-voting report](https://www.toronto.ca/news/turnout-for-2022-toronto-municipal-election-advance-vote/), and the Star's editorials for [wards 1–8](https://www.thestar.com/opinion/editorials/2022/10/19/the-stars-endorsements-for-toronto-council-in-wards-1-to-8.html), [9–16](https://www.thestar.com/opinion/editorials/2022/10/20/the-stars-endorsements-for-toronto-council-in-wards-9-to-16.html), and [17–25](https://www.thestar.com/opinion/editorials/2022/10/21/the-stars-endorsements-for-toronto-council-in-wards-17-to-25.html). Editorial selections and dates use the existing curated assertions; this calculation does not newly establish individual exposure or first-public timestamps.

I calculated each endorsed candidate's share of valid council votes separately in advance voting and election-day voting. The City identifies subdivisions 98/99 as advance votes and 97 as mail votes; mail votes are kept separate and excluded from this contrast. Denominators are candidate votes within the same ward and voting mode, not ballots cast or citywide totals. Sources: [City coding guidance](https://www.toronto.ca/city-government/elections/election-results-reports/election-results/general-election-results/), [official result dataset](https://open.toronto.ca/dataset/election-results-official/), [2022 source archive](https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/96d35404-44d9-49d8-95bb-fb1e5489240d/resource/3ad371de-7c51-45d3-9ea4-0b4efac5fc2b/download/2022-results.zip).

| Recorded Star recipients | N | Mean election-day minus advance share | Median | Number with positive difference |
|---|---:|---:|---:|---:|
| Full 2022 slate | 22 | **−3.4 pp** | −5.4 pp | 6 |
| Excluding Ward 23's changed candidate field | 21 | **−3.1 pp** | −5.2 pp | 6 |
| Incumbents | 13 | −5.0 pp | −5.9 pp | 1 |
| Nonincumbents | 9 | −1.1 pp | +1.5 pp | 5 |
| Nonincumbents excluding Ward 23 | 8 | −0.1 pp | +2.0 pp | 5 |

Means give each endorsed candidate equal weight. Incumbency uses the canonical status, including appointed incumbent Robin Buxton Potts. Five recipients also have a recorded Tory endorsement; this is not a newspaper-only treatment sample. Missing Tory records are not assumed proof of no endorsement. All 22 recipients are included regardless of final rank or victory.

**Ward 23 must be excluded from endorsement-effect estimation.** Cynthia Lai died October 21. The City excluded votes cast for her, including those already cast in advance and by mail. Myers's calculated shares therefore use a retrospectively changed denominator, and the death itself is a major competing event. The full-slate row above is retained for audit completeness; the 21-race row is the preferable descriptive comparison. Sources: [City's October 21 notice](https://www.toronto.ca/news/impact-of-the-passing-of-councillor-cynthia-lai-on-the-scarborough-north-ward-23-election/), [official certification explanation](https://www.toronto.ca/news/toronto-city-clerk-certifies-2022-toronto-municipal-election-results/).

Selected examples below illustrate the variation; the aggregate above and the full machine-readable output include everyone.

| Candidate | Ward | Advance share | Election-day share | Difference |
|---|---:|---:|---:|---:|
| Chiara Padovani | 5 | 42.5% | 48.2% | +5.7 pp |
| Amber Morley | 3 | 44.1% | 46.8% | +2.7 pp |
| Ausma Malik | 10 | 35.5% | 37.0% | +1.5 pp |
| Chris Moise | 13 | 52.3% | 46.6% | −5.7 pp |
| Brad Bradford | 19 | 59.6% | 53.3% | −6.4 pp |
| Jamaal Myers (exclude from comparison) | 23 | 58.6% | 49.8% | −8.8 pp |

**These are voting-mode differences, not changes within the same people or a causal Star effect.** Early voters may be more committed, campaigns mobilize them differently, and late voters can differ demographically and politically. Incumbents without a recorded Star endorsement also had a negative mean difference (−6.3 points, five cases). Even that group is not a clean control: several opposed a Star-endorsed candidate and could lose votes because of that endorsement. Council opponents are affected by the treatment and cannot simply be labeled untreated.

Subtracting the −3.4-point slate mean from Bailão's four-point residual would therefore be wrong. A positive Star effect could be hidden by the voting-mode composition. Conversely, Padovani's positive difference does not establish a 5.7-point newspaper effect. The result makes a useful model diagnostic, but not yet a calibrated newspaper prior. I have not calculated a 2010 mode comparison because the workbook includes additional special subdivision codes whose historical meaning needs verification; the modern 97/98/99 convention should not be applied blindly.

## 3. An explicit rough decomposition

Define the target as **Tory's incremental contribution given that the Star endorses Bailão**:

`Tory given Star = support with both − support with Star alone`.

Then write:

`excess over projected trend = Tory given Star + Star without Tory + other residual movement`.

The last term includes independent campaign developments, pretrend misspecification and polling error. An endorsement-caused consolidation belongs inside the endorsement effect, not automatically inside that last term. Interaction between the endorsements belongs inside “Tory given Star.” A future Tory endorsement without the Star is a different target.

Using the short-window excess of 3.6–4.7 points gives this **assumption table**:

| Assumed net contribution of Star plus all other residual movement | Implied incremental Tory contribution |
|---:|---:|
| −2 pp | 5.6–6.7 pp |
| 0 pp | 3.6–4.7 pp |
| +1 pp | 2.6–3.7 pp |
| +2 pp | 1.6–2.7 pp |
| +4 pp | −0.4 to +0.7 pp |
| +6 pp | −2.4 to −1.3 pp |

The table is subtraction under stated assumptions, not an empirical distribution. Neither the council results nor 2014 establishes which row is right. Assuming the Star and all other residual terms together contributed 0–2 points would imply **about 2–5 points from Tory**, rounded. That is a usable conditional scenario, but the 0–2 assumption is unestimated; zero Tory contribution remains possible. Using the longer pretrend window shifts the same conditional calculation upward to 3.2–6.5 points. There is no identified finite causal bound from these aggregate data alone.

## 4. A design that could make the approximation more credible

1. **Reconstruct all council slates and first-public dates**, including non-endorsements established by comprehensive editorial coverage. Include successes, failures and endorsements of weak candidates. Record other newspaper and politician endorsements and ballot-field changes.
2. **Prioritize repeated ward polls or respondent-level daily interviews.** Estimate a within-firm event trajectory where interviews bracket the editorial. Seek comparison races outside the same vote-transfer contest, match on measured pre-event level/trend and incumbency, and examine placebo dates. Treat same-date endorsements as bundles when exposure cannot be separated.
3. **Use the vote records as a second design.** Model normal advance-versus-election-day differences with comparable candidates, prior cycles and available pre-event characteristics. Repeated candidates and stable boundaries can help, but prior endorsements and changing voter composition must also be tracked. A matched difference-in-differences or triple-difference estimate requires a credible parallel-trends assumption. With one pre-period and two cycles we cannot claim it is tested. Cluster uncertainty by contest and election and assess leave-one-cycle-out sensitivity; 22 wards are not 22 independent campaign environments.
4. **Transport council evidence cautiously.** Council races differ in information, campaign reach, starting strength and strategic voting. A hierarchical model can allow council and mayoral effects to differ, but partial pooling cannot compensate for a confounded input estimate. Historical evidence should inform a broad prior only after these checks, with interaction and transport uncertainty carried through.
5. **For the Bradford/Alexander question, a new randomized survey experiment is more direct.** A four-condition control/Star/Tory/both design would separate stated-preference effects and interaction for a specified hypothetical recipient, with an unchanged ballot question and random assignment. It measures an immediate response to supplied information, not campaign-wide reach or durable election-day votes. Nothing in the current evidence establishes that the two recipients respond equally.

This is consistent with the methodological distinction in Chiang and Knight's [primary newspaper-endorsement study](https://cpb-us-w2.wpmucdn.com/sites.brown.edu/dist/d/75/files/2019/05/Media-Bias-and-Influence.pdf): their design uses individual survey timing and readership, and the response depends on the endorsement's informativeness. We do not import a US presidential-election coefficient into Toronto.

## Reproduction and checks

Run [calculate.py](calculate.py) with the upstream results repository path, using Python with pandas/openpyxl. It writes [results.json](results.json). All inputs are read-only. The retained official 2022 workbook is identified by SHA-256 alongside the endorsement and outcome snapshots. Each candidate's advance, mail and election-day counts must sum exactly to both the original workbook total and the canonical result; every council candidate must join uniquely. The Forum 14-day extrapolation is also checked against its hand-worked 16% projection. The poll values above were cross-checked against primary tables and canonical readings, with the June 16 Forum exception explicitly documented.

No forecast coefficient, endorsement-conditioned win probability, production input or release was changed. The [existing scenario explorer](../tory-endorsement-scenarios/index.html) remains conditional arithmetic; these findings explain which assumptions it can and cannot borrow from history.
