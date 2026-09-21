"""Compact joint mayoral model (ADR 0054).

A hierarchical state-space model over the seven historical Toronto mayoral
campaigns and the current one: named-candidate support as log-odds contrasts on
a random walk, firm effects, a Dirichlet poll likelihood with a learned precision
law, a pooled Student-t election-day discrepancy and a residual-pool logit. It
replaces the observation-layer machinery of the research "integrated" model with
one canonical reading per sample and reproduces that model's 2026 forecast in
seconds; see ``docs/research/compact-mayoral-model-2026-09-21.md``.

Modules: ``readings`` (inputs), ``model`` (NumPyro model), ``hyperpriors``
(shared-scale priors), ``sampling`` (NUTS fit and diagnostics), ``qualification``
(fail-closed gate). The feed builder lives in ``backend.model.compact_mayoral_feed``.
"""

import os

# Four host devices let the production fit run its chains in parallel on CPU.
# Effective only if set before JAX initializes; harmless otherwise.
os.environ.setdefault("XLA_FLAGS", "--xla_force_host_platform_device_count=4")
