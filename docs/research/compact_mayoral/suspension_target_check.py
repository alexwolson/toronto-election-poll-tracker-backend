"""Target check for S2's kept fraction: leave one recorded case out (report only).

Usage (from the backend root)::

    uv run python -m docs.research.compact_mayoral.suspension_target_check

For each case in the suspension table with a kept fraction, S2's log-normal is
estimated from the other usable cases (all cities, as production S2 uses them) and
scored on the held-out case. The baseline has no suspension term, so its implied kept
fraction is 1: the candidate keeps their last pre-suspension poll share. Decided on
2026-10-07 (backend issue 45, after its results) as a report, not a gate.
"""

from __future__ import annotations

import math
from statistics import NormalDist

import numpy as np

from .suspensions import kept_fraction, load_suspensions

Z80 = NormalDist().inv_cdf(0.9)


def leave_one_out(cases: list[tuple[str, float]]) -> list[dict]:
    out = []
    for i, (case, keep) in enumerate(cases):
        logs = [math.log(k) for j, (_, k) in enumerate(cases) if j != i]
        mu, sigma = float(np.mean(logs)), float(np.std(logs, ddof=1))
        lo, hi = math.exp(mu - Z80 * sigma), math.exp(mu + Z80 * sigma)
        out.append(
            {
                "case": case,
                "kept": keep,
                "median": math.exp(mu),
                "low": lo,
                "high": hi,
                "covered_80": lo <= keep <= hi,
                "pit": NormalDist(mu, sigma).cdf(math.log(keep)),
                "s2_log_error": abs(math.log(keep) - mu),
                "baseline_log_error": abs(math.log(keep)),
            }
        )
    return out


def main() -> list[dict]:
    cases = [(r["case_id"], k) for r in load_suspensions() for k in [kept_fraction(r)] if k]
    rows = leave_one_out(cases)
    for r in rows:
        print(
            f"{r['case']:26s} kept {r['kept']:.3f} | S2 median {r['median']:.3f}"
            f" 80% {r['low']:.3f}–{r['high']:.3f} covered {r['covered_80']!s:5s}"
            f" PIT {r['pit']:.3f} | log error S2 {r['s2_log_error']:.2f}"
            f" baseline {r['baseline_log_error']:.2f}"
        )
    print(
        f"S2 covered {sum(r['covered_80'] for r in rows)}/{len(rows)}; mean absolute log error"
        f" S2 {np.mean([r['s2_log_error'] for r in rows]):.2f}"
        f" vs baseline {np.mean([r['baseline_log_error'] for r in rows]):.2f}"
    )
    return rows


if __name__ == "__main__":
    main()
