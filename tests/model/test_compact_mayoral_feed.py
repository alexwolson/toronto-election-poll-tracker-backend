"""Schema-4 mayoral forecast feed assembled from the compact model's joint draws."""

import json
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pytest

from backend.model.compact_mayoral.readings import CampaignPolls, Poll
from backend.model.compact_mayoral.sampling import FitSettings
from backend.model.compact_mayoral_feed import (
    MAYORAL_FORECAST_FEED_SCHEMA_VERSION,
    PUBLICATION_POLICY,
    assemble_forecast_feed,
    build_compact_mayoral_forecast_feed,
    margin_bins,
)

CHOW = "per_chow0000000000000000000000000"
BRAD = "per_brad0000000000000000000000000"
ALEX = "per_alex0000000000000000000000000"
LIVE = {
    "election_cycle_id": "toronto-2026",
    "election_date": "2026-10-26",
    "viable_field": [CHOW, BRAD, ALEX],
    "incumbent_candidate_id": CHOW,
}
CUTOFF = datetime(2026, 9, 21, 12, 0, tzinfo=ZoneInfo("America/Toronto"))


def _campaign() -> CampaignPolls:
    polls = tuple(
        Poll(f"p{i}", f"p{i}", "A", 60 - 10 * i, 930.0, (0, 1, 2), (0.49, 0.40, 0.11))
        for i in range(3)
    )
    return CampaignPolls(
        "toronto-2026",
        (CHOW, BRAD, ALEX),
        ("Olivia Chow", "Brad Bradford", "Chris Alexander"),
        date(2026, 10, 26),
        polls,
        None,
        None,
        (0, 1),
    )


def _draws(n=2000, seed=3):
    rng = np.random.default_rng(seed)
    contest = rng.normal(0, 0.25, n)

    def composition(spread: float) -> np.ndarray:
        logits = np.stack(
            [
                np.log(0.49) + spread * contest,
                np.log(0.40) - spread * contest,
                np.full(n, np.log(0.11)),
            ],
            1,
        )
        return np.exp(logits) / np.exp(logits).sum(1, keepdims=True)

    # Three snapshots of the same simulations, each wider than the last: what the
    # polls say now, support at election day before the election-day error, the result.
    named = composition(1.0)
    tail = 1 / (1 + np.exp(-rng.normal(-2.9, 0.4, n)))
    return {
        "toronto-2026/named_result": named,
        "toronto-2026/tail": tail,
        "toronto-2026/full_ballot": named * (1 - tail)[:, None],
        "toronto-2026/current": composition(0.4),
        "toronto-2026/election_support": composition(0.7),
    }


def test_margin_bins_partition_the_signed_margin_and_sum_to_one() -> None:
    margins = np.array([-100.0, -12.5, 0.0, 4.9, 5.0, 99.9, 100.0])
    bins = margin_bins(margins)
    assert len(bins) == 40 and bins[0]["left"] == -100 and bins[-1]["right"] == 100
    assert sum(b["probability"] for b in bins) == pytest.approx(1.0)
    assert bins[20]["left"] == 0 and bins[20]["probability"] == pytest.approx(2 / 7)  # 0.0 and 4.9
    assert bins[-1]["probability"] == pytest.approx(2 / 7)  # 99.9 and the closed upper edge


def test_assembled_feed_is_schema_4_and_internally_coherent() -> None:
    draws = _draws()
    feed = assemble_forecast_feed(
        campaign=_campaign(),
        draws=draws,
        live_cycle=LIVE,
        analysis_cutoff=CUTOFF,
        model_record={
            "name": "compact_mayoral",
            "version": "test",
            "draws": 2000,
            "chains": 4,
            "seed": 1,
            "specification": {},
            "qualification_passed": True,
        },
        sensitivity=[],
        residual_named=[
            {
                "candidate_id": "per_x",
                "display_name": "X",
                "latest_polled_share": 0.02,
                "poll_id": "p2",
            }
        ],
        residual_candidate_count=50,
    )
    assert feed["schema_version"] == MAYORAL_FORECAST_FEED_SCHEMA_VERSION == 4
    assert feed["publication_policy"] == PUBLICATION_POLICY == "margin-first-joint-draws-v1"
    assert feed["election_cycle_id"] == "toronto_2026" and feed["election_date"] == "2026-10-26"
    assert feed["analysis_cutoff"] == CUTOFF.isoformat()
    assert feed["final_field_samples"] == ["p0", "p1", "p2"]
    assert feed["incumbent_candidate_id"] == CHOW
    assert set(feed["candidate_win"]) == {CHOW, BRAD, ALEX}
    wins = {cid: card["probability"] for cid, card in feed["candidate_win"].items()}
    assert sum(wins.values()) == pytest.approx(1.0, abs=1e-9)
    named = draws["toronto-2026/named_result"]
    assert wins[CHOW] == pytest.approx((named.argmax(1) == 0).mean())
    for cid, card in feed["candidate_win"].items():
        assert card["quantity"] == "challenger_win" and card["candidate_id"] == cid
        assert (
            card["availability"] == "Forecast Available" and card["tier"] == feed["evidence_tier"]
        )
        assert "band" not in card and "sensitivity" not in card
    fav = feed["forecast_favourite"]
    assert fav["candidate_id"] == CHOW and fav["availability"] == "Forecast Available"
    e = feed["election_day"]
    assert (
        e["denominator"] == "full_ballot"
        and e["interval_mass"] == 0.8
        and e["statistic"] == "median"
    )
    assert [c["candidate_id"] for c in e["candidates"]] == [CHOW, BRAD, ALEX]
    full = draws["toronto-2026/full_ballot"]
    for i, c in enumerate(e["candidates"]):
        assert c["lower"] <= c["median"] <= c["upper"]
        assert c["median"] == pytest.approx(float(np.median(full[:, i])), abs=1e-6)
        assert c["lower"] == pytest.approx(float(np.quantile(full[:, i], 0.1)), abs=1e-6)
        assert c["win_probability"] == wins[c["candidate_id"]]
    pool = e["residual_pool"]
    assert pool["win_probability"] == 0.0 and pool["candidate_count"] == 50
    assert pool["named_in_polls"][0]["display_name"] == "X"
    assert pool["median"] == pytest.approx(float(np.median(draws["toronto-2026/tail"])), abs=1e-6)
    m = e["pairwise_margin"]
    assert m["leader_candidate_id"] == CHOW and m["challenger_candidate_id"] == BRAD
    assert m["unit"] == "vote_share_points" and m["bin_width"] == 5 and m["range"] == [-100, 100]
    margins = 100 * (full[:, 0] - full[:, 1])
    assert m["median"] == pytest.approx(float(np.median(margins)), abs=1e-6)
    assert m["probability_challenger_ahead"] == pytest.approx(float((margins < 0).mean()))
    assert sum(b["probability"] for b in m["bins"]) == pytest.approx(1.0)
    assert feed["model"]["qualification_passed"] is True
    assert feed["sensitivity"] == []
    json.dumps(feed, allow_nan=False)  # serializable, no NaN


def test_pairwise_margin_carries_three_exact_outcomes_at_a_two_point_threshold() -> None:
    draws = _draws()
    feed = assemble_forecast_feed(
        campaign=_campaign(),
        draws=draws,
        live_cycle=LIVE,
        analysis_cutoff=CUTOFF,
        model_record={"name": "compact_mayoral", "qualification_passed": True},
        sensitivity=[],
        residual_named=[],
        residual_candidate_count=50,
    )
    m = feed["election_day"]["pairwise_margin"]
    outcomes = m["outcomes"]
    full = draws["toronto-2026/full_ballot"]
    margins = 100 * (full[:, 0] - full[:, 1])
    assert outcomes["close_threshold_points"] == 2
    assert outcomes["leader_ahead"] == pytest.approx(float((margins >= 2).mean()), abs=1e-6)
    assert outcomes["close"] == pytest.approx(
        float(((margins > -2) & (margins < 2)).mean()), abs=1e-6
    )
    assert outcomes["challenger_ahead"] == pytest.approx(float((margins <= -2).mean()), abs=1e-6)
    assert outcomes["leader_ahead"] + outcomes["close"] + outcomes[
        "challenger_ahead"
    ] == pytest.approx(1.0, abs=1e-5)
    # The pairwise probability still counts every draw by who is ahead.
    assert m["probability_challenger_ahead"] >= outcomes["challenger_ahead"]


def test_uncertainty_block_widens_step_by_step_and_ends_at_the_published_margin() -> None:
    draws = _draws()
    feed = assemble_forecast_feed(
        campaign=_campaign(),
        draws=draws,
        live_cycle=LIVE,
        analysis_cutoff=CUTOFF,
        model_record={"name": "compact_mayoral", "qualification_passed": True},
        sensitivity=[],
        residual_named=[],
        residual_candidate_count=50,
    )
    block = feed["uncertainty"]
    margin = feed["election_day"]["pairwise_margin"]
    assert block["leader_candidate_id"] == margin["leader_candidate_id"] == CHOW
    assert block["challenger_candidate_id"] == margin["challenger_candidate_id"] == BRAD
    assert block["unit"] == "vote_share_points" and block["interval_mass"] == 0.8
    assert [s["key"] for s in block["steps"]] == [
        "polls_today",
        "campaign_movement",
        "election_day",
    ]
    # Each step is the leader-minus-challenger gap in full-ballot points for one snapshot.
    scale = 1 - draws["toronto-2026/tail"]
    for step, site in zip(
        block["steps"], ("current", "election_support", "named_result"), strict=True
    ):
        shares = draws[f"toronto-2026/{site}"] * scale[:, None]
        gap = 100 * (shares[:, 0] - shares[:, 1])
        assert step["median"] == pytest.approx(float(np.median(gap)), abs=1e-6)
        assert step["lower"] == pytest.approx(float(np.quantile(gap, 0.1)), abs=1e-6)
        assert step["upper"] == pytest.approx(float(np.quantile(gap, 0.9)), abs=1e-6)
        assert step["probability_challenger_ahead"] == pytest.approx(
            float((gap < 0).mean()), abs=1e-6
        )
        assert step["probability_leader_ahead"] == pytest.approx(float((gap > 0).mean()), abs=1e-6)
    widths = [s["upper"] - s["lower"] for s in block["steps"]]
    assert widths[0] < widths[1] < widths[2]
    # The last step is exactly the published margin.
    last = block["steps"][-1]
    for key in ("median", "lower", "upper", "probability_challenger_ahead"):
        assert last[key] == margin[key]


def _fixture_root(tmp_path: Path) -> Path:
    results = tmp_path / "data/upstream/results"
    results.mkdir(parents=True)
    (results / "mayoral_candidates.json").write_text(
        json.dumps(
            {
                "schema_version": 5,
                "ballot_certified": True,
                "candidates": [
                    {"person_id": CHOW, "display_name": "Olivia Chow"},
                    {"person_id": BRAD, "display_name": "Brad Bradford"},
                    {"person_id": ALEX, "display_name": "Chris Alexander"},
                    {
                        "person_id": "per_mcvie000000000000000000000000",
                        "display_name": "Sarah McVie",
                    },
                    {
                        "person_id": "per_x0000000000000000000000000000",
                        "display_name": "Someone Else",
                    },
                ],
            }
        )
    )
    polls = tmp_path / "polls"
    polls.mkdir()
    (polls / "polls.csv").write_text(
        "poll_id,firm,date_conducted,sample_size,field_tested,alexander,bradford,chow,other,sarah-mcvie\n"
        'mainstreet-2026-09-14,Mainstreet Research,2026-09-17,1000,"alexander,bradford,chow,other,sarah-mcvie",0.096,0.377,0.458,0.024,0.025\n'
        'liaison-2026-09-05,Liaison Strategies,2026-09-05,1000,"alexander,bradford,chow,other",0.10,0.39,0.50,0.02,\n'
        'pallas-2026-08-21,Pallas Data,2026-08-21,808,"alexander,bradford,chow,other",0.081,0.393,0.501,0.026,\n'
        'liaison-2026-07-26,Liaison Strategies,2026-07-26,1000,"bradford,chow,other",,0.41,0.49,0.10,\n'
    )
    return tmp_path


def test_end_to_end_feed_from_the_joint_fit_on_fixture_inputs(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    fast = FitSettings(warmup=150, draws=150, chains=1, seed=5, target_accept=0.9)
    feed = build_compact_mayoral_forecast_feed(
        root,
        LIVE,
        polls_dir=root / "polls",
        analysis_cutoff=CUTOFF,
        settings=fast,
        sensitivity_settings=fast,
        qualification=None,
    )
    assert feed["schema_version"] == 4
    assert feed["final_field_samples"] == [
        "pallas-2026-08-21",
        "liaison-2026-09-05",
        "mainstreet-2026-09-14",
    ]
    assert feed["forecast_favourite"]["candidate_id"] == CHOW
    assert feed["election_day"]["residual_pool"]["candidate_count"] == 2
    assert [c["display_name"] for c in feed["election_day"]["residual_pool"]["named_in_polls"]] == [
        "Sarah McVie"
    ]
    assert {s["label"] for s in feed["sensitivity"]} == {
        "isotropic-discrepancy",
        "with-pre-certification-polls",
    }
    assert feed["model"]["draws"] == 150 and feed["model"]["qualification_passed"] is None
    assert feed["model"]["specification"] == {
        "discrepancy": "dirichlet",
        "innovations": "gaussian",
        "polls": "certified_field_only",
        "hyperpriors": "population_joint_refit",
    }
