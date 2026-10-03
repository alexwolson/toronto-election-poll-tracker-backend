# Sparse ward-poll modelling options

Research date: October 2, 2026. Proposal only; no implementation or publication change. This follows the [source audit](ward-poll-uncertainty-source-audit-2026-10-02.md).

**Yes: six historical contests can support a small probabilistic model and an honest evaluation of its usefulness.** They cannot demonstrate strong calibration across future cycles. Uncertainty about that limitation should enter the model and presentation; it need not prohibit modelling altogether.

## Three methodological sources

[Shirani-Mehr, Rothschild, Goel and Gelman, *Disentangling Bias and Variance in Election Polls*](https://5harad.com/papers/polling-errors.pdf) distinguish sampling variation, extra variance and election-level polling bias. Their Bayesian analysis uses many polls and elections; correlated election error is a substantive issue. This supports estimating total poll-to-result discrepancy rather than attaching ordinary sampling margins. Their numerical scales and two-party structure are not transferable Toronto parameters.

[Stoetzer et al., *Forecasting Elections in Multiparty Systems*](https://www.cambridge.org/core/services/aop-cambridge-core/content/view/CA929544F672A09A0E34C5529EBFA482/S1047198718000499a.pdf/forecasting_elections_in_multiparty_systems_a_bayesian_approach_combining_polls_and_fundamentals.pdf) model composition through log-ratios and integrate parameter uncertainty into predictive distributions. They combine polls, fundamentals and dynamics. The useful principles here are joint shares and integration over uncertain parameters; copying their random walk, covariance matrix or fundamentals component would require evidence absent from these ward polls.

[Vehtari, Gelman and Gabry, *Practical Bayesian model evaluation using leave-one-out cross-validation and WAIC*](https://arxiv.org/abs/1507.04544) discuss predictive scoring from Bayesian fits, importance-sampling diagnostics and influential observations. For this tiny corpus, six actual held-out-contest refits are feasible and easier to audit than an approximation. Choosing the contest as the held-out unit is our domain-specific application, not a claim that their paper studies Toronto wards.

## A concrete first model

The following is a proposed simplification, not a model established by those papers.

For each contest, let the named set be exactly the candidates individually published in that poll. Transform their raw published shares into `q_i = poll_i / sum(named poll shares)`. Match official outcomes for those same people and calculate `z_i = result_i / sum(named result shares)`. Preserve the original source values and make the changed denominator explicit: this endpoint is **relative vote share among the named candidates**, not share of every ballot.

Fit the single joint discrepancy model `z_c ~ Dirichlet(kappa * q_c)` over six contest vectors. Here `kappa` is a pooled concentration governing total poll-to-election discrepancy, not an effective respondent count. Give its dispersion an explicit regularizing prior, inspect prior predictions on the percentage-point scale, and integrate the posterior of `kappa` when producing new predictive draws. Do not replace it with a fitted point estimate. This treats sampling, campaign movement, response mapping and nonsampling error together; it cannot separate them.

Use a one-scale logistic-normal alternative as a prespecified sensitivity: draw exchangeable candidate log-share offsets with a shared uncertain scale and apply softmax to `log(q) + offsets`. Center offsets to remove the irrelevant common shift; do not estimate a full covariance matrix or candidate-specific effects from six differently named contests. Dirichlet has a restrictive mean/variance relationship and negative component covariance; the simple logistic-normal also imposes its covariance structure. Comparing them tests how much that restriction changes conclusions. Neither shape is guaranteed by the evidence.

Use one horizon-matched poll per contest, and one joint vector per contest likelihood. The 26 named rows provide within-contest contrasts, but are not 26 independent elections. Larger named sets contain more information under the model; report evaluation scores averaged equally across contests so Ward 20 does not dominate merely because more names were printed. A pooled, uncertain contest-dispersion extension can be tested only if those diagnostics show a material need; it would be strongly prior-dependent.

## From relative shares to all ballots

Let `S` be the eventual fraction voting for the named set. Full-electorate named shares are `v_i = S * z_i`, with an aggregate final-ballot remainder `1-S`. This is distinct from the poll's Other response. Wards 5 and 20 in 2022 named every final candidate but still published Other: simply appending raw Other to a predictive Dirichlet vector would impose a false mapping.

For a poll naming the entire certified field, set `S=1` structurally. For partial fields, a small second model could relate historical eventual named-set mass to published named-set mass, for example a pooled logit-scale transfer discrepancy. Only **four** primary historical contests inform that transfer; the two complete-field cases are boundary values, not interior beta/logit observations. Propagate its parameter uncertainty and test weak versus more regularized priors. A joint fit can relate this mass error to named-share contrasts, but that dependence is not estimable reliably here. A prespecified independence assumption plus sensitivity is more transparent than learning a large covariance matrix.

If this mass component proves too prior-sensitive, publish relative-share modelling explicitly or keep full-vote outputs as assumption-based scenarios. Do not silently treat a relative-share model as a full-ballot forecast. No aggregate remainder establishes individual omitted-candidate support, so no full-field winner odds follow from either model. Even a reported candidate leading all other named candidates is a different event from winning the ward.

## Minimal evaluation and limits

Run six leave-one-contest-out refits with every poll/reading from the held-out contest excluded. Inspect posterior predictive coverage at several declared levels, interval score or CRPS, point error and joint predictive log score. Report the six results and failures, not a smooth reliability curve from 26 correlated rows. Compare with raw conditional poll shares and the existing historical-miss display; interval width alone is not improvement. Check sensitivity to removing Ward 4, whose Perks/Lhamo errors dominate the raw span, and to the three coherent late polls as a separate horizon cohort. Do not pool late polls as new independent outcomes.

Test prior strength, Dirichlet versus logistic-normal shape, rounding, named-mass assumptions and whether a heavier-tailed discrepancy changes the result. Larger 2026 mixed-mode sample sizes must not mechanically narrow predictions: effective sample sizes are unknown, and six IVR-only historical samples cannot identify a current online-panel adjustment. Treat mode-transfer and cross-cycle error as explicit, unlearned assumptions. One cycle cannot support leave-one-cycle-out validation.

The useful next step is a bounded model prototype and these six honest refits. If the result is unstable, that itself answers how much information the published toplines provide. If stable across plausible specifications, model-based vote ranges are defensible with plainly stated assumptions and limited validation; calibrated Council win odds remain a separate, unmet requirement.
