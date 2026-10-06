# Alexander transfer scenarios: October 2 refresh

Uses the same qualified baseline fit as the refreshed polling-scenario figure,
with 12 eligible independent samples from verified `polling-2026-10-02.2`.
The new Liaison September 27 and Mainstreet September 29 full-field readings
enter the fit. Mainstreet's dependent head-to-head is reviewed separately in
[the source note](../mainstreet-head-to-head-2026-10-02.md); it is not inserted
as an additional independent poll or used to estimate an Alexander transfer rate.

## Results

| Scenario | Chow win | Bradford win | Alexander win |
| --- | ---: | ---: | ---: |
| Unchanged fit | 76.49% | 23.23% | 0.27% |
| One-third to Bradford, one-tenth to Chow; rest with Alexander | 72.76% | 27.23% | 0.01% |
| All Alexander votes to Bradford | 58.40% | 41.60% | 0% |

Removing the unresolved 56⅔% from the named field instead yields Bradford
27.24%, effectively the same partial-transfer answer. The partial-transfer gain
is 4.00 percentage points, with across-chain
simulation standard error 0.11 points; the complete-transfer
gain is 18.37 points, with simulation error
0.35 points. These errors describe computation, not real-election
uncertainty or uncertainty about how supporters would react.

## Interpretation and reproduction

Reallocate Alexander's share in each joint election-day predictive draw and
recount the winner. These are fixed conditional allocations, not refits of
hypothetical ballot answers and not a forecast of campaign suspension. The
one-third/one-tenth split is illustrative; the paired polls do not identify
individual voter transfers. The all-to-Bradford case is an extreme transfer
scenario, not a general bound on how the race might change. The name remains
on the certified ballot. No ingestion, production feed or deployment is changed.

First run `../bradford-parity-2026-10-02/run.py --only baseline` to reproduce the
qualified draws, then run `.venv/bin/python docs/research/alexander-transfer-2026-10-02/run.py`
from the Backend root. `result.json` records input and draw hashes, model
qualification diagnostics, transfer fractions, probability gains, mean shares,
and margin quantiles. The September 29 analysis remains preserved.
