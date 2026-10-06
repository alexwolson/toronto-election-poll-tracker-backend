# What new polls would make Bradford at least as likely to win as Chow?

Research dated September 29, 2026. Hypothetical scenarios only; no real poll or production feed is changed.

## Design fixed before scenario fits

Use the production compact model, Dirichlet election-day discrepancy (ADRs 0054–0057), population hyperpriors and all seven historical campaigns. Append independent synthetic full-field samples to the September 29 Polling release, retaining its ten eligible samples. Refit all campaigns jointly; do not freeze the shared hyperparameters or substitute a weighted average.

Primary grid: one, three or twelve new polls, each reporting Bradford minus Chow of 0, +5, +10 or +20 percentage points. Alexander stays at 10% of support among the named three. Thus +5 means Chow 42.5%, Bradford 47.5%, Alexander 10%; +20 means 35%, 55%, 10%. These are conditional named-candidate shares, excluding Other and undecided; multiply all three by the named share to translate into all-respondent percentages. Effective named base is 800 in every synthetic sample. This roughly resembles recent eligible poll bases; a recruited sample of 1,000 is not necessarily an effective base of 1,000.

Dates are fieldwork ends, matching the current adapter. For multiple polls they are equally spread September 30–October 25 (26–1 days before the election). The single poll ends October 25. Release is assumed immediate. Main scenarios rotate through Liaison, Forum, Mainstreet, Pallas, Ipsos and Canada Pulse, retaining each firm's connection to its existing observations. Three polls use the first three firms. Twelve use each twice. Separate sensitivity scenarios put all three/twelve polls through Liaison, or put three polls on September 30, October 2 and October 4. Every poll is a new independent sample; repeated releases of the same sample would not qualify.

The main criterion is P(Bradford wins) − P(Chow wins) ≥ 0, not necessarily Bradford ≥50% when Alexander has a chance. Win draws use the model's three named candidates, as the published full-race cards do. A near-zero numerical difference is treated as approximate parity, with chain-to-chain simulation uncertainty reported. The model retains election-day discrepancy even under dense polling. No new polls means the same forecast as today: passage of time alone does not remove movement uncertainty (ADR 0021 and the rejected cutoff-horizon experiment).

Each fit uses four chains, 1,000 warmup iterations and initially 1,500 retained draws per chain. All numerical diagnostics are retained. Conclusions rely on fits passing the existing production qualification gate (zero divergences, worst R-hat <1.01, minimum ESS ≥400); failed fits require a longer/tighter confirmation. No assumptions are selected to obtain a preferred probability. The broad grid precedes any refinements used to bracket thresholds.

## Reproduction

From the Backend root: `.venv/bin/python docs/research/bradford-parity-2026-09-29/run.py`. The script uses the isolated September 29 release checkout when available and otherwise reconstructs the exact current campaign from `inputs.json`. That snapshot records the release manifest hash, model implementation hash, historical input hashes and complete original modelled polls. A changed input hash stops reproduction. Per-scenario JSON files cache results. They contain probabilities, margin quantiles, simulation error, diagnostics and poll dates.


## Findings

The current published forecast is Chow 75.5%, Bradford 24.3%, Alexander 0.2%. The shorter research baseline reproduces it within simulation error: 76.0%, 23.7%, 0.3%. The model's odds always concern the election-day result; they do not change merely because the calendar reaches October 26.

The main broad-grid results are below. Percentages are **Bradford's chance of winning**, not his polled vote share. Poll lead is Bradford minus Chow. Alexander is at 10% in every synthetic poll.

| New polls | Chow +5 | Tied | Bradford +5 | Bradford +10 | Bradford +20 |
|---|---:|---:|---:|---:|---:|
| 1, Liaison, October 25 | — | 30.4% | 38.3% | 47.5% | 69.0% |
| 3, three firms, September 30 / October 12 / October 25 | — | 39.7% | 51.6% | 63.8% | 82.5% |
| 12, six firms, September 30–October 25 | 38.4% | 52.4% | 64.3% | 74.8% | 89.2% |

**A few dramatic readings can cross parity; many smaller readings can also cross, but they need to show a sustained approximately tied race.** Simply adding many polls that still give Chow a lead is insufficient in the tested case. Twelve tied polls (45/45/10) and three multi-firm Bradford +5 polls (42.5/47.5/10) both land around even odds. The single-poll broad grid brackets its crossing between Bradford +10 and +20; a separate +12 confirmation refines this below.

Corroboration matters. At Bradford +5, three separate Liaison samples yield Bradford 41.0%, compared with 51.6% across Liaison, Forum and Mainstreet. Twelve Liaison samples yield 42.6%, versus 64.3% across six firms. At Bradford +10, three Liaison samples yield 52.0%, twelve yield 53.6%. The same-firm group consists of independent samples, so the difference is not duplicate-counting: the model keeps a shared uncertain firm effect. These comparisons also hold the poll dates, effective bases and toplines fixed.

Recency matters. The three-firm Bradford +5 scenario reaches 51.6% when evidence spans September 30–October 25; putting all three polls on September 30, October 2 and October 4 yields only 48.9%, approximately a toss-up. The model then carries more unobserved campaign movement to election day. This is a comparison of complete hypothetical sequences, not a claim that every late poll has a fixed extra weight.

These are concrete sufficient examples under a specified schedule, rather than a unique required topline. The singleton represents Liaison; another firm can have a different threshold. Poll sizes, fieldwork dates, dispersion of toplines, Alexander's support and contradictory subsequent polls can change the response. Identical future toplines deliberately represent sustained consensus, rather than a gradual swing or a noisy stream. A full joint refit means future evidence can also update shared model parameters. Near-parity percentages should be read as approximately even odds, not a precise decimal cutoff.

### Numerical verification and artifacts

`results.csv` contains the complete case table, predictive margin quantiles and diagnostics. The per-case JSONs retain simulation error in the probability difference, measured from variation across the four chains. This is numerical error, not uncertainty in the real election outcome. The 80% result-margin intervals remain broad even where a candidate is favoured.

`scenario-grid.png`, `.pdf`, `.svg` and `.html` were rendered with Vega-Altair 6.3.0 and vl-convert 1.9.0.post1. Points are model fits; connecting lines are visual guides, not additional evaluated thresholds. The 50% reference is approximately the equality point because Alexander retains a small winning chance; the actual decision uses Bradford's win probability minus Chow's.

The follow-up Chow +5 / twelve-poll case and Bradford +12 / singleton case were selected after the broad grid to bracket the crossing. This is scenario exploration, not a fitted correction to polling or validation of a new model. All original evidence and production code remain unchanged.


The singleton refinement reports Chow 39%, Bradford 51%, Alexander 10% (Bradford +12), released after fieldwork ends October 25. Its confirmed result is **Bradford 52.0%, Chow 47.7%, Alexander 0.4%**. Thus the tested single-poll crossing is between +10 and +12; these are numerical brackets, not an exact universal cutoff. The first +12 fit had one divergent transition and is excluded from conclusions (`n1-lead12-initial.json`). The confirmation uses the production retry convention (target acceptance 0.99, seed +1) and increases retained draws to 4,000 per chain; zero divergences and all qualification criteria pass. Reproduce it with `run.py --only n1-lead12 --force --target-accept .99 --seed 20260922 --draws 4000`.

Three early Bradford +10 polls give Bradford 58.4% / Chow 41.5%, compared with 63.8% / 35.8% under the spread-through-October-25 schedule. All **21 final scenario fits** pass the production qualification gate. The failed initial singleton is retained for audit. Scenario construction, probability sums, dates and case coverage were checked, and all three research scripts pass Ruff.

To render the figure: install `requirements-figure.txt` in an isolated environment, then run `figure.py`. To rebuild the portable table, run `summarize.py`.


### Presentation revision

`parity-examples.{png,pdf,svg,html}` is the preferred explanatory figure. It presents the three tested near-parity examples as polling inputs → model result, with direct candidate labels, firm counts and fieldwork dates. The original scenario-grid curve remains available for inspecting the complete response grid. Reproduce the revised figure with `figure_parity_examples.py`.

The explanatory figure now includes the simple average of the ten original eligible readings: Chow 51.64%, Bradford 38.78%, Alexander 9.58%, conditional on these names. This descriptive average is separate from the model fit, which uses individual polls, dates, sample precision and firm effects. The baseline odds come from the qualified research baseline. Candidate fills match the frontend CSS: Chow #854A90, Bradford #2E8B57, Alexander #54C4CC.
