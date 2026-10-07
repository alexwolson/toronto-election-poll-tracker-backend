"""The production-path holdout driver: one historical campaign's result hidden, 2026 fitted jointly."""

import csv
import dataclasses
import hashlib
import json
from datetime import date
from pathlib import Path

import numpy as np
import pytest

import scripts.run_holdout_forecasts as driver
from backend.model import compact_mayoral_feed
from backend.model.compact_mayoral.hyperpriors import population_hyperpriors
from backend.model.compact_mayoral.qualification import Diagnostics
from backend.model.compact_mayoral.readings import (
    OUTCOMES,
    current_campaign,
    historical_campaigns,
)
from backend.model.compact_mayoral.sampling import PRODUCTION, FitResult
from tests.model.test_compact_mayoral_feed import _fixture_root

ELECTION_2026 = date(2026, 10, 26)
CUTOFF = date(2026, 10, 7)
HELD_OUT = "toronto_2018"


def _inputs(tmp_path: Path) -> tuple[Path, Path]:
    root = _fixture_root(tmp_path)
    return root / "polls", root / "data/upstream/results/mayoral_candidates.json"


def _scrambled_outcomes(path: Path, cycle: str) -> Path:
    """The outcomes table with one campaign's votes, shares and winner reversed."""
    with OUTCOMES.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fields, rows = reader.fieldnames, list(reader)
    held = [r for r in rows if r["election_cycle_id"] == cycle]
    results = [(r["votes"], r["share"], r["is_winner"]) for r in held]
    for row, (votes, share, winner) in zip(held, reversed(results)):
        row["votes"], row["share"], row["is_winner"] = votes, share, winner
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return path


def _holdout(polls: Path, candidates: Path, **kwargs):
    return driver.holdout_campaigns(
        polls,
        candidates,
        held_out=HELD_OUT,
        election_date=ELECTION_2026,
        cutoff=CUTOFF,
        **{"horizon_days": 1, **kwargs},
    )


def test_the_hidden_result_never_reaches_the_fit(tmp_path: Path) -> None:
    polls, candidates = _inputs(tmp_path)
    scrambled = _scrambled_outcomes(tmp_path / "scrambled.csv", HELD_OUT)

    real = _holdout(polls, candidates)
    other = _holdout(polls, candidates, outcomes_csv=scrambled)

    # Every input to the fit is identical whatever the hidden campaign's result was:
    # its numbers, and the candidate order production derives from final shares.
    assert real == other
    held = {c.key: c for c in real}[HELD_OUT]
    assert held.outcome_shares is None and held.outcome_tail is None


def test_training_campaigns_and_2026_are_exactly_productions(tmp_path: Path) -> None:
    polls, candidates = _inputs(tmp_path)
    history = historical_campaigns(polls)
    current = current_campaign(polls, candidates, election_date=ELECTION_2026, cutoff=CUTOFF)

    campaigns = _holdout(polls, candidates, horizon_days=30)

    assert [c.key for c in campaigns] == [*history, current.key]
    assert campaigns[-1] == current
    for c in campaigns[:-1]:
        if c.key != HELD_OUT:
            assert c == history[c.key]
    # The hidden campaign keeps its ballot and its polls from at least 30 days out.
    held = {c.key: c for c in campaigns}[HELD_OUT]
    assert sorted(held.names) == sorted(history[HELD_OUT].names)
    assert sorted(p.group for p in held.polls) == sorted(
        p.group for p in history[HELD_OUT].polls if p.days_before_election >= 30
    )
    assert len(held.polls) < len(history[HELD_OUT].polls)


def _diagnostics(divergences: int) -> Diagnostics:
    return Diagnostics(
        draws=4000,
        chains=4,
        divergences=divergences,
        worst_r_hat=1.001,
        min_ess=3000.0,
        coordinates_over_r_hat=0,
        mean_leapfrog_steps=255.0,
        constant_coordinates_ignored=0,
    )


def test_the_holdout_runs_productions_gated_fit(tmp_path: Path, monkeypatch) -> None:
    polls, candidates = _inputs(tmp_path)
    calls = []

    def fit_joint(campaigns, hyperpriors, *, settings):
        calls.append((campaigns, hyperpriors, settings))
        divergent = 2 if len(calls) == 1 else 0
        return FitResult({}, _diagnostics(divergent), 1.0, settings)

    monkeypatch.setattr(compact_mayoral_feed, "fit_joint", fit_joint)

    held, result = driver.run_holdout(
        polls,
        candidates,
        held_out=HELD_OUT,
        horizon_days=1,
        election_date=ELECTION_2026,
        cutoff=CUTOFF,
    )

    expected = _holdout(polls, candidates)
    assert held == {c.key: c for c in expected}[HELD_OUT]
    assert [c[0] for c in calls] == [expected, expected]
    assert all(c[1] == population_hyperpriors() for c in calls)
    # Production's settings, then the gate's retry after divergences.
    assert calls[0][2] == PRODUCTION
    assert calls[1][2] == dataclasses.replace(
        PRODUCTION, seed=PRODUCTION.seed + 1, target_accept=0.99
    )
    assert result.settings == calls[1][2]


def test_held_out_draws_are_written_with_their_provenance(tmp_path: Path) -> None:
    polls, candidates = _inputs(tmp_path)
    held = {c.key: c for c in _holdout(polls, candidates)}[HELD_OUT]
    k = len(held.candidates)
    outcome = np.random.default_rng(0).dirichlet(np.ones(k + 1), size=40)
    retry = dataclasses.replace(PRODUCTION, seed=PRODUCTION.seed + 1, target_accept=0.99)
    result = FitResult(
        {f"{HELD_OUT}/full_ballot": outcome[:, :k], f"{HELD_OUT}/tail": outcome[:, k]},
        _diagnostics(0),
        212.5,
        retry,
    )
    out = tmp_path / "out"

    path = driver.write_draws(out, held, result, {"command": "run it", "backend_commit": "abc"})

    with np.load(out / f"{HELD_OUT}.npz") as arrays:
        assert list(arrays["candidate_ids"]) == list(held.candidates)
        np.testing.assert_array_equal(arrays["full_ballot"], outcome[:, :k])
        np.testing.assert_array_equal(arrays["residual_pool"], outcome[:, k])
    record = json.loads(path.read_text(encoding="utf-8"))
    assert path == out / f"{HELD_OUT}.json"
    assert record["campaign"] == HELD_OUT
    assert record["draws"] == 40
    assert [c["candidate_id"] for c in record["candidates"]] == list(held.candidates)
    assert [c["name"] for c in record["candidates"]] == list(held.names)
    assert (
        record["npz_sha256"] == hashlib.sha256((out / f"{HELD_OUT}.npz").read_bytes()).hexdigest()
    )
    assert record["command"] == "run it" and record["backend_commit"] == "abc"
    assert record["fit"]["seed"] == PRODUCTION.seed + 1
    assert record["fit"]["target_accept"] == 0.99 and record["fit"]["retried"] is True
    assert record["fit"]["diagnostics"]["divergences"] == 0
    assert record["polls_used"] == len(held.polls)
    # A campaign's draws are written once; a rerun goes to a fresh directory.
    with pytest.raises(FileExistsError):
        driver.write_draws(out, held, result, {})
