"""Issue 50 diagnostics (report only): how the uniform rule loses in 2010 and fails in 2023.

Usage (from the backend root)::

    uv run python -m docs.research.compact_mayoral.uniform_rule_diagnose 2010 <out_dir>
    uv run python -m docs.research.compact_mayoral.uniform_rule_diagnose 2023 <out_dir> [run ...]

Reads the stored runs of issue 48 (``research-runs/uniform-rule-2026-10-07``) and of the
seed-replicate test (``research-runs/suspension-replicates-2026-10-06``, for S2).
"""

from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from datetime import timedelta
from pathlib import Path

import numpy as np

from . import evaluate as ev
from .readings import Paths, historical_campaigns, with_horizon
from .suspensions import keep_distribution, load_suspensions, suspend
from .uniform_rule import fold_held_out_suspensions

WORKSPACE = Path(__file__).resolve().parents[4]
RUNS = WORKSPACE / "research-runs" / "uniform-rule-2026-10-07" / "runs"
S2_RUNS = WORKSPACE / "research-runs" / "suspension-replicates-2026-10-06" / "runs"
SEEDS = (20260921, 20260922, 20260923, 20260924, 20260925)
RACE = "toronto_2010"


def q(x, probs=(0.1, 0.5, 0.9)):
    return [float(v) for v in np.quantile(np.asarray(x, dtype=float), probs)]


def load_run(run: Path, race: str):
    summary = json.loads((run / "summary.json").read_text(encoding="utf-8"))
    rec = summary["campaigns"][race]
    with np.load(run / "draws.npz") as d:
        named = np.asarray(d[f"{race}/named_result"]).reshape(-1, len(rec["candidates"]))
        tail = np.asarray(d[f"{race}/tail"]).reshape(-1)
    return summary, rec, named, tail


def published(reading_ids: set[str]) -> dict[str, dict[str, float]]:
    out = defaultdict(dict)
    path = Paths().historical / "poll_responses.csv"
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["poll_reading_id"] in reading_ids and row["share"] != "":
                label = row["candidate_name"] or row["response_label"] or row["response_kind"]
                out[row["poll_reading_id"]][label] = float(row["share"])
    return out


def count_shares() -> dict[str, float]:
    path = Paths().outcomes
    with path.open(encoding="utf-8", newline="") as handle:
        return {
            r["candidate_name"]: float(r["share"])
            for r in csv.DictReader(handle)
            if r["election_cycle_id"] == RACE
        }


def decompose(base: np.ndarray, variant: np.ndarray, truth: float) -> dict:
    """CRPS change split into a centre shift and a width/shape change.

    centre = CRPS(baseline moved to the variant's median) - CRPS(baseline);
    width  = CRPS(variant) - CRPS(baseline moved to the variant's median).
    """
    shift = np.median(variant) - np.median(base)
    c_base, c_var = ev.crps(base, truth), ev.crps(variant, truth)
    c_moved = ev.crps(base + shift, truth)
    return {
        "crps_base": c_base,
        "crps_variant": c_var,
        "change": c_var - c_base,
        "centre": c_moved - c_base,
        "width": c_var - c_moved,
        "median_shift": float(shift),
        "band_ratio": float(
            (np.quantile(variant, 0.9) - np.quantile(variant, 0.1))
            / (np.quantile(base, 0.9) - np.quantile(base, 0.1))
        ),
    }


def diagnose_2010(out: Path) -> dict:
    rows = load_suspensions()
    camp = historical_campaigns()[RACE]
    count = count_shares()
    report: dict = {"count_full_ballot": {k: count[k] for k in camp.names}, "horizons": {}}
    mu, sigma = keep_distribution(rows, exclude_cycles=(RACE,))
    for h in (20, 14):
        held = with_horizon(camp, h)
        cutoff = camp.election_date - timedelta(days=h)
        folded, names = fold_held_out_suspensions(held, rows, cutoff)
        ids = {p.reading_id for p in held.polls}
        pub = published(ids)
        polls = []
        for p in held.polls:
            fp = next((x for x in folded.polls if x.reading_id == p.reading_id), None)
            polls.append(
                {
                    "reading": p.reading_id,
                    "firm": p.firm,
                    "days_before": p.days_before_election,
                    "published": pub.get(p.reading_id, {}),
                    "baseline": {held.names[i]: s for i, s in zip(p.offered, p.shares)},
                    "uniform": (
                        {folded.names[i]: s for i, s in zip(fp.offered, fp.shares)} if fp else None
                    ),
                }
            )
        hr: dict = {"folded": list(names), "polls": polls, "seeds": {}}
        for s in SEEDS:
            name = f"holdout{h}-{RACE}-dirichlet"
            _bs, brec, bnamed, btail = load_run(RUNS / "baseline" / f"seed{s}" / name, RACE)
            _us, urec, unamed, utail = load_run(RUNS / "uniform" / f"seed{s}" / name, RACE)
            bn, un = brec["candidates"], urec["candidates"]
            lead, second = bn.index("Rob Ford"), bn.index("George Smitherman")
            ul, us_ = un.index("Rob Ford"), un.index("George Smitherman")
            truth_b = brec["holdout"]["leader_margin_actual"]
            truth_u = urec["holdout"]["leader_margin_actual"]
            # S2 exactly as suspension_compare.s2_fold builds it, from the S2 test's stored fold
            s2dir = S2_RUNS / f"seed{s}" / name
            _, _, s2base, s2tail = load_run(s2dir, RACE)
            found = (bn.index("Sarah Thomson"),)
            keep = np.exp(np.random.default_rng(s).normal(mu, sigma, size=(s2base.shape[0], 1)))
            keep = np.minimum(keep, 1.0)
            s2named = np.asarray(suspend(s2base, found, keep))
            freed = s2base[:, found[0]] * (1.0 - keep[:, 0])
            t = bn.index("Sarah Thomson")
            arms = {
                "baseline": (
                    bnamed[:, lead] - bnamed[:, second],
                    bnamed * (1 - btail[:, None]),
                    bn,
                ),
                "uniform": (unamed[:, ul] - unamed[:, us_], unamed * (1 - utail[:, None]), un),
                "s2": (s2named[:, lead] - s2named[:, second], s2named * (1 - s2tail[:, None]), bn),
                # counterfactual on the baseline draws: S2's freed share all to Smitherman
                "s2_to_smitherman": (
                    s2base[:, lead] - (s2base[:, second] + freed),
                    None,
                    bn,
                ),
                # counterfactual: Thomson's whole election-day share to Smitherman
                "all_to_smitherman": (
                    s2base[:, lead] - (s2base[:, second] + s2base[:, t]),
                    None,
                    bn,
                ),
            }
            sr = {}
            for arm, (margin, full, names_) in arms.items():
                truth = truth_u if arm == "uniform" else truth_b
                entry = {
                    "margin": q(margin),
                    "actual": truth,
                    "crps": ev.crps(margin, truth),
                    "covered": bool(np.quantile(margin, 0.1) <= truth <= np.quantile(margin, 0.9)),
                }
                if full is not None:
                    entry["full_ballot"] = {n: q(full[:, i]) for i, n in enumerate(names_)}
                if arm != "baseline":
                    entry["vs_baseline"] = decompose(arms["baseline"][0], margin, truth_b)
                sr[arm] = entry
            sr["thomson_named_share_baseline"] = q(bnamed[:, t])
            sr["thomson_full_ballot_baseline"] = q(bnamed[:, t] * (1 - btail))
            hr["seeds"][str(s)] = sr
        report["horizons"][str(h)] = hr
    (out / "diagnose_2010.json").write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    return report


def print_2010(r: dict) -> None:
    print("count (full ballot):", {k: round(100 * v, 2) for k, v in r["count_full_ballot"].items()})
    for h, hr in r["horizons"].items():
        print(f"=== {h} days; folded {hr['folded']}")
        for p in hr["polls"]:
            pub = {k: round(100 * v, 1) for k, v in p["published"].items()}
            base = {k.split()[-1]: round(100 * v, 1) for k, v in p["baseline"].items()}
            uni = (
                {k.split()[-1]: round(100 * v, 1) for k, v in p["uniform"].items()}
                if p["uniform"]
                else None
            )
            print(f"  {p['reading']} {p['firm']} {p['days_before']}d published {pub}")
            print(f"      baseline {base}\n      uniform  {uni}")
        arms = ("baseline", "uniform", "s2", "s2_to_smitherman", "all_to_smitherman")
        for arm in arms:
            vals = [hr["seeds"][s][arm] for s in hr["seeds"]]
            med = np.mean([v["margin"][1] for v in vals])
            lo = np.mean([v["margin"][0] for v in vals])
            hi = np.mean([v["margin"][2] for v in vals])
            crps = np.mean([v["crps"] for v in vals])
            line = (
                f"  {arm:18s} margin {100 * med:+5.1f} ({100 * lo:+5.1f}..{100 * hi:+5.1f}) "
                f"actual {100 * vals[0]['actual']:+5.2f} crps {100 * crps:5.2f}"
            )
            if arm != "baseline":
                dc = [v["vs_baseline"] for v in vals]
                line += (
                    f" | change {100 * np.mean([d['change'] for d in dc]):+5.2f} = centre "
                    f"{100 * np.mean([d['centre'] for d in dc]):+5.2f} + width "
                    f"{100 * np.mean([d['width'] for d in dc]):+5.2f} | median shift "
                    f"{100 * np.mean([d['median_shift'] for d in dc]):+5.2f} | band x"
                    f"{np.mean([d['band_ratio'] for d in dc]):.3f}"
                )
            print(line)
        for arm in ("baseline", "uniform", "s2"):
            vals = [hr["seeds"][s][arm]["full_ballot"] for s in hr["seeds"]]
            names = vals[0].keys()
            print(
                f"  full ballot {arm:9s}",
                {
                    n.split()[-1]: f"{100 * np.mean([v[n][1] for v in vals]):.1f}"
                    f" ({100 * np.mean([v[n][0] for v in vals]):.1f}-"
                    f"{100 * np.mean([v[n][2] for v in vals]):.1f})"
                    for n in names
                },
            )
        th = [hr["seeds"][s]["thomson_full_ballot_baseline"] for s in hr["seeds"]]
        print(f"  baseline Thomson full-ballot median {100 * np.mean([t[1] for t in th]):.2f}")


def coordinate_diagnostics(run: Path, top: int = 15) -> dict:
    """R-hat and ESS for every varying coordinate of a stored grouped-by-chain draw file."""
    from numpyro.diagnostics import effective_sample_size, split_gelman_rubin

    rows = []
    with np.load(run / "draws.npz") as d:
        for site in d.files:
            x = np.asarray(d[site], dtype=float)
            chains, draws = x.shape[:2]
            flat = x.reshape(chains, draws, -1)
            for j in range(flat.shape[2]):
                c = flat[:, :, j]
                if c.std() < 1e-9:
                    continue
                rows.append(
                    (
                        float(split_gelman_rubin(c)),
                        float(effective_sample_size(c)),
                        f"{site}[{j}]" if flat.shape[2] > 1 else site,
                    )
                )
    rows.sort(reverse=True)
    by_rhat = rows[:top]
    by_ess = sorted(rows, key=lambda r: r[1])[:top]
    return {
        "coordinates": len(rows),
        "over_1.01": sum(r[0] > 1.01 for r in rows),
        "ess_below_400": sum(r[1] < 400 for r in rows),
        "worst_r_hat": [{"coord": c, "r_hat": r, "ess": e} for r, e, c in by_rhat],
        "lowest_ess": [{"coord": c, "r_hat": r, "ess": e} for r, e, c in by_ess],
    }


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    what, out = argv[0], Path(argv[1])
    out.mkdir(parents=True, exist_ok=True)
    if what == "2010":
        print_2010(diagnose_2010(out))
    elif what == "2023":
        result = {}
        for run in argv[2:]:
            r = coordinate_diagnostics(Path(run))
            result[run] = r
            print(
                f"=== {run}\n  coords {r['coordinates']} | R-hat>1.01: {r['over_1.01']} | "
                f"ESS<400: {r['ess_below_400']}"
            )
            for x in r["worst_r_hat"][:10]:
                print(f"    R-hat {x['r_hat']:.4f} ESS {x['ess']:7.0f} {x['coord']}")
            print("  lowest ESS:", [(x["coord"], round(x["ess"])) for x in r["lowest_ess"][:6]])
        (out / "coordinates_2023.json").write_text(json.dumps(result, indent=1) + "\n")
    elif what == "pairs":
        print_pairs(compare_pairs(out))
    elif what == "divergences":
        result = {}
        for run in argv[2:]:
            r = divergences(Path(run))
            r["chain_means"] = chain_means(
                Path(run),
                (
                    "m_move",
                    "omega_move",
                    "phi_election",
                    "tau_reference",
                    "toronto_2023/election_mixing",
                    "toronto_2023/movement_z",
                ),
            )
            result[run] = r
            print(
                f"=== {Path(run).name}: divergences per chain {r['per_chain']}, mean accept "
                f"{[round(a, 3) for a in r['mean_accept_by_chain']]}"
            )
            for site, v in sorted(
                r["sites"].items(), key=lambda kv: -abs(kv[1]["median_rank_at_divergence"] - 0.5)
            ):
                print(
                    f"    {site:34s} median rank {v['median_rank_at_divergence']:.2f} | "
                    f"outer 10% {v['share_in_outer_10pct']:.2f}"
                )
            print(
                "    chain means:",
                {k: [round(x, 3) for x in v] for k, v in r["chain_means"].items()},
            )
        (out / "divergences_2023.json").write_text(json.dumps(result, indent=1) + "\n")


SHARED = (
    "m_move",
    "omega_move",
    "tau_firm",
    "kappa",
    "tau_reference",
    "mu_tail",
    "sigma_tail",
    "phi_election",
)
OWN = ("weekly_movement", "movement_z", "election_mixing", "election_precision")


def site_summary(draws, site: str) -> dict:
    from numpyro.diagnostics import effective_sample_size, split_gelman_rubin

    x = np.asarray(draws[site], dtype=float)
    chains, n = x.shape[:2]
    c = x.reshape(chains, n)
    return {
        "q": q(c.ravel()),
        "sd": float(c.std()),
        "r_hat": float(split_gelman_rubin(c)),
        "ess": float(effective_sample_size(c)),
    }


def compare_pairs(out: Path) -> dict:
    """Passing 2023 folds in both arms: shared, 2023 and 2026 parameters side by side; plus
    2026's own parameters over every held-out fit of both arms (identification check)."""
    passing = [(20, s) for s in (20260921, 20260922, 20260923)] + [
        (14, s) for s in (20260921, 20260924)
    ]
    sites = [*SHARED, *(f"toronto_2023/{x}" for x in OWN), *(f"toronto-2026/{x}" for x in OWN)]
    result: dict = {"pairs": {}, "identification": {}}
    for h, s in passing:
        row = {}
        for arm in ("baseline", "uniform"):
            run = RUNS / arm / f"seed{s}" / f"holdout{h}-toronto_2023-dirichlet"
            with np.load(run / "draws.npz") as d:
                row[arm] = {site: site_summary(d, site) for site in sites}
        result["pairs"][f"{h}d-{s}"] = row
    for arm in ("baseline", "uniform"):
        stats = defaultdict(list)
        for run in sorted((RUNS / arm).glob("seed*/holdout*-dirichlet")):
            with np.load(run / "draws.npz") as d:
                for x in OWN:
                    stats[x].append(site_summary(d, f"toronto-2026/{x}"))
                for site in ("toronto-2026/start", "toronto-2026/firm_z", "toronto-2026/steps"):
                    v = np.asarray(d[site], dtype=float)
                    stats[site + " sd (mean over coords)"].append(
                        {"sd": float(v.reshape(-1, *v.shape[2:]).std(axis=0).mean())}
                    )
        result["identification"][arm] = {
            k: {
                "median_sd": float(np.median([e["sd"] for e in v])),
                **(
                    {
                        "min_ess": float(min(e["ess"] for e in v)),
                        "max_r_hat": float(max(e["r_hat"] for e in v)),
                    }
                    if "ess" in v[0]
                    else {}
                ),
            }
            for k, v in stats.items()
        }
    (out / "pairs_2023.json").write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    return result


def print_pairs(r: dict) -> None:
    sites = list(next(iter(r["pairs"].values()))["baseline"])
    print("passing 2023 folds: posterior median baseline -> uniform (mean over 5 pairs); ESS")
    for site in sites:
        b = np.mean([p["baseline"][site]["q"][1] for p in r["pairs"].values()])
        u = np.mean([p["uniform"][site]["q"][1] for p in r["pairs"].values()])
        be = np.mean([p["baseline"][site]["ess"] for p in r["pairs"].values()])
        ue = np.mean([p["uniform"][site]["ess"] for p in r["pairs"].values()])
        print(
            f"  {site:32s} {b:9.4f} -> {u:9.4f} ({100 * (u / b - 1):+6.1f}%) | ESS {be:6.0f} -> {ue:6.0f}"
        )
    print(
        "2026's own parameters over all 65 fits per arm (posterior sd; prior sd: movement_z 1,"
        " election_mixing 0.632)"
    )
    for arm, v in r["identification"].items():
        for k, e in v.items():
            extra = (
                f" min ESS {e['min_ess']:.0f} max R-hat {e['max_r_hat']:.4f}"
                if "min_ess" in e
                else ""
            )
            print(f"  {arm:8s} {k:42s} median sd {e['median_sd']:.4f}{extra}")


def divergences(run: Path) -> dict:
    """Where divergent transitions sit: per-chain counts and the percentile rank of key
    parameters at divergent draws within the fit's own posterior."""
    with np.load(run / "sampler.npz") as s:
        div = np.asarray(s["diverging"], dtype=bool)
        accept = np.asarray(s["accept_prob"], dtype=float)
    out = {
        "per_chain": [int(c.sum()) for c in div],
        "mean_accept_by_chain": [float(a.mean()) for a in accept],
        "sites": {},
    }
    if not div.any():
        return out
    with np.load(run / "draws.npz") as d:
        for site in (
            *SHARED,
            *(f"toronto_2023/{x}" for x in OWN),
            *(f"toronto-2026/{x}" for x in OWN),
            "toronto_2003/election_mixing",
        ):
            x = np.asarray(d[site], dtype=float)
            flat, at = x.ravel(), x[div]
            ranks = [float((flat < v).mean()) for v in at]
            out["sites"][site] = {
                "median_rank_at_divergence": float(np.median(ranks)),
                "share_in_outer_10pct": float(np.mean([(r < 0.05) or (r > 0.95) for r in ranks])),
            }
    return out


def chain_means(run: Path, sites: tuple[str, ...]) -> dict:
    with np.load(run / "draws.npz") as d:
        return {s: [float(c.mean()) for c in np.asarray(d[s], dtype=float)] for s in sites}


if __name__ == "__main__":
    main()
