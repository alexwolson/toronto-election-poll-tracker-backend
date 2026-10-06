"""How the production compact model responds to synthetic post-exit polls.

Isolated scenario fits on the ``backend-2026-10-06.1`` inputs; never writes real
inputs, feeds or releases. Each scenario appends hypothetical polls to the
production 2026 campaign and refits with the production settings, seed and
qualification gate (``_qualified_fit``: one retry at target acceptance 0.99).

Usage, from the Backend root:
    uv run python docs/research/alexander-post-exit-polls-2026-10-06/run.py \
        --pins <dir with polling/ and results/> [--only LABEL] [--workers N] [--force]
"""

import os

os.environ.setdefault("XLA_FLAGS", "--xla_force_host_platform_device_count=4")
import argparse
import csv
import hashlib
import json
import multiprocessing
import shutil
import sys
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from backend.model.compact_mayoral.hyperpriors import population_hyperpriors
from backend.model.compact_mayoral.qualification import qualify
from backend.model.compact_mayoral.readings import (
    Poll,
    current_campaign,
    historical_campaigns,
)
from backend.model.compact_mayoral.sampling import PRODUCTION, FitSettings
from backend.model.compact_mayoral_feed import _qualified_fit

OUT = Path(__file__).parent
ELECTION = date(2026, 10, 26)
RELEASE = "backend-2026-10-06.1"
POLLING_RELEASE = "polling-2026-10-06.2"
RESULTS_RELEASE = "results-2026-09-30.2"
# Manifest hashes recorded in the backend-2026-10-06.1 release manifest.
POLLING_MANIFEST_SHA = "7759f60284037ca81526c6c792728eeb5d3509ee24c8f94aea14bd31d2f7f5c0"
RESULTS_MANIFEST_SHA = "e03cea31ef178cbd0758e967d5adcb184d00279bf309f6542d6bb7e3867fdbfe"
# Post-exit fieldwork end dates and firms, in order: poll k of a sequence uses
# the first k entries. Established firms with repeated 2026 polls.
SCHEDULE = (
    (date(2026, 10, 9), "Liaison Strategies"),
    (date(2026, 10, 12), "Mainstreet Research"),
    (date(2026, 10, 15), "Forum Research"),
)
N_EFF = 800.0  # matches the Oct 2 scenarios; the 14 real polls' median is 780


def scenarios(average: np.ndarray):
    """(label, kind, alexander share or None, poll count)."""
    yield "baseline", "none", None, 0
    for k in (1, 2, 3):
        yield f"head-to-head-n{k}", "head_to_head", None, k
    for k in (1, 2, 3):
        yield f"control-n{k}", "full_field", float(average[2]), k
    for share in (0.01, 0.03, 0.06):
        for k in (1, 2, 3):
            yield f"alexander-{round(100 * share)}pct-n{k}", "full_field", share, k


def synthetic_polls(kind: str, alexander: float | None, count: int, ratio: float):
    polls = []
    for i, (fieldwork_end, firm) in enumerate(SCHEDULE[:count]):
        days = (ELECTION - fieldwork_end).days
        if kind == "head_to_head":
            offered, shares = (0, 1), (ratio, 1 - ratio)
        else:
            offered = (0, 1, 2)
            shares = ((1 - alexander) * ratio, (1 - alexander) * (1 - ratio), alexander)
        polls.append(Poll(f"post-exit-{i}", f"post-exit-{i}", firm, days, N_EFF, offered, shares))
    return tuple(polls)


def head_to_head_dropped_check(pins: Path, baseline) -> dict:
    """Inject a two-name reading into a copy of the Polling bundle and run the real
    reading selection: the production rule must drop it; two-of-three keeps it."""
    with tempfile.TemporaryDirectory() as tmp:
        bundle = Path(tmp) / "polling"
        shutil.copytree(pins / "polling", bundle)
        sample_id, reading_id = "synthetic-2026-10-09", "synthetic_h2h_mayor"

        def append(name: str, row: dict):
            path = bundle / name
            with path.open(encoding="utf-8", newline="") as handle:
                header = next(csv.reader(handle))
            with path.open("a", encoding="utf-8", newline="") as handle:
                csv.DictWriter(handle, header).writerow({k: row.get(k, "") for k in header})

        append(
            "poll_samples.csv",
            {
                "poll_sample_id": sample_id,
                "election_cycle_id": "toronto-2026",
                "geography_type": "citywide",
                "extraction_status": "extracted",
                "pollster": "Liaison Strategies",
                "fieldwork_start": "2026-10-08",
                "fieldwork_end": "2026-10-09",
                "publication_date": "2026-10-10",
                "recruited_sample_size": "1000",
            },
        )
        append(
            "poll_readings.csv",
            {
                "poll_reading_id": reading_id,
                "poll_sample_id": sample_id,
                "contest_type": "mayoral",
                "reading_purpose": "general_vote_intention",
                "denominator_semantics": "decided_plus_leaners",
                "reported_base": "800",
            },
        )
        for slug, share in (("chow", "0.56"), ("bradford", "0.44")):
            append(
                "poll_responses.csv",
                {
                    "poll_reading_id": reading_id,
                    "response_kind": "candidate",
                    "source_candidate_id": slug,
                    "share": share,
                },
            )
        candidates = pins / "results/mayoral_candidates.json"
        main = current_campaign(bundle, candidates, election_date=ELECTION)
        widened = current_campaign(
            bundle, candidates, election_date=ELECTION, require_full_field=False
        )
    kept = [p for p in widened.polls if p.group == sample_id]
    return {
        "production_rule_drops_two_name_poll": main.polls == baseline.polls,
        "two_of_three_rule_keeps_it": bool(kept),
        "kept_as": [{"offered": list(p.offered), "shares": list(p.shares)} for p in kept],
    }


def summarize(draws: dict, settings: FitSettings) -> dict:
    prefix = "toronto-2026/"
    named = np.asarray(draws[prefix + "named_result"])
    full = np.asarray(draws[prefix + "full_ballot"])
    current = np.asarray(draws[prefix + "current"])
    winners = named.argmax(axis=1)
    margin = 100 * (full[:, 0] - full[:, 1])
    scale = 1.0 - np.asarray(draws[prefix + "tail"]).ravel()

    def gap(shares):
        return 100 * (shares[:, 0] - shares[:, 1]) * scale

    def band(x):
        return {
            "median": float(np.median(x)),
            "lower": float(np.quantile(x, 0.1)),
            "upper": float(np.quantile(x, 0.9)),
        }

    bradford = (winners == 1).astype(float).reshape(settings.chains, -1).mean(axis=1)
    return {
        "win_probability": {
            name: float((winners == i).mean())
            for i, name in enumerate(("chow", "bradford", "alexander"))
        },
        "bradford_win_chain_se": float(bradford.std(ddof=1) / np.sqrt(settings.chains)),
        "chow_minus_bradford_points": band(margin),
        "election_day_full_ballot": {
            name: band(full[:, i]) for i, name in enumerate(("chow", "bradford", "alexander"))
        },
        "alexander_current_named_support": band(current[:, 2]),
        "chow_share_of_two_current": band(current[:, 0] / (current[:, 0] + current[:, 1])),
        # Mechanism: the 2026 campaign's movement scale (log-odds per week) and the
        # Chow - Bradford gap in full-ballot points today, at election-day support,
        # and in the result (the feed's uncertainty decomposition, ADR 0056).
        "weekly_movement": band(np.asarray(draws[prefix + "weekly_movement"]).ravel()),
        "gap_by_stage": {
            stage: band(gap(np.asarray(draws[prefix + stage])))
            for stage in ("current", "election_support", "named_result")
        },
    }


def run_one(job):
    """Fit one scenario; return only what is recorded (draw dicts stay in the worker)."""
    label, campaigns, settings, gated = job
    started = time.monotonic()
    gate = qualify if gated else None
    result = _qualified_fit(campaigns, population_hyperpriors(), settings, gate)
    keep = ("named_result", "full_ballot") if label == "baseline" else ()
    return {
        "label": label,
        "summary": summarize(result.draws, result.settings),
        "retried": result.settings.target_accept != settings.target_accept,
        "diagnostics": result.diagnostics.as_dict(),
        "settings": result.settings.__dict__,
        "seconds": round(time.monotonic() - started, 1),
        "draws": {k: np.asarray(result.draws["toronto-2026/" + k]) for k in keep},
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pins", type=Path, required=True)
    parser.add_argument("--only", action="append")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--draws", type=int, default=PRODUCTION.draws)
    parser.add_argument("--warmup", type=int, default=PRODUCTION.warmup)
    parser.add_argument("--out", type=Path, default=OUT / "scenarios")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--smoke", action="store_true", help="skip the gate (plumbing check)")
    opts = parser.parse_args()
    for sub, expected in (("polling", POLLING_MANIFEST_SHA), ("results", RESULTS_MANIFEST_SHA)):
        actual = hashlib.sha256((opts.pins / sub / "release_manifest.json").read_bytes())
        if actual.hexdigest() != expected:
            raise ValueError(f"{sub} bundle is not the {RELEASE} pin")
    base = current_campaign(
        opts.pins / "polling", opts.pins / "results/mayoral_candidates.json", election_date=ELECTION
    )
    assert base.names == ("Olivia Chow", "Brad Bradford", "Chris Alexander")
    assert len(base.polls) == 14
    average = np.mean([p.shares for p in base.polls], axis=0)
    ratio = float(average[0] / (average[0] + average[1]))
    history = tuple(historical_campaigns().values())
    settings = FitSettings(warmup=opts.warmup, draws=opts.draws, seed=PRODUCTION.seed)
    opts.out.mkdir(parents=True, exist_ok=True)

    inputs = {
        "release": RELEASE,
        "polling_release": POLLING_RELEASE,
        "results_release": RESULTS_RELEASE,
        "model_package_sha256": {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted((ROOT / "backend/model/compact_mayoral").glob("*.py"))
        },
        "simple_average_named_three": average.tolist(),
        "chow_share_of_two": ratio,
        "schedule": [{"fieldwork_end": d.isoformat(), "firm": f} for d, f in SCHEDULE],
        "n_eff": N_EFF,
        "head_to_head_check": head_to_head_dropped_check(opts.pins, base),
    }
    (opts.out / "inputs.json").write_text(json.dumps(inputs, indent=2) + "\n")
    print("head-to-head check", inputs["head_to_head_check"], flush=True)

    jobs = []
    for label, kind, alexander, count in scenarios(average):
        if opts.only and label not in opts.only:
            continue
        target = opts.out / f"{label}.json"
        if target.exists() and not opts.force:
            continue
        added = synthetic_polls(kind, alexander, count, ratio)
        polls = tuple(sorted((*base.polls, *added), key=lambda p: -p.days_before_election))
        campaign = replace(base, polls=polls)
        meta = {
            "label": label,
            "kind": kind,
            "alexander_poll_share": alexander,
            "poll_count": count,
            "polls": [
                {
                    "firm": p.firm,
                    "fieldwork_end": (
                        ELECTION - timedelta(days=p.days_before_election)
                    ).isoformat(),
                    "offered": list(p.offered),
                    "shares": list(p.shares),
                }
                for p in added
            ],
        }
        jobs.append((meta, (label, (*history, campaign), settings, not opts.smoke)))

    def record(meta, done):
        row = {
            **meta,
            **done["summary"],
            "qualified": not opts.smoke,
            "retried": done["retried"],
            "diagnostics": done["diagnostics"],
            "settings": done["settings"],
            "seconds": done["seconds"],
        }
        (opts.out / f"{meta['label']}.json").write_text(json.dumps(row, indent=2) + "\n")
        win = done["summary"]["win_probability"]
        print(
            f"DONE {meta['label']}: Chow {100 * win['chow']:.2f} Bradford "
            f"{100 * win['bradford']:.2f} ({done['seconds']:.0f}s"
            + (", retried" if done["retried"] else "")
            + ")",
            flush=True,
        )
        if done["draws"]:
            np.savez_compressed(opts.out / "baseline-draws.npz", **done["draws"])

    metas = {job[0]: meta for meta, job in jobs}
    if opts.workers <= 1:
        for meta, job in jobs:
            print("START", meta["label"], flush=True)
            record(meta, run_one(job))
    else:
        context = multiprocessing.get_context("spawn")
        with ProcessPoolExecutor(max_workers=opts.workers, mp_context=context) as pool:
            futures = [pool.submit(run_one, job) for _, job in jobs]
            for future in as_completed(futures):
                done = future.result()
                record(metas[done["label"]], done)


if __name__ == "__main__":
    main()
