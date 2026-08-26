# Candidate career identity audit

> Upstream status update (2026-08-20): all 12 cases that remained null-linked after
> the first upstream correction are now published as confirmed links in release
> `2026-08-21T00:09:33.813600Z`. The audit decisions below document the stricter
> primary/first-party review conducted before that upstream adjudication.

## Result

Ten of the 13 held cross-office identity proposals are **confirmed** by evidence that directly bridges the council candidate to the prior officeholder. Three remain **unresolved**. None is rejected.

This is an identity audit, not an analysis of electoral effects. A confirmed result means the council candidacy can be attached to the retained persistent `person_id`; an unresolved result means the current evidence does not justify that attachment. It does not mean the people are different.

| Council candidate | Council candidacy | Retained target | Audit result | Resulting career category if linked |
|---|---|---|---|---|
| David Caplan | 2018-10-22, Ward 16 — Don Valley East; not elected (30.30%) | `per_656bf9ee8956529195719d111d5fe53d` | **Unresolved** | Target is a Prior officeholder |
| Matthew Kellway | 2018-10-22, Ward 19 — Beaches-East York; not elected (37.78%) | `per_b05bca5a3f225453b8484ce46c8b2bb8` | **Confirmed** | Mixed prior-office record |
| Jennifer Arp | 2018-10-22, Ward 8 — Eglinton-Lawrence; not elected (7.05%) | `per_c264c8a222ea5baea6a15b1bfeac3ae0` | **Confirmed** | Prior officeholder |
| Ken Lister | 2018-10-22, Ward 17 — Don Valley North; not elected (13.07%) | `per_fd89e2daa64b5513ba56eb9e1c8b51f7` | **Confirmed** | Mixed prior-office record |
| Pamela Gough | 2018-10-22, Ward 3 — Etobicoke-Lakeshore; not elected (18.07%) | `per_b94977f840da534caf789477d036ee8c` | **Confirmed** | Prior officeholder |
| Tiffany Ford | 2018-10-22, Ward 7 — Humber River-Black Creek; not elected (14.07%) | `per_d56a01f9891c5106ba8bf6281c6f713c` | **Confirmed** | Prior officeholder |
| Manna Wong | 2021-01-15, Ward 22 — Scarborough-Agincourt by-election; not elected (25.13%) | `per_cbad12eb2bc15f4fb7ba5a96bd68dec9` | **Confirmed** | Mixed prior-office record |
| Avtar Minhas | 2022-10-24, Ward 1 — Etobicoke North; not elected (20.54%) | `per_194efd592b915c2ca63859d3ebbef5e0` | **Unresolved** | Target is a Prior officeholder |
| Christopher Mammoliti | 2022-10-24, Ward 7 — Humber River-Black Creek; not elected (22.63%) | `per_2d23abe818995711b696fd8b8f2af4ed` | **Unresolved** | Target is a Prior officeholder |
| Norm Di Pasquale | 2022-10-24, Ward 11 — University-Rosedale; not elected (34.87%) | `per_9f569a842c9e527b88cda3fc73dbfacb` | **Confirmed** | Prior officeholder |
| Malika Ghous | 2023-11-30, Ward 20 — Scarborough Southwest by-election; not elected (9.23%) | `per_74212bbadc535bca8fa201bda63cee06` | **Confirmed** | Prior officeholder |
| Anu Sriskandarajah | 2025-09-29, Ward 25 — Scarborough-Rouge Park by-election; not elected (17.52%) | `per_3c246b205ffd55298633b81a804f8b82` | **Confirmed** | Prior officeholder |
| Zakir Patel | 2025-09-29, Ward 25 — Scarborough-Rouge Park by-election; not elected (7.90%) | `per_353b9c4a63ac57ab9ee85eb011797754` | **Confirmed** | Prior officeholder |

The percentages above reproduce `vote_share` from the audited upstream release. The corresponding council candidacy remains null-linked in that release for every row in this table.

## Scope and decision rule

The audited upstream release is schema `2.0.0`, generated `2026-08-20T22:16:22.639073Z`, with coverage through 2026-08-20. Its `election_results.csv` has 5,488 rows and SHA-256 `5dba7bce788988dc3135e02f505c4307b23164f806d9f6e08ad76dffc8a326c7`. The 13 council rows and retained targets were read from the current `election_results.csv` and `identity_review_dispositions.csv`, not from the older release previously analyzed.

The audit applies the repository vocabulary in `CONTEXT.md`:

- **Prior officeholder**: at least one certified pre-council win in another elected office.
- **Prior unsuccessful candidate**: at least one certified pre-council loss in another elected office and no pre-council win.
- **Mixed prior-office record**: at least one certified pre-council win and at least one certified pre-council loss in another elected office.

An exact name match across official result rows is not an identity bridge. Confirmation requires an official institutional biography/archive, a first-party campaign page, or candidate-authored material that explicitly connects the council campaign with the earlier office. Archived first-party pages are treated as the candidate's own contemporaneous claims. Secondary reporting was not used to confirm any row.

For unresolved cases, the prior-office rows below describe the **retained target**, not the council candidate. They must not be used as candidate history until the identity bridge is resolved.

`Signed margin` is the winner's lead over the runner-up for an elected candidate, and a non-winner's vote share minus the winner's share otherwise. It is included so the identity decisions preserve the study's prior-performance-strength axis. Values are reported in percentage points (`pp`).

## Candidate findings

### David Caplan — unresolved

`can_3b00773d04365f64a37bf88fce264eaf` should remain unlinked. The [City Clerk's 2018 declaration](https://www.toronto.ca/wp-content/uploads/2018/10/97da-2018clerksofficialdeclarationofresults.pdf) certifies a David Caplan council candidacy. Elections Ontario certifies the retained target's MPP wins, and a later [City of Toronto commemoration record](https://secure.toronto.ca/council/agenda-item.do?item=2024.NY12.30) describes the former MPP. None of these primary sources explicitly says that the 2018 council candidate was that former MPP. The available explicit bridge is only in secondary reporting, which is outside this audit's admissible source set.

Retained target's pre-council other-office rows:

| Date | Office | District | Outcome | Vote share | Signed margin | Official result |
|---|---|---|---|---:|---:|---|
| 2003-10-02 | MPP, Ontario Legislative Assembly | Don Valley East | Elected | 56.80% | +24.77 pp | [Elections Ontario CSV](https://results.elections.on.ca/api/report-groups/5/report-outputs/521/csv) |
| 2007-10-10 | MPP, Ontario Legislative Assembly | Don Valley East | Elected | 55.63% | +30.52 pp | [Elections Ontario CSV](https://results.elections.on.ca/api/report-groups/4/report-outputs/510/csv) |

### Matthew Kellway — confirmed

Attach `can_8702c409b44c56869788d0fcb7ee8999` to `per_b05bca5a3f225453b8484ce46c8b2bb8`. In his candidate-authored [2018 Ward 19 questionnaire](https://deca.to/ward-19-candidate-qa-matthew-kellway/), Kellway identifies the campaign and describes his service as the Member of Parliament for Beaches—East York. The [House of Commons member record](https://www.ourcommons.ca/Members/en/matthew-kellway%2871585%29) independently establishes that federal office.

Pre-council other-office rows:

| Date | Office | District | Outcome | Vote share | Signed margin | Official result |
|---|---|---|---|---:|---:|---|
| 2011-05-02 | MP, House of Commons | Beaches—East York | Elected | 41.64% | +10.89 pp | [Elections Canada raw official results](https://www.elections.ca/scripts/OVR2011/34/data_donnees/pollresults_resultatsbureau35.zip) |
| 2015-10-19 | MP, House of Commons | Beaches—East York | Not elected | 30.82% | −18.63 pp | [Elections Canada raw official results](https://www.elections.ca/res/rep/off/ovr2015app/41/data_donnees/pollresults_resultatsbureau35.zip) |

### Jennifer Arp — confirmed

Attach `can_246c0347d317593aa183f92681afb95e` to `per_c264c8a222ea5baea6a15b1bfeac3ae0`. Her archived first-party [2018 council campaign home page](https://web.archive.org/web/20181214222254/https://www.jenniferarp.ca/) identifies her as a city-council candidate, while the campaign's archived [about page](https://web.archive.org/web/20181026215109/https://www.jenniferarp.ca/about) says she had been elected public-school trustee in 2014.

Pre-council other-office row:

| Date | Office | District | Outcome | Vote share | Signed margin | Official result |
|---|---|---|---|---:|---:|---|
| 2014-10-27 | Trustee, Toronto District School Board | Ward 8 | Elected | 30.98% | +4.07 pp | [City of Toronto official-results archive](https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/96d35404-44d9-49d8-95bb-fb1e5489240d/resource/d59b5a52-33c3-4380-a136-82707e4d9aae/download/2014-results.zip) |

### Ken Lister — confirmed

Attach `can_b07911ac186c5fedbb0acd5ccd8a2bd8` to `per_fd89e2daa64b5513ba56eb9e1c8b51f7`. The archived first-party [2018 council campaign site](https://web.archive.org/web/20181026215226/https://www.kenlister.ca/) identifies Lister as a Don Valley North council candidate and says he served four years as a TDSB trustee. His [TDSB biography](https://www.tdsb.on.ca/ward17/Ward17/KenListerBio.aspx) supplies institutional corroboration.

Pre-council other-office rows:

| Date | Office | District | Outcome | Vote share | Signed margin | Official result |
|---|---|---|---|---:|---:|---|
| 2012-02-27 | Trustee, Toronto District School Board | Ward 17 by-election | Not elected | 11.94% | −6.97 pp | [City of Toronto official by-election result](https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/97d72233-8681-4b3d-828e-4929d40d122c/resource/79f831c8-48ec-45f2-a65e-3b514f877a93/download/2012-tdsb-wards-17-20.xls) |
| 2014-10-27 | Trustee, Toronto District School Board | Ward 17 | Elected | 22.60% | +0.84 pp | [City of Toronto official-results archive](https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/96d35404-44d9-49d8-95bb-fb1e5489240d/resource/d59b5a52-33c3-4380-a136-82707e4d9aae/download/2014-results.zip) |

### Pamela Gough — confirmed

Attach `can_690689c4111c50918c06f6b446c95d0d` to `per_b94977f840da534caf789477d036ee8c`. The archived first-party [2018 council campaign home page](https://web.archive.org/web/20181106153055/https://www.votegough.ca/) identifies the Etobicoke-Lakeshore council campaign, and its archived [biography](https://web.archive.org/web/20181106152912/https://www.votegough.ca/about-pamela/) describes Gough's tenure as the area's elected TDSB trustee.

Pre-council other-office rows:

| Date | Office | District | Outcome | Vote share | Signed margin | Official result |
|---|---|---|---|---:|---:|---|
| 2010-10-25 | Trustee, Toronto District School Board | Ward 3 | Elected | 35.84% | +7.44 pp | [City of Toronto official-results archive](https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/96d35404-44d9-49d8-95bb-fb1e5489240d/resource/6fbfaab0-bb84-442a-8e4b-1c14d4c10d6d/download/2010-results.zip) |
| 2014-10-27 | Trustee, Toronto District School Board | Ward 3 | Elected | 55.05% | +32.54 pp | [City of Toronto official-results archive](https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/96d35404-44d9-49d8-95bb-fb1e5489240d/resource/d59b5a52-33c3-4380-a136-82707e4d9aae/download/2014-results.zip) |

### Tiffany Ford — confirmed

Attach `can_34fbfb27258159f1b05bf2d0cb8302ff` to `per_d56a01f9891c5106ba8bf6281c6f713c`. Her archived first-party [2018 Ward 7 council campaign site](https://web.archive.org/web/20181214230713/https://tiffanyford2018.ca/) says that she had served the preceding three years as the local public-school trustee.

Pre-council other-office row:

| Date | Office | District | Outcome | Vote share | Signed margin | Official result |
|---|---|---|---|---:|---:|---|
| 2014-10-27 | Trustee, Toronto District School Board | Ward 4 | Elected | 39.26% | +19.69 pp | [City of Toronto official-results archive](https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/96d35404-44d9-49d8-95bb-fb1e5489240d/resource/d59b5a52-33c3-4380-a136-82707e4d9aae/download/2014-results.zip) |

### Manna Wong — confirmed

Attach `can_f9f7d971b99c52cf9a48edf7b1dd38ba` to `per_cbad12eb2bc15f4fb7ba5a96bd68dec9`. Wong's candidate-authored [2021 Ward 22 questionnaire](https://static1.squarespace.com/static/5aae198d96e76f27dc9377ce/t/5fd90dea89ea717cb5d4a69a/1608060394760/Manna%2BWong%2B-%2BScarbrough-Agincourt%2BBy-election%2BProgressive%2BChampion%2BSurvey%2B.pdf) identifies her city-council campaign and says she had served as Scarborough-Agincourt school trustee since 2014. The City of Toronto's [campaign-compliance record](https://secure.toronto.ca/council/agenda-item.do?item=2021.EA8.5) independently identifies the Ward 22 council candidate.

Pre-council other-office rows:

| Date | Office | District | Outcome | Vote share | Signed margin | Official result |
|---|---|---|---|---:|---:|---|
| 2012-02-27 | Trustee, Toronto District School Board | Ward 20 by-election | Not elected | 26.13% | −2.66 pp | [City of Toronto official by-election result](https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/97d72233-8681-4b3d-828e-4929d40d122c/resource/79f831c8-48ec-45f2-a65e-3b514f877a93/download/2012-tdsb-wards-17-20.xls) |
| 2014-10-27 | Trustee, Toronto District School Board | Ward 20 | Elected | 43.21% | +7.64 pp | [City of Toronto official-results archive](https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/96d35404-44d9-49d8-95bb-fb1e5489240d/resource/d59b5a52-33c3-4380-a136-82707e4d9aae/download/2014-results.zip) |
| 2018-10-22 | Trustee, Toronto District School Board | Ward 20 | Elected | 55.60% | +30.32 pp | [City of Toronto official-results archive](https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/96d35404-44d9-49d8-95bb-fb1e5489240d/resource/2fcd5f20-90f5-4dd0-88eb-22e978b9bf89/download/2018-results.zip) |

The target also won the same trustee office in 2022, but that event occurred after the audited 2021 council candidacy and is therefore not prior history for that observation.

### Avtar Minhas — unresolved

`can_d0b1cdfb35165fb0acbf31c7cd5ae8c2` should remain unlinked. The retained target is already linked to a 2014 council loss and a 2016 trustee win. Official 2022 results certify another Avtar Minhas council candidacy, but those official same-name rows do not bridge the changed council district regime to the retained person. The located non-government biography explicitly connects the 2014 council candidate and 2016 trustee but not the 2022 council candidate, and it is outside the permitted source classes in any event. No qualifying official, institutional, or first-party 2022 bridge was found.

Retained target's pre-council other-office row:

| Date | Office | District | Outcome | Vote share | Signed margin | Official result |
|---|---|---|---|---:|---:|---|
| 2016-07-25 | Trustee, Toronto District School Board | Ward 1 by-election | Elected | 29.67% | +6.89 pp | [City of Toronto official by-election result](https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/97d72233-8681-4b3d-828e-4929d40d122c/resource/836c4152-0603-4fd4-8ab4-a53cf386bc43/download/2016-tdsb-ward-1-.xlsx) |

The retained target's 2014 council loss is same-office history, not an other-office candidacy, so it is not included in the table above.

### Christopher Mammoliti — unresolved

`can_910c3031a66e5d91978ea8cb4b25fd15` should remain unlinked. The City Clerk certifies the 2018 trustee result and 2022 council result under the same name. Mammoliti's current first-party [trustee campaign biography](https://www.mammolitifortrustee.ca/) confirms his earlier TDSB service, but it does not mention his 2022 council candidacy. Explicit accounts connecting the two were found only in secondary reporting. Under the strict bridge rule, the official same-name rows plus the partial first-party biography are insufficient.

Retained target's pre-council other-office row:

| Date | Office | District | Outcome | Vote share | Signed margin | Official result |
|---|---|---|---|---:|---:|---|
| 2018-10-22 | Trustee, Toronto District School Board | Ward 4 | Elected | 31.96% | +3.47 pp | [City of Toronto official-results archive](https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/96d35404-44d9-49d8-95bb-fb1e5489240d/resource/2fcd5f20-90f5-4dd0-88eb-22e978b9bf89/download/2018-results.zip) |

### Norm Di Pasquale — confirmed

Attach `can_cc7dfd8b06db51e592901dc4b159ca78` to `per_9f569a842c9e527b88cda3fc73dbfacb`. Di Pasquale's candidate-submitted [2025 federal profile](https://en.votemate.org/canada2025/candidates/10278) identifies him as both a former school trustee and a Toronto council candidate. A contemporaneous first-party [Kristyn Wong-Tam campaign newsletter](https://www.kristynwongtam.ca/newsletter_october_7_2022) explicitly calls him both the outgoing Catholic trustee and the University-Rosedale City Council candidate. An official [letter filed with Toronto City Council](https://www.toronto.ca/legdocs/mmis/2022/cc/comm/communicationfile-152340.pdf), signed in his trustee capacity shortly before the election, independently fixes the trustee identity.

Pre-council other-office row:

| Date | Office | District | Outcome | Vote share | Signed margin | Official result |
|---|---|---|---|---:|---:|---|
| 2018-10-22 | Trustee, Toronto Catholic District School Board | Ward 9 | Elected | 23.77% | +5.07 pp | [City of Toronto official-results archive](https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/96d35404-44d9-49d8-95bb-fb1e5489240d/resource/2fcd5f20-90f5-4dd0-88eb-22e978b9bf89/download/2018-results.zip) |

The upstream release also contains a same-name 2021 federal candidacy that is not linked to this retained target. It is not counted here because this audit was limited to the specified council-to-retained-target bridge.

### Malika Ghous — confirmed

Attach `can_94c9f534cc225dbbb74ad1b9aa11a1d7` to `per_74212bbadc535bca8fa201bda63cee06`. In her candidate-authored [2023 council by-election questionnaire](https://beachmetro.com/2023/11/15/scarborough-southwest-byelection-2023-candidate-malika-ghous-answers-our-questions/), Ghous identifies herself as the sitting TDSB trustee for Scarborough Southwest. The City of Toronto's [official campaign-filing record](https://secure.toronto.ca/EFD/jsf/candidate2018/candidate_campaign_status.xhtml?campaign=20) independently records her Ward 20 council campaign.

Pre-council other-office row:

| Date | Office | District | Outcome | Vote share | Signed margin | Official result |
|---|---|---|---|---:|---:|---|
| 2022-10-24 | Trustee, Toronto District School Board | Ward 18 | Elected | 28.48% | +0.35 pp | [City of Toronto official-results archive](https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/96d35404-44d9-49d8-95bb-fb1e5489240d/resource/3ad371de-7c51-45d3-9ea4-0b4efac5fc2b/download/2022-results.zip) |

### Anu Sriskandarajah — confirmed

Attach `can_77360db1d61055b1862abdad17f5e03c` to `per_3c246b205ffd55298633b81a804f8b82`. Her first-party [2025 campaign site](https://www.dranu.ca/) asks voters to elect her Ward 25 city councillor and says she had served as their school-board trustee for seven years. The City's [official Ward 25 candidate list](https://www.toronto.ca/city-government/elections/ward-25-scarborough-rouge-park-by-election-list-of-candidates-third-party-advertisers/) links that campaign website to her council candidacy.

Pre-council other-office rows:

| Date | Office | District | Outcome | Vote share | Signed margin | Official result |
|---|---|---|---|---:|---:|---|
| 2018-10-22 | Trustee, Toronto District School Board | Ward 22 | Elected | 36.27% | +22.02 pp | [City of Toronto official-results archive](https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/96d35404-44d9-49d8-95bb-fb1e5489240d/resource/2fcd5f20-90f5-4dd0-88eb-22e978b9bf89/download/2018-results.zip) |
| 2022-10-24 | Trustee, Toronto District School Board | Ward 22 | Elected | 44.04% | +16.26 pp | [City of Toronto official-results archive](https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/96d35404-44d9-49d8-95bb-fb1e5489240d/resource/3ad371de-7c51-45d3-9ea4-0b4efac5fc2b/download/2022-results.zip) |

### Zakir Patel — confirmed

Attach `can_d61ecb46f8f45feda51476da5f4af62b` to `per_353b9c4a63ac57ab9ee85eb011797754`. The City's [official Ward 25 candidate list](https://www.toronto.ca/city-government/elections/ward-25-scarborough-rouge-park-by-election-list-of-candidates-third-party-advertisers/) identifies Patel's council candidacy and links his first-party campaign. In his candidate-submitted [Highland Creek Community Association profile](https://myhighlandcreek.org/event/ward-25-by-election-candidate-forums-2/), Patel says he is running for Ward 25 councillor and has served as a TDSB trustee since 2018. That is an explicit first-person bridge, not an inference from the name.

Pre-council other-office rows:

| Date | Office | District | Outcome | Vote share | Signed margin | Official result |
|---|---|---|---|---:|---:|---|
| 2018-10-22 | Trustee, Toronto District School Board | Ward 19 | Elected | 21.99% | +2.51 pp | [City of Toronto official-results archive](https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/96d35404-44d9-49d8-95bb-fb1e5489240d/resource/2fcd5f20-90f5-4dd0-88eb-22e978b9bf89/download/2018-results.zip) |
| 2022-10-24 | Trustee, Toronto District School Board | Ward 19 | Elected | 46.78% | +29.23 pp | [City of Toronto official-results archive](https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/96d35404-44d9-49d8-95bb-fb1e5489240d/resource/3ad371de-7c51-45d3-9ea4-0b4efac5fc2b/download/2022-results.zip) |

## Implementation consequence

The ten confirmed council candidacies can be assigned to their retained persistent `person_id`s. David Caplan, Avtar Minhas, and Christopher Mammoliti should remain in the identity-review queue. Their retained targets' prior wins must not be exposed as the council candidates' `Prior officeholder` history until a qualifying bridge is added.
