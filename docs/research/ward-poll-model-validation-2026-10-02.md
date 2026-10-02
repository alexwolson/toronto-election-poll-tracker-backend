# Conditional ward-poll model: design and evaluation

October 2, 2026. This implements the user's chosen modelled view among poll-named candidates. The source corpus and its limitations are documented in [the source audit](ward-poll-uncertainty-source-audit-2026-10-02.md). Primary methodological sources and the modelling ladder are in [the research note](ward-poll-modelling-options-2026-10-02.md). Those papers motivate modelling principles, not the numerical priors used here.

## Model and assumptions

Each historical poll's named shares are divided by their named-share total; official outcomes for exactly the same candidates are separately divided by their official named-share total. One Dirichlet result vector per ward is centred on the poll vector. Ward concentration varies lognormally: `log(kappa_w) ~ Normal(mu, tau)`, with `mu ~ Normal(log(30), 1.5)` and `tau ~ HalfNormal(1)`. Concentration governs total poll-to-result discrepancy and is **not a respondent count**. Numerical integration retains posterior uncertainty in both hyperparameters and draws a new ward concentration for each predictive result. Every joint result sums to one. Source percentages and Other remain unchanged outside this modelling transform.

The six historical joint vectors yield 26 named-candidate comparisons, not 26 independent election trials. Sampling, bias, campaign movement and response mapping remain combined. No current nominal-sample-size shrinkage is applied: unknown effective n and the IVR-to-mixed-mode/cycle transfer cannot be learned here. This is an explicit stationarity assumption, not an assurance of conservative or calibrated coverage. The model does not estimate unreported names, their combined eventual vote, whole-ward winners, candidate-specific effects, or time-series dynamics.

A 100,000-draw seed-fixed mixture produces median and central 80% marginal intervals; marginal medians need not add to one. Typical concentration's prior median 30 is a regularizer with broad log-scale dispersion; the prior also allows near-corner outcomes through uncertain ward heterogeneity. No data-dependent prior or interval-mass adjustment was made to target desired current outcomes.

## Whole-contest validation

We refit six times, removing the entire held-out contest. Table entries are named-candidate results contained in the declared marginal interval; candidate rows within a ward are dependent. Coverage counts are descriptive and do not establish future calibration. Scores use the proper central-80% interval score `width + 10*(lower-actual)_+ + 10*(actual-upper)_+`, averaged within a ward and then equally across wards. They combine sharpness and misses.

| Held-out ward | Named candidates | In 80% | In 95% | Mean 80% width (points) | Mean interval score |
|---|---:|---:|---:|---:|---:|
| 10 | 4 | 3 | 4 | 25.3 | 0.4450 |
| 13 | 3 | 3 | 3 | 34.3 | 0.3425 |
| 20 | 8 | 6 | 8 | 19.1 | 0.3632 |
| 22 | 4 | 3 | 4 | 28.2 | 0.2917 |
| 4 | 4 | 2 | 3 | 26.1 | 0.7569 |
| 5 | 3 | 3 | 3 | 32.6 | 0.3256 |

Across these six same-cycle tests, 20/26 named results were inside 80% bands and 25/26 inside 95% bands. Ward 4 remains influential: two of its four results miss the 80% intervals and one misses 95%. This is a real failure retained in the audit, not repaired with a coverage-tuned multiplier. Mean equal-contest interval score is 0.4208. There is no second cycle for leave-one-cycle-out testing.

## Sensitivity and numerical checks

The posterior new-ward concentration 10th/50th/90th percentiles are 5.76, 10.68, 18.98. Shifting the population concentration prior median from 30 to 10 or 100 moves current 80% endpoints by at most 0.7 percentage points; reducing the heterogeneity prior scale from 1 to 0.5 moves them at most 0.3 points. These checks do not address unobserved cross-cycle bias.

The one-scale logistic-normal alternative fits exchangeable centred log-share offsets with `log(sigma) ~ Normal(log(0.8), 1)` and integrates that scale. Its held-out mean equal-contest interval score is 0.5120; it covers 21/26 at 80% and 25/26 at 95%. It is generally wider but still misses historical results. Current interval endpoints differ by up to 21.8 points, a material family assumption. The simpler Dirichlet model was specified before this evaluation; the tiny comparison cannot establish it as the true distribution. The site explicitly reports the material shape sensitivity and calls the outputs rough model-based estimates. No averaging weights are fitted from six wards.

The integration grid is mu [-4,10] by 0.04 and tau [0,4] by 0.04. Builds fail if posterior outer-edge mass exceeds 0.001. Comparing 32 with 64 Gauss–Hermite nodes yields total variation 0.000104, below the 0.005 numerical gate. Each current prediction is independently replicated; endpoint/median deviations must stay below one percentage point. Current maximum replication difference is 0.30 points. These checks establish computation stability, not empirical calibration.

## Presentation

The five current final-field pages use the same reusable range-chart component as the mayoral view. They state shares are conditional on the poll's named candidates, show the actual Council decided/leaning response base and source link, retain original toplines in a disclosure, and link to the model/evidence limitations. No Kalman filter, full-ballot winner odds or residual allocation is introduced.
