# Ward polling: historical source audit

Research date: October 2, 2026. Scope: recover original historical Council poll tables to assess the practical value of the September 2026 published ward toplines. This is a descriptive evidence corpus, not a fitted election forecast. This completed audit supersedes the initial incomplete retrieval inventory; it does not change production Polling tables.

## Acquired and verified

Twelve five-page Forum Research releases from 2022 were recovered as archived copies of the original first-party PDF bytes. The live host returned HTTP 404/503; raw Internet Archive captures succeeded. All 60 pages were rendered and visually inspected, including every Council total, denominator, table base, fieldwork date, release date and method. SHA-256 hashes were checked after acquisition. Thus these are successfully acquired primary documents, not search snippets or acquisition leads.

Two retained CSVs distinguish the immediately usable cohort from the full audit:

- `historical_council_poll_toplines_primary.csv`: six September samples, six Council contests, one firm, one election cycle; 26 named-candidate rows and six unallocated Other rows.
- `historical_council_poll_toplines_audit.csv`: all twelve acquired releases, ten wards, 52 named-candidate rows and twelve Other rows; explicit eligibility and exclusion reasons. Repeated ward samples are distinct poll releases, not additional election outcomes. Across wards, samples are geographically distinct; this does not establish independent firm/campaign error.
- `source_audit_manifest.json`: original and recovered URLs, acquisition UTC times, SHA-256 hashes, byte counts, page counts, render paths and QA status. `acquisition.json` also retains failed attempts. PDFs, extracted text, PNG renders and raw CDX-index records remain alongside these files.

The committed corpus is [poll_responses.csv](../../data/raw/polls/historical_council/poll_responses.csv), with the complete [acquisition audit](../../data/raw/polls/historical_council/acquisition_audit.csv) and [document manifest](../../data/raw/polls/historical_council/source_documents.json). Source PDFs are retained locally under the ignored `data/source_documents/historical_council/` directory; they are not redistributed.

Scratch directory: `/private/tmp/ward-poll-uncertainty-2026-10-02/historical/`. The dataset's `source_url` always points to the original Forum document; `retrieved_url` identifies the actual archived bytes. The audit manifest contains hashes of both CSVs. No normalization, fabricated base, residual allocation or omitted-candidate zero was introduced.

## Primary comparable cohort

Election day was October 24, 2022. These samples are 39–41 days before election day and therefore inside the agreed 21–45 day comparison window. They provide six contests, not 26 independent calibration trials. Each PDF's ward mayoral question is another question of the same respondent sample; it is excluded from the Council corpus.

| Ward | Fieldwork end | Printed release | Recruited sample | Council table base | Named shares; Other (%) |
|---|---|---|---:|---:|---|
| 4 | Sep 13 | Sep 14 | 228 | 162 | Perks 52; Agrell 21; Lhamo 6; Gorham 10; Other 11 |
| 5 | Sep 13 | Sep 14 | 211 | 153 | Nunziata 52; Padovani 28; Takang 8; Other 12 |
| 10 | Sep 14 | Sep 15 | 208 | 105 | Engelberg 8; Malik 52; Achampong 5; Nation 13; Other 22 |
| 13 | Sep 14 | Sep 15 | 217 | 90 | Moise 41; Lester 10; Ward 26; Other 23 |
| 20 | Sep 15 | Sep 16 | 216 | 165 | Crawford 39; Berardinetti 21; Rupasinghe 2; Kandavel 9; Ahmad 4; Ahmed 1; Mills 8; David 4; Other 14 |
| 22 | Sep 15 | Sep 16 | 207 | 118 | Nick Mantas 43; Antonios Mantas 5; Khatchadourian 23; Internicola 9; Other 21 |

Every Council table is on PDF page 2 and labels its denominator decided/leaning. Table bases are labeled only Sample; the documents do not identify them as weighted, unweighted or effective sample sizes. `base_kind=reported_table_base` preserves that limitation. Page 1 describes an IVR telephone survey of randomly selected eligible ward voters. The total-sample polling precision claim does not establish election-day predictive uncertainty for Council shares. Printed release dates are document dates; acquisition did not independently prove their original public-availability timestamps.

The tables rather than contradictory headline prose govern extraction. Ward 4 prose gives a decided/leaning base of 160 versus the table's 162. Ward 5 prose gives 112 versus 153. Ward 10 headline prose refers to all 208 recruited respondents although the Council table base is 105. Small age cells are visible, including zero under-25 respondents in Ward 22 and only two age-25–34 respondents in Ward 20. No design effect is supplied.

Ward 20 totals 102%; Ward 22 totals 101%. With nine and five rounded categories respectively, those totals can arise from whole-percentage rounding and were retained. More fundamentally, Other is not automatically final-ballot unnamed votes: the Wards 5 and 20 Council tables name every final candidate yet retain 12% and 14% Other. Do not allocate those shares across named or unnamed candidates or silently renormalize them. Named shares can be compared descriptively with official outcomes while retaining this observation-to-ballot mismatch.

## Official outcome join

All 26 primary named responses join to official 2022 Council candidates within their ward using the locally retained Results release `results-2026-09-30.2`, source authority Toronto City Clerk, source workbook `data/interim/results/2022/2022_Toronto_Poll_By_Poll_Councillor.xlsx`. The CSV retains official candidate name, vote count, vote share, contest ID and election date. See the City's [certification of 2022 results](https://www.toronto.ca/news/toronto-city-clerk-certifies-2022-toronto-municipal-election-results/) and [official results page](https://www.toronto.ca/city-government/elections/election-results-reports/election-results/general-election-results/).

One primary spelling correction is explicit: source Anthony Inernicola becomes official Anthony Internicola in Ward 22, while `source_response_label` retains the original. Additional-release joins similarly map Vince Crisanti to Vincent Crisanti and source John Burnside to Jon Burnside. All other named choices match exactly. Other rows have no synthetic official outcome. Cynthia Lai has no counted 2022 outcome, explained below.

The prior probe's reported margin-error standard deviation must not be reused as a fixed-pair error distribution: it compared poll top-two candidates with eventual top-two candidates, which sometimes differ. In Ward 4 the poll second was Agrell but the election runner-up was Lhamo; the fixed Perks–Lhamo poll gap was 46 points. Our primary data retain candidate identity, permitting named-share or fixed-pair comparisons without this substitution.

## Later releases: useful sensitivity, explicit exclusions

All six later documents were also fully acquired and visually verified. Three are coherent late-campaign comparisons, subject to the same denominator/Other caveats, but are six or seven days before election day rather than 21–45 days:

| Ward | Fieldwork | Recruited / Council base | Published Council shares (%) | Audit treatment |
|---|---|---|---|---|
| 1 | Oct 17 | 211 / 170 | Crisanti 53; Genser 12; Minhas 10; Ozzoude 9; Noor 1; Other 15 | Late-horizon sensitivity |
| 5 | Oct 17 | 217 / 185 | Nunziata 54; Padovani 34; Takang 2; Other 11 | Late-horizon sensitivity; same election outcome as September W5 |
| 16 | Oct 18 | 216 / 168 | Burnside 22; Alvarez-Bardales 1; Kargiannakis 4; Ksiazek 20; Mahovlich 21; Alim 15; Pachis 2; Other 15 | Late-horizon sensitivity |
| 3 | **Sep 13 as printed** | 213 / 184 | Grimes 32; Morley 29; Hu 24; Ari 3; Valle 1; Other 10 | Excluded: Oct 18 release prints September fieldwork; do not infer a corrected date |
| 13 | Oct 18 | 213 / 144 | Moise 27; Lester 7; Ward 39; Other 38 | Excluded: published vector totals 111%, beyond rounding; no correction inferred |
| 23 | Oct 19 | 204 / 166 | Lai 37; Myers 30; Jones 19; Other 13 | Excluded: intervening candidate death changes the counted field |

The Ward 13 111% total is visually present in the PDF, not an extraction error. Its named shares match the release prose, but the whole reading requires source clarification. Ward 23 contains obvious age-cell typographical errors as well; total-column values remain readable. More decisively, the City [announced Cynthia Lai's death on October 21 and that votes for her would not be counted](https://www.toronto.ca/news/impact-of-the-passing-of-councillor-cynthia-lai-on-the-scarborough-north-ward-23-election/). Pairing those shares with the remaining counted votes would misstate polling error.

There are nine usable samples across eight contests if the three late comparisons are included, still one firm and one cycle. The main window remains six samples/six contests. The audit CSV records all exclusions to prevent the misleading printed September date in the Ward 3 October document from entering the primary window automatically.

A wider-horizon check keeps the latest usable sample in each of the eight contests, giving 38 named-candidate comparisons. Its signed actual-minus-poll extremes are unchanged: −16.5219 to +25.5640 percentage points. This check does not add a second firm or election cycle. The main six-contest benchmark and its leave-one-contest-out results remain separately published in the feed.

## How this evidence is used

The released chart uses a small joint model conditional on each poll’s named set, as chosen by the user. Named source shares and same-person official shares are normalized separately within that set for modelling; original percentages remain available unchanged. Other is neither allocated nor mapped to eventual unnamed candidates. The full raw error span remains audit metadata rather than a probability interval. See [the model and validation](ward-poll-model-validation-2026-10-02.md) and [ADR 0059](../adr/0059-show-historical-error-context-for-ward-polls.md).

The corpus is too narrow to establish reliable full-field Council win probabilities. It has one historical cycle and one firm, sparse within-contest time coverage, unresolved Other meanings and changing named fields. The 2026 polls mix IVR with a non-random online panel, unlike the recovered 2022 IVR-only releases. The historical horizon is about ten days earlier than the current September 27 poll end. Transferring discrepancy across methods and cycles is an assumption, not an estimated correction. Whole-contest checks and distribution sensitivities qualify what the charts mean without turning candidate rows into independent elections.

## Leads remaining unacquired

The earlier note's Forum Ward 10 October post, Ward 11 September post and Ward 18 October post remain acquisition leads. They are not added to the twelve acquired documents or the benchmark. The five-ward 2018 Mainstreet report on Scribd also remains unauthenticated as a first-party acquisition; this bounded effort did not obtain an original pollster publication or archived first-party bytes. No second firm or second cycle has therefore been added. These are limitations of the present retained corpus, not claims that no additional historical polls exist.

## Exact document provenance

The complete machine-readable manifest retains acquisition times, errors, byte lengths and rendering records. Every entry below is a five-page PDF with all five pages visually reviewed; Council total column on page 2 and method/date on page 1.

- **4-sep**: [original Forum PDF](https://poll.forumresearch.com/data/0f87336b-4a32-498e-8411-70b1dd986581Ward%204%20News%20Release.pdf); [recovered first-party capture](https://web.archive.org/web/20250227004529id_/https://poll.forumresearch.com/data/0f87336b-4a32-498e-8411-70b1dd986581Ward%204%20News%20Release.pdf). SHA-256 `74bb49a7ce9a4759d1b933dd9a3699587c6803aa4a3cbf723948a9b70fbae397`.
- **5-sep**: [original Forum PDF](https://poll.forumresearch.com/data/74bddea4-50a4-4c53-a017-52dabdd9cb43Ward%205%20News%20Release.pdf); [recovered first-party capture](https://web.archive.org/web/20250227004521id_/https://poll.forumresearch.com/data/74bddea4-50a4-4c53-a017-52dabdd9cb43Ward%205%20News%20Release.pdf). SHA-256 `73e01b0fd533a1dffeab6ebc8b79fab0cdf2815dba23482797e85b8a1019dbd4`.
- **10-sep**: [original Forum PDF](https://poll.forumresearch.com/data/b390026c-ece7-475d-85f0-9cc0e050e9e0Ward%2010%20News%20Release.pdf); [recovered first-party capture](https://web.archive.org/web/20250227004457id_/https://poll.forumresearch.com/data/b390026c-ece7-475d-85f0-9cc0e050e9e0Ward%2010%20News%20Release.pdf). SHA-256 `ec7d6072e46ef91d24f55857c4172ba03fdc6c4eeff0b9bd4e98bd714b13e415`.
- **13-sep**: [original Forum PDF](https://poll.forumresearch.com/data/a199cd17-a268-43ac-a464-8c75787e2657Ward%2013%20News%20Release.pdf); [recovered first-party capture](https://web.archive.org/web/20250227004442id_/https://poll.forumresearch.com/data/a199cd17-a268-43ac-a464-8c75787e2657Ward%2013%20News%20Release.pdf). SHA-256 `7052a1572b6917208fbc5a85c593a8852f9f4af5ca4a42288889fb3f0631c729`.
- **20-sep**: [original Forum PDF](https://poll.forumresearch.com/data/00bd353b-b4c5-4efc-ba8a-7e75d5abb630Ward%2020%20News%20Release.pdf); [recovered first-party capture](https://web.archive.org/web/20221006035149id_/https://poll.forumresearch.com/data/00bd353b-b4c5-4efc-ba8a-7e75d5abb630Ward%2020%20News%20Release.pdf). SHA-256 `fd392e38eb95c03b88ad219c05919f0464ce0a59f0cbac7964df8d5e525286eb`.
- **22-sep**: [original Forum PDF](https://poll.forumresearch.com/data/2fc49a81-6baf-49bc-ad01-f22449099fb4Ward%2022%20News%20Release.pdf); [recovered first-party capture](https://web.archive.org/web/20221006043454id_/https://poll.forumresearch.com/data/2fc49a81-6baf-49bc-ad01-f22449099fb4Ward%2022%20News%20Release.pdf). SHA-256 `43e08675fae043d146d1cf2282497c29865b113d243c6d727c8eb3ca2ace9d98`.
- **1-oct**: [original Forum PDF](https://poll.forumresearch.com/data/c33fd6af-e9e0-4f30-a67d-5f1c5a335e44Ward%201%20News%20Release%20%282%29.pdf); [recovered first-party capture](https://web.archive.org/web/20250227004404id_/https://poll.forumresearch.com/data/c33fd6af-e9e0-4f30-a67d-5f1c5a335e44Ward%201%20News%20Release%20(2).pdf). SHA-256 `62972cb20359ec0e4d92b6bff4e54431e66e88270ac37a163f9db01d8dac0011`.
- **5-oct**: [original Forum PDF](https://poll.forumresearch.com/data/4a391231-3daa-4e46-bf07-b2969a3d8998Ward%205%20News%20Release%20%282%29.pdf); [recovered first-party capture](https://web.archive.org/web/20221025143641id_/https://poll.forumresearch.com/data/4a391231-3daa-4e46-bf07-b2969a3d8998Ward%205%20News%20Release%20(2).pdf). SHA-256 `c5d564120b5546d6de5da5967ef0572da7265601de7e2e9a482f969583132b84`.
- **3-oct**: [original Forum PDF](https://poll.forumresearch.com/data/39f8b538-ba12-41bd-949b-9fe053591addWard%203%20News%20Release%20%282%29.pdf); [recovered first-party capture](https://web.archive.org/web/20250227004400id_/https://poll.forumresearch.com/data/39f8b538-ba12-41bd-949b-9fe053591addWard%203%20News%20Release%20(2).pdf). SHA-256 `a0b82a2ee808d1fa0ecb1c7c4253da0cf3c222eedb484df515bfac207a885dea`.
- **13-oct**: [original Forum PDF](https://poll.forumresearch.com/data/1fd427fb-bc3a-467e-9799-b06249743aa1Ward%2013%20News%20Release%20%282%29.pdf); [recovered first-party capture](https://web.archive.org/web/20221023134010id_/http://poll.forumresearch.com/data/1fd427fb-bc3a-467e-9799-b06249743aa1Ward%2013%20News%20Release%20(2).pdf). SHA-256 `447d1ff444322d378ab3f25ccbfca2d49b836413e7bf112b6826bcc5fd53b677`.
- **16-oct**: [original Forum PDF](https://poll.forumresearch.com/data/49ae2b2d-076c-4e6b-b5c6-5f00b1f55858Ward%2016%20News%20Release%20%282%29.pdf); [recovered first-party capture](https://web.archive.org/web/20221023012922id_/https://poll.forumresearch.com/data/49ae2b2d-076c-4e6b-b5c6-5f00b1f55858Ward%2016%20News%20Release%20(2).pdf). SHA-256 `20cb572be926d9a1b8c6cbedc7e713a51afab76cdaa2dda14e4ba22e2cec56a0`.
- **23-oct**: [original Forum PDF](https://poll.forumresearch.com/data/a97b9d54-6e26-4c61-85f1-e424f292559dWard%2023%20News%20Release%20%282%29.pdf); [recovered first-party capture](https://web.archive.org/web/20221023045916id_/https://poll.forumresearch.com/data/a97b9d54-6e26-4c61-85f1-e424f292559dWard%2023%20News%20Release%20(2).pdf). SHA-256 `f5cd3201de9bd52aa5e0172ebd241d7d7b42e0e94bd0c3fa4076e912d321639e`.
