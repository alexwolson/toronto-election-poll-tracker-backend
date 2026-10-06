# Alexander vote-transfer scenarios: model counterfactuals

Research dated September 29, 2026. These are conditional calculations,
not a candidate-withdrawal forecast. Alexander cannot leave the certified ballot.
No poll input, model parameter, production feed, or release is changed.

## Method

Use the pinned September 29 current campaign from
[`../bradford-parity-2026-09-29/inputs.json`](../bradford-parity-2026-09-29/inputs.json),
the production compact joint model, all seven historical campaigns, the population
hyperpriors, and production fit settings (four chains, 1,000 warmup and 4,000
retained draws). The script verifies the pinned model and historical input hashes.

For **each election-day predictive draw**, allocate one-third of Alexander's
named-result share to Bradford and one-tenth to Chow, then recount the winner.
Treat the remaining 56⅔% two ways: leave it with Alexander, or remove it from
the named-candidate field (as if those voters chose someone else, abstained, or
left the mayoral ballot blank). For comparison, also allocate all of Alexander's
share to Bradford. The existing posterior and every other candidate's share stay
fixed. Because the model's named-result candidates all receive the same
`(1 - tail)` full-ballot scaling, these recounts preserve the published
named-candidate winner rule. They do not retroactively change poll answers or
refit a hypothetical different ballot.

## Result

| Scenario | Chow win | Bradford win | Alexander win |
| --- | ---: | ---: | ---: |
| Unchanged model | 75.49% | 24.28% | 0.23% |
| One-third to Bradford, one-tenth to Chow; remainder with Alexander | 72.01% | 27.99% | 0.01% |
| Same split; remainder leaves named-candidate field | 72.01% | 27.99% | 0% |
| All Alexander result votes assigned to Bradford | 58.89% | 41.11% | 0% |

Under the partial split, Bradford gains about **3.71 percentage points** of win
probability. The across-chain Monte Carlo standard error is 0.21 percentage
points. The model's mean Alexander result share is 8.91%, so this rule shifts
about 2.97 points to Bradford and 0.89 points to Chow on average, narrowing
their gap by about 2.08 points. The unresolved remainder hardly affects winner
odds because Alexander was already a very unlikely winner. The all-to-Bradford
scenario raises his chance by 16.83 points; its Monte Carlo standard error is
0.33 points. The fit passes production numerical qualification: zero divergent
transitions, worst R-hat 1.0012 and minimum effective sample size 4,178.

These probabilities are conditional on the model's existing predictive draws
and the stipulated transfers. The one-third/one-tenth split is an illustrative
interpretation of limited polling evidence, not a measured individual-level
transfer rate. The calculations do not estimate the chance of Alexander making
such a request, how many supporters would follow it, or any other campaign
reaction. The all-to-Bradford result is an extreme *vote-transfer scenario*,
not an upper bound on every possible way the race could change.

## Reproduction

From the Backend repository root:

```bash
.venv/bin/python docs/research/alexander-full-transfer-2026-09-29/run.py
```

The script writes [`result.json`](result.json) with the complete numerical
diagnostics and pinned manifest hash. `ruff check` passes for the script.
