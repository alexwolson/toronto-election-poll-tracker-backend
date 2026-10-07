"""Fit the compact mayoral model and write draws plus a JSON summary.

Examples (run from the backend root)::

    uv run --no-project --with numpyro --with jax python -m docs.research.compact_mayoral.fit \
        --campaigns 2026 --hyperpriors docs/research/compact_mayoral/hyperpriors_heavy_2026-09-16.json \
        --variant isotropic --out docs/research/compact-mayoral-runs-2026-09-21/v1-2026-borrowed

    ... --campaigns all --hyperpriors population --variant leaders --holdout toronto_2023 --out ...

``--hyperpriors`` is either ``population`` (the heavy model's priors, for a joint
refit) or the path of a provenance JSON written by ``hyperpriors.py`` (borrowed
posteriors, for fitting 2026 alone). ``--holdout`` nulls one historical
campaign's result so its election day becomes a poll-only prediction.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
import sys
import time
from datetime import date, timedelta
from pathlib import Path

ELECTION_2026 = date(2026, 10, 26)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaigns", choices=("2026", "all", "historical"), default="2026")
    parser.add_argument(
        "--corpus",
        choices=("all", "from-2010"),
        default="all",
        help="historical campaigns to include: all seven, or 2010 onward (era rule, 2026-09-22 note)",
    )
    parser.add_argument(
        "--hyperpriors", required=True, help="'population' or a provenance JSON path"
    )
    parser.add_argument(
        "--variant",
        choices=("isotropic", "leaders", "support_scaled", "dirichlet"),
        default="isotropic",
    )
    parser.add_argument(
        "--innovations",
        choices=("gaussian", "student_t"),
        default="gaussian",
        help="random-walk step and firm-effect family (student_t = heavy model's t(5) mixtures)",
    )
    parser.add_argument(
        "--holdout", default=None, help="historical campaign key whose result to null"
    )
    parser.add_argument(
        "--horizon-days",
        type=int,
        default=None,
        help="held-out campaign: use only polls at least this many days before its election",
    )
    parser.add_argument("--include-pre-certification", action="store_true")
    parser.add_argument(
        "--exclude-campaigns",
        default="",
        help="comma-separated historical campaign keys to drop (width diagnostics, 2026-09-22)",
    )
    parser.add_argument(
        "--drop-candidates",
        default="",
        help='drop reference candidates: "toronto_2010:Rocco Rossi;Sarah Thomson[,key:Name;...]" (width diagnostics)',
    )
    parser.add_argument(
        "--late-movement",
        action="store_true",
        help="final-fortnight movement multiplier late_move (width defence, 2026-09-22)",
    )
    parser.add_argument(
        "--fixed-election-mixing",
        action="store_true",
        help="election-day precision = phi_election (no Gamma scale mixture)",
    )
    parser.add_argument(
        "--name-minor-candidates",
        action="store_true",
        help="model the certified minor candidates some 2026 polls report (McVie, Paloma Parker) "
        "as named candidates instead of leaving them in the residual pool",
    )
    parser.add_argument(
        "--suspension-signal",
        choices=("none", "joint"),
        default="none",
        help="S1 of backend issue 43: a shared kept fraction for Suspended Campaigns known at "
        "each campaign's cutoff (held-out campaign: election day minus the horizon)",
    )
    parser.add_argument(
        "--current-suspension",
        default="",
        help='with --suspension-signal joint: "Name:YYYY-MM-DD" for the 2026 campaign '
        "(not used in the held-out folds; issue 43 report)",
    )
    parser.add_argument(
        "--keep-prior-exclude-case",
        action="append",
        default=[],
        help="with --suspension-signal joint: leave this suspension-table case_id out of the "
        "kept-fraction prior (repeatable; leave-one-case-out target check, issue 45 follow-up)",
    )
    parser.add_argument(
        "--current-rule",
        choices=("production", "decided", "uniform"),
        default="production",
        help="2026 treatment of Alexander's Suspended Campaign (issue 48; uniform_rule.py)",
    )
    parser.add_argument(
        "--drop-current-poll",
        action="append",
        default=[],
        help="2026 polls.csv poll_id to leave out (repeatable; issue 48 arms without Forum Oct 6)",
    )
    parser.add_argument(
        "--fold-held-out-suspensions",
        action="store_true",
        help="fold the held-out campaign's candidates suspended on or before the cutoff into "
        "the pool, in its readings and its target (issue 48 uniform arm)",
    )
    parser.add_argument(
        "--reactive",
        choices=("none", "c2", "c3"),
        default="none",
        help="issue 51: model the exit inside the fit for the forecast-target campaigns "
        "(held-out and 2026); c3 adds a one-time shift at the exit (reactive.py)",
    )
    parser.add_argument(
        "--save-sampler-stats",
        action="store_true",
        help="also write sampler.npz (diverging, accept_prob, num_steps by chain; issue 50)",
    )
    parser.add_argument("--min-offered", type=int, default=2)
    parser.add_argument(
        "--denominator-rank", choices=("decided_first", "all_first"), default="decided_first"
    )
    parser.add_argument("--warmup", type=int, default=1000)
    parser.add_argument("--draws", type=int, default=1000)
    parser.add_argument("--chains", type=int, default=4)
    parser.add_argument("--seed", type=int, default=20260921)
    parser.add_argument("--target-accept", type=float, default=0.9)
    parser.add_argument("--out", type=Path, required=True)
    return parser.parse_args(argv)


def quantiles(x, probs=(0.05, 0.1, 0.5, 0.9, 0.95)):
    import numpy as np

    x = np.asarray(x, dtype=float)
    q = np.quantile(x, probs)
    return {
        "mean": float(x.mean()),
        "sd": float(x.std()),
        **{f"q{round(p * 100):02d}": float(v) for p, v in zip(probs, q)},
    }


def reactive_summary(reactive_exits, campaigns, flat) -> dict:
    """Exit specs and allocation / keep / shift posteriors per target campaign (issue 51)."""
    out = {}
    names = {c.key: c.names for c in campaigns}
    for key, exits in reactive_exits.items():
        departed, rows = [], []
        for j, e in enumerate(exits):
            remaining = [
                n for i, n in enumerate(names[key]) if i != e.candidate and i not in departed
            ]
            row = {
                "name": e.name,
                "day": e.day,
                "keep_prior_log_normal": [e.keep_mu, e.keep_sigma],
                "remaining": remaining,
                "keep_fraction": quantiles(flat[f"{key}/keep_fraction_{j}"]),
                "allocation": {
                    n: quantiles(flat[f"{key}/allocation_{j}"][:, i])
                    for i, n in enumerate(remaining)
                },
            }
            if f"{key}/shift_{j}" in flat:
                row["shift_sigma"] = quantiles(flat[f"{key}/shift_sigma_{j}"])
                row["shift"] = {
                    n: quantiles(flat[f"{key}/shift_{j}"][:, i]) for i, n in enumerate(remaining)
                }
            rows.append(row)
            departed.append(e.candidate)
        out[key] = rows
    return out


def main(argv=None):
    args = parse_args(argv)
    # Parallel chains on CPU need the host device count set before JAX initializes.
    os.environ.setdefault("XLA_FLAGS", f"--xla_force_host_platform_device_count={args.chains}")
    import jax
    import numpy as np
    import numpyro
    from numpyro.diagnostics import summary as numpyro_summary
    from numpyro.infer import MCMC, NUTS

    jax.config.update("jax_enable_x64", True)
    numpyro.set_host_device_count(args.chains)

    from .hyperpriors import load_hyperpriors, population_hyperpriors
    from .model import build_model
    from .reactive import ALLOCATION_CONCENTRATION, SHIFT_SCALE
    from .readings import (
        EXTRA_2026,
        current_campaign,
        historical_campaigns,
        with_horizon,
        without_candidates,
    )
    from .suspensions import (
        check_no_post_suspension_offer,
        current_suspension_row,
        keep_distribution,
        known_suspensions,
        load_suspensions,
    )

    started = time.monotonic()
    campaigns = []
    if args.campaigns in {"all", "historical"}:
        campaigns.extend(
            c
            for key, c in historical_campaigns(
                min_offered=args.min_offered, denominator_rank=args.denominator_rank
            ).items()
            if (args.corpus == "all" or int(key.rsplit("_", 1)[1]) >= 2010)
            and key not in set(filter(None, args.exclude_campaigns.split(",")))
        )
    if args.campaigns in {"all", "2026"}:
        if args.reactive != "none" and args.current_rule == "uniform":
            sys.exit("--reactive keeps Alexander named; it cannot combine with the uniform rule")
        if (
            args.current_rule == "production"
            and not args.drop_current_poll
            and args.reactive == "none"
        ):
            campaigns.append(
                current_campaign(
                    election_date=ELECTION_2026,
                    require_full_field=not args.include_pre_certification,
                    extra_named=EXTRA_2026 if args.name_minor_candidates else (),
                )
            )
        else:
            from .uniform_rule import current_campaign_under

            campaigns.append(
                current_campaign_under(
                    "decided" if args.reactive != "none" else args.current_rule,
                    election_date=ELECTION_2026,
                    drop_polls=tuple(args.drop_current_poll),
                )
            )
    for spec in filter(None, args.drop_candidates.split(",")):
        key, _, names = spec.partition(":")
        campaigns = [
            without_candidates(c, tuple(n.strip().replace("_", " ") for n in names.split(";")))
            if c.key == key
            else c
            for c in campaigns
        ]
    actual, baseline_target = {}, {}
    if args.holdout:
        keys = [c.key for c in campaigns]
        if args.holdout not in keys:
            sys.exit(f"--holdout {args.holdout!r} is not among {keys}")
        held = campaigns[keys.index(args.holdout)]
        if args.horizon_days is not None:
            held = with_horizon(held, args.horizon_days)
        if args.fold_held_out_suspensions:
            from .uniform_rule import fold_held_out_suspensions

            cutoff = held.election_date - timedelta(days=args.horizon_days or 0)
            unfolded = dict(zip(held.names, held.outcome_shares))
            held, folded_names = fold_held_out_suspensions(held, load_suspensions(), cutoff)
            baseline_target[held.key] = {"folded": list(folded_names), "named_shares": unfolded}
        actual[held.key] = {
            "names": list(held.names),
            "named_shares": list(held.outcome_shares),
            "tail": held.outcome_tail,
        }
        campaigns[keys.index(args.holdout)] = dataclasses.replace(
            held, outcome_shares=None, outcome_tail=None
        )
    reactive_exits = {}
    if args.reactive != "none":
        from .reactive import set_aside_after_exits, target_exits
        from .readings import CURRENT_KEY

        rows = load_suspensions()
        current_rows = [*rows, current_suspension_row("Chris Alexander:2026-10-06")]
        assembled = []
        for c in campaigns:
            exits = ()
            if c.key == CURRENT_KEY:
                exits = target_exits(c, current_rows, ELECTION_2026, keep_distribution(rows))
            elif c.key == args.holdout:
                cutoff = c.election_date - timedelta(days=args.horizon_days or 0)
                prior = keep_distribution(rows, exclude_cycles=(c.key,))
                exits = target_exits(c, rows, cutoff, prior)
            if exits:
                c = set_aside_after_exits(c, exits)
                reactive_exits[c.key] = exits
            assembled.append(c)
        campaigns = assembled
        print(
            "reactive:",
            args.reactive,
            {
                k: [(e.name, e.day, round(e.keep_mu, 4), round(e.keep_sigma, 4)) for e in v]
                for k, v in reactive_exits.items()
            },
            flush=True,
        )
    campaigns = tuple(campaigns)
    suspensions, keep_prior = {}, None
    if args.suspension_signal == "joint":
        # The table holds the recorded historical cases; 2026 gets no signal inside these
        # fits (its forecast there is sealed and unused by the held-out decision).
        rows = load_suspensions()
        keep_prior = keep_distribution(
            rows, exclude_cities=("Toronto",), exclude_cases=tuple(args.keep_prior_exclude_case)
        )
        if args.current_suspension:
            rows = [*rows, current_suspension_row(args.current_suspension)]
        for c in campaigns:
            check_no_post_suspension_offer(c, rows)
            cutoff = c.election_date
            if c.key == args.holdout and args.horizon_days is not None:
                cutoff = c.election_date - timedelta(days=args.horizon_days)
            found = known_suspensions(c, rows, cutoff)
            if found:
                suspensions[c.key] = found
        print(
            "suspension signal:",
            {
                k: [c.names[i] for c in campaigns if c.key == k for i in v]
                for k, v in suspensions.items()
            },
            f"keep prior log-normal({keep_prior[0]:.4f}, {keep_prior[1]:.4f})",
            flush=True,
        )
    hyperpriors = (
        population_hyperpriors()
        if args.hyperpriors == "population"
        else load_hyperpriors(args.hyperpriors)
    )
    model = build_model(
        campaigns,
        hyperpriors,
        variant=args.variant,
        innovations=args.innovations,
        election_mixing=not args.fixed_election_mixing,
        late_movement=args.late_movement,
        suspensions=suspensions,
        keep_prior=keep_prior,
        reactive=reactive_exits,
        allocation_concentration=ALLOCATION_CONCENTRATION,
        shift_scale=SHIFT_SCALE if args.reactive == "c3" else None,
    )

    args.out.mkdir(parents=True, exist_ok=False)
    kernel = NUTS(model, target_accept_prob=args.target_accept, dense_mass=False)
    mcmc = MCMC(
        kernel,
        num_warmup=args.warmup,
        num_samples=args.draws,
        num_chains=args.chains,
        chain_method="parallel",
        progress_bar=False,
    )
    print(
        f"fitting {len(campaigns)} campaign(s) [{', '.join(c.key for c in campaigns)}] "
        f"variant={args.variant} innovations={args.innovations} hyperpriors={hyperpriors['mode']} "
        f"{args.chains}x({args.warmup}+{args.draws})",
        flush=True,
    )
    mcmc.run(jax.random.key(args.seed), extra_fields=("diverging", "num_steps", "accept_prob"))
    elapsed = time.monotonic() - started

    grouped = mcmc.get_samples(group_by_chain=True)
    flat = {k: np.asarray(v).reshape((-1,) + np.asarray(v).shape[2:]) for k, v in grouped.items()}
    extras = mcmc.get_extra_fields(group_by_chain=True)
    np.savez_compressed(args.out / "draws.npz", **{k: np.asarray(v) for k, v in grouped.items()})
    if args.save_sampler_stats:
        np.savez_compressed(
            args.out / "sampler.npz", **{k: np.asarray(v) for k, v in extras.items()}
        )

    # Diagnostics over every sampled and deterministic coordinate.
    # Constant coordinates (deterministic functions of observed results) carry no
    # mixing information; their R-hat is floating-point noise and is excluded.
    diagnostics = numpyro_summary(grouped, prob=0.9, group_by_chain=True)
    worst, over_threshold = [], 0
    for site, stats in diagnostics.items():
        r_hat = np.asarray(stats["r_hat"], dtype=float).ravel()
        ess = np.asarray(stats["n_eff"], dtype=float).ravel()
        varying = flat[site].reshape(flat[site].shape[0], -1).std(axis=0) > 1e-9
        keep = np.isfinite(r_hat) & varying
        if keep.any():
            worst.append((float(r_hat[keep].max()), float(ess[keep].min()), site))
            over_threshold += int((r_hat[keep] > 1.01).sum())
    worst.sort(reverse=True)
    divergences = int(np.asarray(extras["diverging"]).sum())
    steps = np.asarray(extras["num_steps"], dtype=float)

    def campaign_summary(c):
        prefix = c.key + "/"
        record = {
            "candidates": list(c.names),
            "polls": len(c.polls),
            "leaders": [c.names[i] for i in c.leaders],
            "latest_poll_days_before_election": min(p.days_before_election for p in c.polls),
            "weekly_movement": quantiles(flat[prefix + "weekly_movement"]),
        }
        if c.outcome_shares is None:
            current = flat[prefix + "current"]
            named = flat[prefix + "named_result"]
            full = flat[prefix + "full_ballot"]
            lead, second = c.leaders
            margin_now = current[:, lead] - current[:, second]
            margin_day = named[:, lead] - named[:, second]
            winners = named.argmax(axis=1)
            record.update(
                {
                    "current_support": {n: quantiles(current[:, i]) for i, n in enumerate(c.names)},
                    "election_named_shares": {
                        n: quantiles(named[:, i]) for i, n in enumerate(c.names)
                    },
                    "election_full_ballot": {
                        n: quantiles(full[:, i]) for i, n in enumerate(c.names)
                    },
                    "residual_pool": quantiles(flat[prefix + "tail"]),
                    "leader_margin_now": {
                        **quantiles(margin_now),
                        "p_leader_ahead": float((margin_now > 0).mean()),
                    },
                    "leader_margin_election": {
                        **quantiles(margin_day),
                        "p_leader_ahead": float((margin_day > 0).mean()),
                    },
                    "win_probability": {
                        n: float((winners == i).mean()) for i, n in enumerate(c.names)
                    },
                }
            )
            if c.key in actual:
                truth = np.asarray(actual[c.key]["named_shares"])
                record["holdout"] = {
                    "actual_named_shares": actual[c.key]["named_shares"],
                    "actual_tail": actual[c.key]["tail"],
                    "pit": [float((named[:, i] <= truth[i]).mean()) for i in range(len(truth))],
                    "covered_80": [
                        bool(
                            np.quantile(named[:, i], 0.1)
                            <= truth[i]
                            <= np.quantile(named[:, i], 0.9)
                        )
                        for i in range(len(truth))
                    ],
                    "horizon_days": args.horizon_days,
                    "polls_used": len(c.polls),
                    "leader_margin_actual": float(truth[lead] - truth[second]),
                    "leader_margin_pit": float((margin_day <= truth[lead] - truth[second]).mean()),
                    "leader_margin_covered_80": bool(
                        np.quantile(margin_day, 0.1)
                        <= truth[lead] - truth[second]
                        <= np.quantile(margin_day, 0.9)
                    ),
                    "actual_winner": c.names[int(truth.argmax())],
                    "p_actual_winner": float((winners == int(truth.argmax())).mean()),
                }
                if c.key in baseline_target:
                    unfolded = baseline_target[c.key]["named_shares"]
                    base_margin = unfolded[c.names[lead]] - unfolded[c.names[second]]
                    record["holdout"]["folded_suspensions"] = baseline_target[c.key]["folded"]
                    record["holdout"]["baseline_target_margin"] = float(base_margin)
        return record

    summary = {
        "config": {**{k: (str(v) if isinstance(v, Path) else v) for k, v in vars(args).items()}},
        "hyperpriors": {"mode": hyperpriors["mode"], "source": hyperpriors.get("source")},
        "suspension_signal": {
            "applied": {
                k: [c.names[i] for c in campaigns if c.key == k for i in v]
                for k, v in suspensions.items()
            },
            "keep_prior_log_normal": keep_prior,
        },
        "elapsed_seconds": round(elapsed, 1),
        "draws_per_chain": args.draws,
        "chains": args.chains,
        "diagnostics": {
            "divergences": divergences,
            "mean_leapfrog_steps": float(steps.mean()),
            "max_leapfrog_steps": int(steps.max()),
            "worst_r_hat": worst[0][0] if worst else None,
            "min_ess": min(w[1] for w in worst) if worst else None,
            "worst_sites": [{"site": site, "r_hat": r, "min_ess": e} for r, e, site in worst[:8]],
            "coordinates_r_hat_over_1.01": over_threshold,
        },
        "shared_scales": {
            name: quantiles(flat[name])
            for name in (
                *(("late_move",) if args.late_movement else ()),
                "m_move",
                "omega_move",
                "tau_firm",
                "tau_election",
                "tau_lead",
                "tau_rest",
                "gamma_election",
                "phi_election",
                "kappa",
                "tau_reference",
                "mu_tail",
                "sigma_tail",
                "keep_fraction",
            )
            if name in flat
        },
        "campaigns": {c.key: campaign_summary(c) for c in campaigns},
        "reactive": reactive_summary(reactive_exits, campaigns, flat),
    }
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    d = summary["diagnostics"]
    print(
        f"done in {elapsed:.0f}s | divergences {d['divergences']} | worst R-hat {d['worst_r_hat']:.4f} "
        f"| min ESS {d['min_ess']:.0f} | mean steps {d['mean_leapfrog_steps']:.0f}",
        flush=True,
    )
    for key, record in summary["campaigns"].items():
        if "win_probability" in record:
            print(
                key,
                "win",
                {k: round(v, 3) for k, v in record["win_probability"].items()},
                flush=True,
            )
    return summary


if __name__ == "__main__":
    main()
