"""Rule logic for the uniform-rule test (backend issue 48).

Run from the backend root:

    uv run python -m pytest docs/research/compact_mayoral/test_uniform_rule.py -q
"""

import csv
from dataclasses import replace
from datetime import date

import numpy as np

from .readings import Paths, historical_campaigns, with_horizon
from .suspensions import load_suspensions
from .uniform_rule import admitted, apply_s2, current_campaign_under, fold_held_out_suspensions

E = date(2026, 10, 26)
HEADER = ["poll_id", "firm", "date_conducted", "sample_size", "alexander", "bradford", "chow"]
ROWS = [
    ["pre-ab", "F", "2026-07-26", "1000", "", "0.40", "0.45"],  # pre-Alexander: Chow-Bradford only
    ["three", "F", "2026-09-23", "1000", "0.06", "0.35", "0.46"],
    ["post-named", "M", "2026-10-07", "1000", "0.01", "0.44", "0.47"],  # post-exit, names him
    ["post", "F", "2026-10-06", "1600", "", "0.42", "0.46"],
]


def _paths(tmp_path):
    path = tmp_path / "polls.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(HEADER)
        writer.writerows(ROWS)
    return replace(Paths(), current_polls=path, current_candidates=tmp_path / "missing.json")


def test_admitted_is_production_set_plus_post_suspension_chow_bradford():
    rows = [dict(zip(HEADER, r)) for r in ROWS]
    assert [admitted(r) for r in rows] == [False, True, True, True]


def test_production_drops_the_post_exit_poll_that_omits_him(tmp_path):
    c = current_campaign_under("production", _paths(tmp_path), election_date=E)
    assert sorted(p.reading_id for p in c.polls) == ["post-named", "three"]


def test_decided_sets_aside_his_post_exit_share(tmp_path):
    c = current_campaign_under("decided", _paths(tmp_path), election_date=E)
    polls = {p.reading_id: p for p in c.polls}
    assert set(polls) == {"three", "post-named", "post"}
    assert polls["three"].offered == (0, 1, 2)
    assert polls["post-named"].offered == (0, 1)  # Alexander's 1% set aside
    assert np.isclose(polls["post-named"].n_eff, 1000 * 0.91)
    assert np.isclose(polls["post"].shares[0], 0.46 / 0.88)


def test_uniform_reads_every_poll_as_chow_bradford_and_keeps_the_same_samples(tmp_path):
    c = current_campaign_under("uniform", _paths(tmp_path), election_date=E)
    assert c.names == ("Olivia Chow", "Brad Bradford")
    polls = {p.reading_id: p for p in c.polls}
    assert set(polls) == {"three", "post-named", "post"}  # pre-Alexander stays out
    assert polls["three"].offered == (0, 1)
    assert np.isclose(polls["three"].shares[0], 0.46 / 0.81)
    assert np.isclose(polls["three"].n_eff, 1000 * 0.81)


def test_drop_polls_removes_a_named_sample(tmp_path):
    c = current_campaign_under("uniform", _paths(tmp_path), election_date=E, drop_polls=("post",))
    assert "post" not in {p.reading_id for p in c.polls}


def test_held_out_fold_in_follows_the_cutoff():
    rows = load_suspensions()
    camp = historical_campaigns()["toronto_2010"]
    for horizon in (20, 14):
        held = with_horizon(camp, horizon)
        cutoff = camp.election_date.fromordinal(camp.election_date.toordinal() - horizon)
        folded, names = fold_held_out_suspensions(held, rows, cutoff)
        assert names == ("Sarah Thomson",)  # Rossi (Oct 13) is after both cutoffs
        assert "Sarah Thomson" not in folded.names and "Rocco Rossi" in folded.names
        assert folded.outcome_tail > held.outcome_tail
    camp23 = historical_campaigns()["toronto_2023"]
    held = with_horizon(camp23, 14)
    _, names = fold_held_out_suspensions(held, rows, date(2023, 6, 12))
    assert names == ()


def test_apply_s2_keeps_the_others_ratio_and_the_pool():
    named = np.array([[0.55, 0.38, 0.07], [0.5, 0.4, 0.1]])
    tail = np.array([0.05, 0.06])
    out, full = apply_s2(named, tail, 2, -1.8382, 0.7132, seed=1)
    assert np.allclose(out.sum(axis=1), 1.0)
    assert np.allclose(out[:, 0] / out[:, 1], named[:, 0] / named[:, 1])
    assert np.all(out[:, 2] <= named[:, 2])
    assert np.allclose(full.sum(axis=1), 1.0 - tail)
