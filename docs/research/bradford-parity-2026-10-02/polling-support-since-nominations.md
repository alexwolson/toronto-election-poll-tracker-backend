# Polling support since nominations closed: October 2 refresh

Eight post-nomination samples from verified `polling-2026-10-02.2`, with fieldwork
ending September 5–29, produce 24 candidate marks. The frozen marker shares retain
Other in the candidate-choice denominator; Ipsos is converted from its
all-respondent table. The head-to-head question is a dependent alternate field
and does not enter this series as a separate poll.

Both this chart and June 2023 use the same `polling_figure.py` article renderer
and trend code. Estimates update on poll dates using equal initial sample weights
and exponential decay with a one-day half-life. Each new estimate is visually
eased forward over the following 24 hours using `causal_curve.py`. Later polls
cannot change the earlier displayed curve. Only post-nomination polls enter this
trend; the extracted website LOESS is retained in the source snapshot but unused.
This is a descriptive series, not the forecast.

The two charts share filled circular marks, white outlines, opacity, line width,
Arial typography, navy axes, light grids, a bottom line legend, plot dimensions,
and compact footer styling. Chow is `#854A90`, Bradford `#2E8B57`, Alexander
`#54C4CC`. The June chart retains its Tory endorsement annotation.

The nomination cutoff is August 21, and the x-axis runs August 22–October 4.
`polling-support-trailing-average.csv` records the dated estimates. Figure exports
are PNG, PDF, SVG, HTML and Vega-Lite JSON. The older September 29 folder remains
an archived analysis. No forecasting inputs or outputs change.
