"""Seed-replicate rule for the Suspended Campaign signal (backend issue 45, 2026-10-06).

Run from the backend root:

    uv run python -m pytest docs/research/compact_mayoral/test_suspension_replicates.py -q
"""

import json

import pytest

from .suspension_replicates import HORIZONS, SEEDS, adopted, check_run_config, rules

RACES_20 = HORIZONS[20]
RACES_14 = HORIZONS[14]


def fold(crps=0.09, covered=True, divergences=0, r_hat=1.005):
    return {"crps": crps, "covered_80": covered, "divergences": divergences, "worst_r_hat": r_hat}


def arm(overrides=None):
    """One arm: {seed: {horizon: {race: fold}}}; overrides map (seed, horizon, race) -> fold."""
    out = {s: {h: {r: fold() for r in races} for h, races in HORIZONS.items()} for s in SEEDS}
    for (s, h, r), f in (overrides or {}).items():
        out[s][h][r] = f
    return out


def test_the_rule_covers_five_seeds_and_the_two_horizons():
    assert SEEDS == (20260921, 20260922, 20260923, 20260924, 20260925)
    assert sorted(HORIZONS) == [14, 20]
    assert "toronto_2022" not in RACES_20 and len(RACES_20) == 6
    assert len(RACES_14) == 7


def test_crps_is_judged_on_the_mean_over_seeds_not_seed_by_seed():
    base = arm()
    # One seed is 0.15 pts worse on every 14-day fold, the other four are equal: mean +0.03.
    one_bad_seed = arm({(SEEDS[0], 14, r): fold(crps=0.0915) for r in RACES_14})
    assert rules(one_bad_seed, base)["1_crps"]
    # Every seed is 0.11 pts worse at 20 days: fails.
    worse = arm({(s, 20, r): fold(crps=0.0911) for s in SEEDS for r in RACES_20})
    assert not rules(worse, base)["1_crps"]


def test_a_fold_counts_as_covered_in_three_of_five_seeds():
    base = arm()
    three = arm({(s, 20, "toronto_2023"): fold(covered=False) for s in SEEDS[:2]})
    assert rules(three, base)["coverage"][20] == 6
    two = arm({(s, 20, "toronto_2023"): fold(covered=False) for s in SEEDS[:3]})
    assert rules(two, base)["coverage"][20] == 5


def test_coverage_needs_every_fold_but_one():
    base = arm()
    one_miss = arm({(s, 20, "toronto_2003"): fold(covered=False) for s in SEEDS})
    assert rules(one_miss, base)["2_coverage"]
    two_misses = arm(
        {(s, 20, r): fold(covered=False) for s in SEEDS for r in ("toronto_2003", "toronto_2023")}
    )
    assert not rules(two_misses, base)["2_coverage"]
    two_misses_14 = arm(
        {(s, 14, r): fold(covered=False) for s in SEEDS for r in ("toronto_2003", "toronto_2023")}
    )
    assert not rules(two_misses_14, base)["2_coverage"]


def test_a_baseline_short_of_the_threshold_sets_the_bar_instead():
    misses = ("toronto_2003", "toronto_2006")
    base = arm({(s, 20, r): fold(covered=False) for s in SEEDS for r in misses})  # 4 of 6
    level = arm({(s, 20, r): fold(covered=False) for s in SEEDS for r in misses})
    assert rules(level, base)["2_coverage"]
    below = arm({(s, 20, r): fold(covered=False) for s in SEEDS for r in (*misses, "toronto_2023")})
    assert not rules(below, base)["2_coverage"]


def test_sampling_is_checked_on_every_fit_in_every_seed():
    base = arm()
    assert rules(arm({(SEEDS[3], 14, "toronto_2014"): fold(divergences=4)}), base)["3_sampler"]
    assert not rules(arm({(SEEDS[3], 14, "toronto_2014"): fold(divergences=5)}), base)["3_sampler"]
    assert not rules(arm({(SEEDS[4], 20, "toronto_2010"): fold(r_hat=1.02)}), base)["3_sampler"]


def test_outcome_order_is_s1_then_s2_then_neither():
    yes, no = {"pass": True}, {"pass": False}
    assert adopted(yes, yes) == "S1"
    assert adopted(yes, no) == "S1"
    assert adopted(no, yes) == "S2"
    assert adopted(no, no) == "neither"


def write_summary(path, **config):
    path.mkdir(parents=True)
    defaults = {
        "variant": "dirichlet",
        "hyperpriors": "population",
        "corpus": "all",
        "innovations": "gaussian",
        "target_accept": 0.95,
        "chains": 4,
        "warmup": 1000,
        "draws": 1000,
        "seed": 20260922,
        "suspension_signal": "none",
        "horizon_days": 20,
        "holdout": "toronto_2010",
    }
    (path / "summary.json").write_text(json.dumps({"config": {**defaults, **config}}))
    return path


def test_run_config_must_match_its_seed_arm_and_the_record_settings(tmp_path):
    ok = write_summary(tmp_path / "a" / "holdout20-toronto_2010-dirichlet")
    check_run_config(ok, seed=20260922, joint=False)
    joint = write_summary(
        tmp_path / "b" / "holdout20-toronto_2010-dirichlet_joint", suspension_signal="joint"
    )
    check_run_config(joint, seed=20260922, joint=True)
    with pytest.raises(AssertionError):
        check_run_config(ok, seed=20260923, joint=False)
    with pytest.raises(AssertionError):
        check_run_config(ok, seed=20260922, joint=True)
    loose = write_summary(tmp_path / "c" / "holdout20-toronto_2010-dirichlet", target_accept=0.9)
    with pytest.raises(AssertionError):
        check_run_config(loose, seed=20260922, joint=False)
