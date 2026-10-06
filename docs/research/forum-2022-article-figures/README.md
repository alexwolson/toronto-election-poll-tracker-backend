# Forum's 2022 ward polling: article figures

Two Altair figures in the article's established Arial/navy/light-grid style.
Blue circles mark polls; arrows point from each poll to its result. Both the
shaft and arrowhead are teal for increases and orange for decreases; result
number labels use the same direction colours.
Both titles are neutral:

- `forum-2022-lead-errors`: poll leader versus the strongest other named candidate
  in the final result, holding the candidate pair fixed between poll and result.
  This avoids substituting the poll runner-up for the election runner-up.
- `forum-2022-candidate-shares`: all 26 named candidates in all six comparable
  contests, sorted by final share within each ward. No candidate-level omissions
  or selection by size of the miss.

The audited cohort contains Forum polls in Wards 4, 5, 10, 13, 20 and 22, with
fieldwork ending September 13–15, 2022, 39–41 days before the October 24 election.
These are the six observations in the other agent's registered 21–45-day
historical comparison window. Later polls are outside this figure's cohort.
All six reported leaders ultimately won. The figures demonstrate errors in
shares and the size of the lead, rather than incorrect winner calls.

`source-poll-responses.csv` is a frozen copy of the other agent's audited corpus
from `/private/tmp/ward-poll-uncertainty-2026-10-02/backend/data/raw/polls/historical_council/`.
It retains exact published percentages, source/retrieved URLs, document hashes,
question-level bases, official candidate identities and the Results release pin
`results-2026-09-30.2`. The [source audit](../ward-poll-uncertainty-source-audit-2026-10-02.md)
records acquisition and visual checks of the original Forum tables. Official
outcomes are from the Toronto City Clerk. Source PDF bytes are not redistributed.

For each ward, displayed poll shares equal 100 times the published share divided
by the summed published shares of named candidates. Displayed results equal
100 times official votes divided by official votes for those exact same names.
Other is excluded without allocation; omitted candidates are excluded from both
sides. This matches the named-set denominator in the ward modelling work.
Original unnormalized shares remain in `candidate-comparisons.csv` alongside
these displayed values. Ward 20 and Ward 22's rounded source totals are preserved
in the original CSV, rather than edited to total 100.

The mean absolute candidate-share discrepancy is 10.96 points, and the largest
is 26.58 points. These are descriptive summaries of 26 rows within six contests,
not 26 independent calibration trials. The observed differences combine sampling,
survey error, question/ballot differences and actual movement over the remaining
campaign. They do not isolate a causal pollster bias or establish 2026 coverage.

Run `figures.py` from the Backend root using the existing figure environment:
Altair 6.3.0 and vl-convert-python 1.9.0.post1. It checks unit-sum normalization,
26 candidate rows, six ward identities and preservation of the leading candidate.
PNG layouts were visually inspected, and the script passes Ruff. Each figure
exports PNG at 2×, PDF, SVG, HTML and Vega-Lite JSON. CSVs permit numerical review;
`figure-exports.json` records SHA-256 hashes and descriptive summaries.

## Five current polls with descriptive historical bands

`forum-2026-historical-error-bands` shows every named candidate in Forum's five
September 26–27, 2026 ward polls. Dots are reported shares normalized across
named candidates, excluding Other. They are descriptive poll estimates, not
fitted model medians. `source-2026-five-polls.csv` retains the exact published
shares, and `current-poll-provenance.json` pins the verified Polling release.

The dark inner band is ±11.410591 points. For each of the six 2022 wards, take
the mean absolute named-candidate share difference between poll and result,
then average those six ward means equally. This avoids letting the eight-name
Ward 20 table dominate the three-name tables. The light outer band is ±26.576085
points, the largest absolute named-candidate difference in the entire cohort.
These magnitudes are applied symmetrically around each current poll share, with
endpoints clipped to the valid 0–100% share range. The 2022 inputs use the same
named-set normalization on the poll and official result.

Neither band has a coverage probability. The largest observed historical miss
is not a guaranteed worst-case bound for 2026. These marginal displays also do
not form a joint vote distribution or establish candidate win probabilities.
The older polls ended 39–41 days before election day; the current polls ended
29 days before election day and used IVR plus an online panel, rather than IVR
alone. No unsupported horizon or mode correction is applied.

Run `figure_current_bands.py` with the same figure environment. It verifies five
independent samples, 21 named candidate rows, unit-sum normalization and all six
historical comparison wards. Its CSV records the published and normalized
shares and all four endpoints. PNG, PDF, SVG, HTML and Vega-Lite JSON are saved,
with hashes and exact error magnitudes in `current-bands-exports.json`.
