# Editorial figure refresh: October 2, 2026

Refresh the preferred explanatory artifacts against verified
`polling-2026-10-02.2`, pinned to `results-2026-09-30.2`. The downloaded manifest
and every asset hash were checked against the saved live source manifest. The
current full-field model contains 12 independent eligible samples, adding
Liaison September 27 and Mainstreet September 29. Alternate head-to-head
questions remain dependent readings and are not counted as additional polls.
The older September 29 analysis and superseded scenario grid remain preserved.
No ingestion, production feed or deployment is changed here.

## Figures

All seven article figures use the same Arial typography, navy labels, light grid
lines and compact spacing. Alexander is `#54C4CC`, matching the website. Chart
text is limited to titles, essential labels and short keys; detailed methods stay
in these notes. The 2023 data are unchanged, but their presentation is refreshed.


- `polling-support-since-nominations`: eight post-nomination polls, candidate
  choices, with the same one-sided trailing-average method and visual styling
  as the June 2023 chart.
- `parity-examples`: current simple polling average and three independently
  fitted hypothetical future polling sequences, with page stacks for three and
  twelve polls. See the numerical table below.
- `mainstreet-full-field-vs-head-to-head`: the latest survey's two dependent
  questions, compared on the common all-respondent denominator. Source-exact
  frozen numerical rows are in `head-to-head-source.json`.

Every figure exports PNG, PDF, SVG, HTML and Vega-Lite JSON. Figure dependencies
match the original pipeline: Altair 6.3.0 and vl-convert-python 1.9.0.post1.
`figure-inputs.json` records source feed and extraction hashes, plus the shared
article renderer and causal trend implementation. The extracted website LOESS
curves are retained for provenance but are no longer used by the article chart.

## Model scenarios and inputs

Use the production compact joint model with seven historical campaigns,
population hyperpriors and the unchanged Dirichlet election-day discrepancy.
`inputs.json` records the current campaign, all 12 original modelled readings,
Polling manifest hash, model package hashes and historical input hashes. The
simple average is Chow **51.257%**, Bradford **39.131%**, Alexander **9.612%**,
normalized among the three names. It is descriptive; the model fits individual
samples using their dates, own bases and uncertain firm effects.

The preferred three examples are retained from the original analysis: one
Liaison poll showing Bradford +12, three independent polls from Liaison, Forum
and Mainstreet showing Bradford +5, and twelve polls from six established firms
showing a tied race. Each hypothetical poll has effective named base 800 and
Alexander at 10%. For the article's Monday, October 5 publication, hypothetical polls fall between
October 6 and October 25. The three-poll schedule is October 6, 16 and 25;
the twelve-poll sequence is equally spread across October 6–25 (rounded to whole
days). The single late poll remains October 25. The real evidence is still
frozen as of October 2; no intervening polls are assumed. These are
conditional sufficient examples, not a unique threshold or a forecast of new
polls. They represent repeated sustained toplines rather than a gradual swing.

Fit each scenario with four chains, 1,000 warmup and 4,000 retained draws per
chain. Qualification requires zero divergences, worst R-hat below 1.01 and
minimum ESS 400. A failed initial fit is retried at target acceptance 0.99 and
seed +1. The baseline's initial fit had one divergence and was excluded; its
qualified retry exactly reproduces the released forecast's odds to rounding.
Per-scenario JSONs record final settings and diagnostics. The baseline's
`baseline-named-result.npz` supports the independently documented
[Alexander transfer scenarios](../alexander-transfer-2026-10-02/README.md).

## Reproduction

From the Backend root, use `.venv/bin/python docs/research/bradford-parity-2026-10-02/run.py`.
The script uses the verified release directory when available, or reconstructs
the campaign from the frozen snapshot; changed pinned model/history hashes fail
closed. Existing case results are cached; `--force` refits, and `--only` selects
one case. Then run `summarize.py` and `figure_parity_examples.py` with the figure
environment. `figure_polling_support.py` uses the frozen poll markers to compute a one-day
half-life trailing average, eased forward for 24 hours after each update;
`extract_polling_trend.cjs` recreates it from the release feed when invoked from
the frontend root. `figure_head_to_head.py` retains a frozen source fallback.

The stage-matched fragmentation figures are updated in the Polling repository's
`docs/research/poll-fragmentation/`. The historical data and October 5 target
cutoff remain unchanged; current coverage is 10 samples from six firms, with
centroid gap **13.9881 points** and **2.33036 effective named candidates**.
This is a different window, field handling and aggregation from the model's
simple named-three average. The selection is a 60-day lookback ending 21 days
before election day, not the final three weeks of election polling.

## Latest head-to-head evidence

Chow gains 9.0 points and Bradford 8.7 points when all other candidates are
removed from Mainstreet's September 28–29 question; Chow's all-respondent lead
is 5.9 points in the full field and 6.2 points head-to-head. Undecideds remain
allowed. This cannot identify Alexander-specific transfers or be treated as
another independent sample. See [the primary-source review](../mainstreet-head-to-head-2026-10-02.md).


## Refreshed numerical table

| Evidence scenario | Chow win | Bradford win | Alexander win |
| --- | ---: | ---: | ---: |
| Current evidence | 76.49% | 23.23% | 0.27% |
| One late Liaison poll: Bradford +12 | 48.31% | 51.39% | 0.31% |
| Three polls / three firms: Bradford +5 | 48.25% | 51.39% | 0.36% |
| Twelve polls / six firms: tied | 48.58% | 51.11% | 0.31% |

All four fits pass qualification with the full production draw count. The three
hypothetical examples remain near parity (Bradford 51.1–51.4%). The baseline
reproduces the released forecast exactly within printed rounding. The original
September 29 baseline was Bradford 24.3%; the new baseline is 23.2%. The
[fixed Alexander transfer scenarios](../alexander-transfer-2026-10-02/README.md)
now give Bradford 27.2% under the one-third/one-tenth split and 41.6% under
complete transfer. Historical fragmentation and the 2023 consolidation estimate
are unchanged. Applying the earlier 27% pool analogy to the new simple named-three
poll average gives a 2.60-point Bradford gain and a remaining Chow lead of
9.53 points, so the draft's approximate 2.6-point / 10-point description still holds.

PNG layouts were inspected for labels and clipping. Poll counts and uniqueness,
new-sample inclusion, alternate-question exclusion, hypothetical future dates,
probability sums, release pins and historical-region equality were checked. The
research Python scripts pass Ruff.

The October 6–25 schedule was refitted for the Monday article. Both changed
cases qualify; the baseline and October 25 singleton are unchanged. The prior
October 3–25 schedule gave Bradford 50.78% with three polls and 51.52% with
twelve; revised values are 51.39% and 51.11%, respectively.
