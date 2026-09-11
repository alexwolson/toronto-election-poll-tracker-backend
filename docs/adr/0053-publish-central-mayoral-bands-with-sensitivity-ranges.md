---
status: accepted
---

# Publish central mayoral bands with sensitivity ranges

Following the user's decision to replace the design that suppresses stable forecasts at band boundaries, the mayoral feed will publish the authoritative model's approximate out-of-five band and retain the complete mandatory sensitivity envelope as audit metadata. The same-band requirement in ADRs 0018/0049 is superseded for this mayoral presentation; the shared legacy gate remains available to other consumers. The existing rare-event phrases below 5% and at or above 95% remain unchanged.

The band is a rounding convention for the central forecast, not an empirically established accuracy tier. Sensitivity endpoints include the existing simulation-error intervals and round outwards to whole percentages. They describe variation across model assumptions, not a confidence interval. All registered runnable variants are included; the authoritative bridge is labelled `authoritative`, and other variants `stress_test`, including the unqualified incumbency challenger. No variant is silently promoted by inclusion in a range.

Ballot, evidence-tier, historical-unlock and operational-integrity requirements remain. Missing required computations, duplicate labels and missing central estimates withhold the quantity. Crossing a rounding boundary, a wide assumption range or disagreement about the favourite does not itself remove numerical summaries. Favourite agreement is reported separately from the central probability.

After reviewing the local preview, the user explicitly rejected exposing internal diagnostics in the frontend. The public page therefore shows the favourite and familiar odds bands, with no numerical assumption ranges, model-comparison table or simulation-error explanation. Detailed comparisons remain in the research outputs and feed audit metadata. The methodology explains the approach in plain language; retaining audit metadata is not a request to render it.

This is feed schema 3 and publication policy `central-band-with-sensitivity-v1`. Historical schema-2 releases remain readable and unchanged. The predictor is still the qualified main bridge: this publication decision does not qualify the experimental evidence-responsive replacement. Model adoption depends on the separately reported statistical comparisons, not on whether a preferred band reappears.
