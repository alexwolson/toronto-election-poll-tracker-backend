# Can Star council endorsements identify the Star component of Bailão's 2023 surge?

**Research date:** 2026-09-09
**Scope:** Recorded Toronto Star council endorsements in 2010 and 2022, recoverable council opinion polls, and official 2022 voting-mode results. Research only; no production model or data changes.

## Finding

The council cases provide useful checks on a proposed newspaper-endorsement effect, but the recovered evidence does **not identify a Star effect that can be subtracted from Bailão's June 2023 movement**. Three concrete 2022 cases have pre-endorsement opinion evidence and official results. None has a verified, comparable public opinion poll interviewed after the Star endorsement. Advance voting provides an actual before-endorsement outcome, but election-day voters are a different group, not the same voters observed after treatment.

The available comparisons also do not show a uniform positive late shift. Padovani gained between advance and election-day voting; Malik gained modestly; Perks declined. These differences describe voters and campaign periods jointly. They neither establish nor rule out a positive causal Star effect.

## Coverage and source audit

The read-only endorsement corpus records **65 Star council endorsements: 43 in 2010 and 22 in 2022**. The other five Star entries are mayoral endorsements. The council recipients won 26 and 17 seats respectively; those win counts describe the newspaper's selections, not how much its support changed votes. The corpus is a source inventory, not proof that unrecorded endorsements never happened. Joins use `endorser_id` and `candidacy_id`, not candidate-name matching. Source files: [endorsers](/Users/alex/code/personal/toronto-election-results/data/out/endorsers.csv), [endorsements](/Users/alex/code/personal/toronto-election-results/data/out/endorsements.csv), [dated assertions](/Users/alex/code/personal/toronto-election-results/data/out/endorsement_assertions.csv), and [results](/Users/alex/code/personal/toronto-election-results/data/out/election_results.csv).

The dated assertions identify the 2022 editorial batches as [October 19, Wards 1–8](https://www.thestar.com/opinion/editorials/2022/10/19/the-stars-endorsements-for-toronto-council-in-wards-1-to-8.html), [October 20, Wards 9–16](https://www.thestar.com/opinion/editorials/2022/10/20/the-stars-endorsements-for-toronto-council-in-wards-9-to-16.html), and [October 21, Wards 17–25](https://www.thestar.com/opinion/editorials/2022/10/21/the-stars-endorsements-for-toronto-council-in-wards-17-to-25.html). These dates rely on the existing confirmed source assertions, which identify archived publisher copies; the live Star pages could not be retrieved afresh in this audit.

The [earlier council poll audit](unmeasured-candidate-tail.md#six-directly-matched-2022-ward-polls) covered six September Forum polls. This search also located October Forum material, so the six September samples are not a complete 2022 inventory. Several old Forum PDF URLs now return errors; where available, the pollster's indexed PDF text supplied the evidence below. Missing post-endorsement documents are an evidence gap, not proof that no private poll existed.

## Three concrete opinion-poll comparators

### Chiara Padovani, Ward 5: late movement, but no measured Star discontinuity

The Star endorsed Padovani **October 19**. Forum interviewed **October 17**, released October 18, with **217 eligible voters** and **185 decided/leaning respondents**. Its council table gave Padovani **34%**, Frances Nunziata **54%**, Gabriel Takang **2%**, and Other **11%**. Forum's quoted ±7-point margin applies to the full sample; the council subset is less precise. The earlier September 14 release gave Padovani **28%** among 153 decided/leaning respondents. Thus a six-point improvement was already visible before the endorsement; the September interview date was not freshly recovered here. [Forum October release and table](https://poll.forumresearch.com/data/4a391231-3daa-4e46-bf07-b2969a3d8998Ward%205%20News%20Release%20%282%29.pdf), [Forum September table](https://poll.forumresearch.com/data/74bddea4-50a4-4c53-a017-52dabdd9cb43Ward%205%20News%20Release.pdf).

Padovani finished with **9,983 votes, 47.16%**, losing to Nunziata's 10,077 by 94 votes. The apparent poll-to-result gain from 34% is **13.16 points**, but its endpoints differ in turnout, measurement, and campaign time. The poll even retained Other when all three eventual candidates had named rows. It supplies no isolated newspaper coefficient. [City's certified declaration, Ward 5](https://www.toronto.ca/wp-content/uploads/2022/10/9085-FinalDeclaration-of-Results-for-the-2022-Toronto-Municipal-Election.pdf).

The official mode breakdown below is particularly informative: Padovani already received **42.51% of advance votes cast October 7–14**, before the October 17 poll estimated 34%. This mismatch is direct evidence against treating the poll and the early-voter result as interchangeable measurements of one population.

### Ausma Malik, Ward 10: an apparent post-endorsement publication is not a post-endorsement survey

The Star endorsed Malik **October 20**. Forum's verified **September 14** IVR sample had **208 eligible voters**, with **105 decided/leaning**; Malik received **52%**, Karlene Nation 13%, and Other 22%. [Forum September 15 release, methodology and table](https://poll.forumresearch.com/data/b390026c-ece7-475d-85f0-9cc0e050e9e0Ward%2010%20News%20Release.pdf).

A later first-party Forum article reports Malik **35%**, Nation 15%, and 30% undecided, again describing 208 ward voters. Its website timestamp is **October 21**, but its report body is dated **October 19**. Exact interview dates and the complete later council table were not recovered. The article therefore cannot be classified as post-Star fieldwork merely because its webpage appeared after the editorial. It documents a lower later estimate, with unresolved timing and denominator details. [Forum's later Ward 10 article](https://poll.forumresearch.com/post/3134/despite-slight-decrease-in-support--malik-maintains-lead/).

Malik won with **8,033 votes, 36.55%**. The September-to-result decline and the much smaller difference from the later report illustrate how choosing a distant baseline can dominate an alleged endorsement effect. A twelve-candidate final ballot and a substantial poll Other category add measurement concerns. [City's certified declaration, Ward 10](https://www.toronto.ca/wp-content/uploads/2022/10/9085-FinalDeclaration-of-Results-for-the-2022-Toronto-Municipal-Election.pdf).

### Gord Perks, Ward 4: a winner with a declining measured share

The Star endorsed Perks **October 19**. Forum interviewed **September 13**, released September 14, with **228 eligible voters**, reporting Perks **52%** and Siri Agrell 21% among decided/leaning respondents. The release is internally inconsistent on the council subset size: the opening prose says 160 and the table says 162; the methodology gives the full sample as 228. No verified post-Star poll was recovered. [Forum Ward 4 release](https://poll.forumresearch.com/data/0f87336b-4a32-498e-8411-70b1dd986581Ward%204%20News%20Release.pdf).

Perks won with **11,149 votes, 35.48%**. He also did better among advance voters than election-day voters. Winning after an endorsement therefore need not coincide with either a rising measured share or a positive early-to-late contrast. Incumbency, the long September-to-election interval, and changing support among six candidates prevent attribution of the decline to the Star. [City's certified declaration, Ward 4](https://www.toronto.ca/wp-content/uploads/2022/10/9085-FinalDeclaration-of-Results-for-the-2022-Toronto-Municipal-Election.pdf).

## Actual advance-versus-election-day evidence

The City confirms advance voting ran **October 7–14**, entirely before the Star's October 19–21 endorsements, and election day was **October 24**. [City advance-voting report](https://www.toronto.ca/news/turnout-for-2022-toronto-municipal-election-advance-vote/).

The following calculations use the original City council workbook, separating subdivisions 98–99 (advance), 97 (mail), and ordinary election-day subdivisions. Shares divide each candidate's votes by all credited candidate votes within the same ward and mode. Mail votes are excluded from the comparison because their precise voting dates are unavailable. Full sums, source hashes, and reproduction code are in [results.json](endorsement-identification/results.json) and [calculate.py](endorsement-identification/calculate.py); the source workbook is [2022_Toronto_Poll_By_Poll_Councillor.xlsx](/Users/alex/code/personal/toronto-election-results/data/raw/results/extracted/2022/2022_Toronto_Poll_By_Poll_Councillor.xlsx), obtained from the [City's official-results collection](https://www.toronto.ca/city-government/elections/election-results-reports/election-results/general-election-results/).

| Star recipient | Advance votes / credited ward votes | Advance share | Election-day votes / credited ward votes | Day share | Day minus advance |
|---|---:|---:|---:|---:|---:|
| Padovani, Ward 5 | 1,684 / 3,961 | 42.51% | 8,068 / 16,745 | 48.18% | +5.67 pp |
| Malik, Ward 10 | 1,297 / 3,649 | 35.54% | 6,410 / 17,303 | 37.05% | +1.50 pp |
| Perks, Ward 4 | 2,653 / 6,592 | 40.25% | 7,900 / 23,641 | 33.42% | −6.83 pp |

Across all 22 recorded recipients, only six have positive differences; the unweighted mean is **−3.40 points** and median **−5.42**. This is an all-recorded-case descriptive summary, including seriously confounded races. It must not be interpreted as a negative Star effect or subtracted from Bailão's movement. The script's incumbent/nonincumbent splits and overlapping Tory endorsements further document that these are heterogeneous comparisons, not exchangeable repetitions of one treatment.

Excluding Ward 23 for the reason below leaves 21 cases, six positive differences, a mean of **−3.15 points**, and a median of **−5.17**. This is the preferable descriptive comparison; it still does not identify a causal effect.

### Fourth case: Ward 23 should be excluded from causal comparison

The Star's recorded endorsement of Jamaal Myers was **October 21**, the day incumbent candidate Cynthia Lai died. The City announced that **none of Lai's votes, including advance and mail votes already cast, would count**, and that those voters could not change their votes. [City's election-specific notice](https://www.toronto.ca/news/impact-of-the-passing-of-councillor-cynthia-lai-on-the-scarborough-north-ward-23-election/).

Myers ultimately received **5,315 votes, 51.09%**. The workbook gives 712 of 1,215 credited advance votes (58.60%) versus 4,508 of 9,046 election-day votes (49.83%). Even the early denominator retrospectively omits an active candidate whom people could vote for when those ballots were cast. The candidate's death changes both the available choices and the interpretation of the recorded early share. This is an explicit exclusion, not an endorsement effect of −8.77 points. [City declaration, Ward 23](https://www.toronto.ca/wp-content/uploads/2022/10/9085-FinalDeclaration-of-Results-for-the-2022-Toronto-Municipal-Election.pdf), [reproduced mode calculations](endorsement-identification/results.json).

## What these cases permit

1. **Use them to test the credibility of assumptions.** They show substantial late movement in both directions and a strong distinction between winning, poll changes, and changes across voting modes. They support treating any common Star coefficient as uncertain and context dependent.
2. **Do not label the council recipients an untreated control group.** They received the Star endorsement themselves. They could inform a separate Star-only effect estimate if credible within-race counterfactuals were available. Recorded absence of Tory support also does not establish absence of other influential endorsements.
3. **Do not call advance/day comparison a discontinuity design.** Voting time is self-selected, individual exposure is unknown, and the public outcomes do not follow the same electorate continuously across the announcement. Within-ward shares remove ward size, not differences in who votes early, campaign trends, or turnout mobilization.
4. **A better study needs comparable pre/post interviews, multiple pre-periods, endorsement timing and overlap, and defensible controls.** A council-to-mayor transfer additionally requires assumptions about readership, candidate familiarity, and race salience. Even a well-estimated Star-only council effect would not establish the interaction when the Star and Tory endorse the same mayoral candidate together.

For 2010, the corpus includes Bailão's own Ward 18 endorsement on October 18, but this bounded search did not recover an opinion-poll pair surrounding it. That earlier endorsement is an interesting same-candidate lead, not an additional measured treatment effect. The [2010 editorial source recorded in the corpus](https://www.thestar.com/article/876714--star-election-choices-for-city-council) should be followed by targeted archival work only if a dated ward polling series can be found.

The defensible use in the [2023 Tory scenario analysis](john-tory-2023-endorsement-evidence.md) remains sensitivity analysis over an explicitly assumed Star contribution and possible joint effect. These council observations improve the discussion of that assumption; they do not identify its numerical value.
