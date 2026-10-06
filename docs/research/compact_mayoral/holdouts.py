"""Tabulate held-out election checks written by ``fit.py --holdout``.

Usage::

    uv run --no-project python -m docs.research.compact_mayoral.holdouts <runs_dir> [prefix]

Reads every ``<runs_dir>/<prefix>*/summary.json`` whose held-out campaign carries a
``holdout`` record and prints one row per (horizon, campaign, variant): polls used,
leaders known at the horizon, actual leader margin, predicted margin (p10/p50/p90),
the margin's PIT, 80% coverage and the probability assigned to the actual winner.
Also writes ``<runs_dir>/<prefix>table.json``. For CRPS, log scores and the
pre-registered decision rule see ``evaluate.py``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def rows_from(runs_dir: Path, prefix: str) -> list[dict]:
    rows = []
    for path in sorted(runs_dir.glob(f"{prefix}*/summary.json")):
        summary = json.loads(path.read_text(encoding="utf-8"))
        config = summary["config"]
        for key, record in summary["campaigns"].items():
            if "holdout" not in record:
                continue
            h = record["holdout"]
            m = record["leader_margin_election"]
            scales = summary["shared_scales"]
            rows.append(
                {
                    "run": path.parent.name,
                    "horizon_days": h["horizon_days"],
                    "campaign": key,
                    "variant": config["variant"],
                    "innovations": config.get("innovations", "gaussian"),
                    "polls_used": h["polls_used"],
                    "leaders": record["leaders"],
                    "actual_margin": h["leader_margin_actual"],
                    "margin_q10": m["q10"],
                    "margin_q50": m["q50"],
                    "margin_q90": m["q90"],
                    "margin_pit": h["leader_margin_pit"],
                    "margin_covered_80": h["leader_margin_covered_80"],
                    "actual_winner": h["actual_winner"],
                    "p_actual_winner": h["p_actual_winner"],
                    "tau_election": scales.get("tau_election", {}).get("mean"),
                    "tau_lead": scales.get("tau_lead", {}).get("mean"),
                    "tau_rest": scales.get("tau_rest", {}).get("mean"),
                    "gamma_election": scales.get("gamma_election", {}).get("mean"),
                    "phi_election": scales.get("phi_election", {}).get("mean"),
                    "divergences": summary["diagnostics"]["divergences"],
                    "worst_r_hat": summary["diagnostics"]["worst_r_hat"],
                }
            )
    return rows


def scales_label(r: dict) -> str:
    if r.get("phi_election") is not None:
        return f"phi {r['phi_election']:.1f}"
    if r["tau_election"] is None:
        return f"lead {r['tau_lead']:.2f} rest {r['tau_rest']:.2f}"
    label = f"{r['tau_election']:.2f}"
    if r.get("gamma_election") is not None:
        label += f" g {r['gamma_election']:.2f}"
    return label


def render(rows: list[dict]) -> str:
    head = (
        f"{'H':>3s} {'campaign':13s} {'variant':15s} {'innov':9s} {'n':>2s} {'leaders':24s} "
        f"{'actual':>7s} {'p10':>6s} {'p50':>6s} {'p90':>6s} {'PIT':>5s} {'80%':>4s} "
        f"{'P(win)':>6s} {'div':>4s} {'scales':>18s}"
    )
    lines = [head, "-" * len(head)]
    order = lambda r: (-r["horizon_days"], r["campaign"], r["variant"], r["innovations"])
    for r in sorted(rows, key=order):
        lines.append(
            f"{r['horizon_days']:>3d} {r['campaign']:13s} {r['variant']:15s} {r['innovations']:9s} "
            f"{r['polls_used']:>2d} {' / '.join(n.split()[-1] for n in r['leaders']):24s} "
            f"{100 * r['actual_margin']:>+7.1f} {100 * r['margin_q10']:>+6.1f} "
            f"{100 * r['margin_q50']:>+6.1f} {100 * r['margin_q90']:>+6.1f} "
            f"{r['margin_pit']:>5.2f} {'yes' if r['margin_covered_80'] else 'NO':>4s} "
            f"{r['p_actual_winner']:>6.2f} {r['divergences']:>4d} {scales_label(r):>18s}"
        )
    return "\n".join(lines)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        sys.exit("usage: holdouts.py <runs_dir> [prefix]")
    runs_dir = Path(argv[0])
    prefix = argv[1] if len(argv) > 1 else "holdout"
    rows = rows_from(runs_dir, prefix)
    if not rows:
        sys.exit(f"no held-out summaries under {runs_dir}/{prefix}*")
    (runs_dir / f"{prefix}table.json").write_text(
        json.dumps(rows, indent=2) + "\n", encoding="utf-8"
    )
    print(render(rows))
    groups = sorted({(r["variant"], r["innovations"]) for r in rows})
    for variant, innovations in groups:
        for horizon in sorted({r["horizon_days"] for r in rows}, reverse=True):
            sub = [
                r
                for r in rows
                if r["variant"] == variant
                and r["innovations"] == innovations
                and r["horizon_days"] == horizon
            ]
            if not sub:
                continue
            covered = sum(r["margin_covered_80"] for r in sub)
            pits = sorted(r["margin_pit"] for r in sub)
            divergent = sum(r["divergences"] for r in sub)
            print(
                f"\n{variant}/{innovations} @ {horizon}d: {len(sub)} elections | margin 80% coverage "
                f"{covered}/{len(sub)} | divergences {divergent} "
                f"| PITs {[f'{p:.2f}' for p in pits]} | mean P(actual winner) "
                f"{sum(r['p_actual_winner'] for r in sub) / len(sub):.2f}"
            )
    return rows


if __name__ == "__main__":
    main()
