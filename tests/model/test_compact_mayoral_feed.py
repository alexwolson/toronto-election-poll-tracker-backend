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
    history_cutoffs,
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


def test_uncertainty_block_isolates_each_source_and_ends_at_the_published_margin() -> None:
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
    assert [s["key"] for s in block["sources"]] == [
        "polls_today",
        "campaign_movement",
        "election_day",
    ]
    # Each source on its own, applied to today's middle estimate, in full-ballot points.
    scale = 1 - draws["toronto-2026/tail"]

    def gap(site: str) -> np.ndarray:
        shares = draws[f"toronto-2026/{site}"] * scale[:, None]
        return 100 * (shares[:, 0] - shares[:, 1])

    now, at_election, result = gap("current"), gap("election_support"), gap("named_result")
    centre = float(np.median(now))
    assert block["centre"] == pytest.approx(centre, abs=1e-6)
    expected = {
        "polls_today": now,
        "campaign_movement": centre + (at_election - now),
        "election_day": centre + (result - at_election),
    }
    for source in block["sources"]:
        x = expected[source["key"]]
        assert source["median"] == pytest.approx(float(np.median(x)), abs=1e-6)
        assert source["lower"] == pytest.approx(float(np.quantile(x, 0.1)), abs=1e-6)
        assert source["upper"] == pytest.approx(float(np.quantile(x, 0.9)), abs=1e-6)
        assert source["probability_challenger_ahead"] == pytest.approx(
            float((x < 0).mean()), abs=1e-6
        )
        assert source["probability_leader_ahead"] == pytest.approx(float((x > 0).mean()), abs=1e-6)
    # Shares of the uncertainty: each part's variance over the parts' summed variance.
    variances = {
        k: float(np.var(x - (centre if k == "polls_today" else 0))) for k, x in expected.items()
    }
    summed = sum(variances.values())
    for source in block["sources"]:
        assert source["share_of_uncertainty"] == pytest.approx(
            variances[source["key"]] / summed, abs=1e-6
        )
    assert sum(s["share_of_uncertainty"] for s in block["sources"]) == pytest.approx(1.0, abs=1e-5)
    assert block["variance_explained"] == pytest.approx(summed / float(np.var(result)), abs=1e-6)
    combined = block["combined"]
    for source in block["sources"]:
        assert source["upper"] - source["lower"] < combined["upper"] - combined["lower"]
    # All three together is exactly the published margin.
    for key in ("median", "lower", "upper", "probability_challenger_ahead"):
        assert combined[key] == margin[key]


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
    # The model reads the bundle tables (ADR 0057); the archive above feeds the
    # minor-candidate listing only. Same four samples, one reading each.
    (polls / "poll_samples.csv").write_text(
        "poll_sample_id,election_cycle_id,pollster,geography_type,fieldwork_end,publication_date,recruited_sample_size,extraction_status\n"
        "mainstreet-2026-09-14,toronto-2026,Mainstreet Research,citywide,2026-09-17,2026-09-18,1000,extracted\n"
        "liaison-2026-09-05,toronto-2026,Liaison Strategies,citywide,2026-09-05,2026-09-09,1000,extracted\n"
        "pallas-2026-08-21,toronto-2026,Pallas Data,citywide,2026-08-21,2026-08-25,808,extracted\n"
        "liaison-2026-07-26,toronto-2026,Liaison Strategies,citywide,2026-07-26,2026-07-29,1000,extracted\n"
    )
    (polls / "poll_readings.csv").write_text(
        "poll_reading_id,poll_sample_id,contest_type,reading_purpose,denominator_semantics,weighted_base,reported_base,unweighted_base\n"
        "mainstreet_dl,mainstreet-2026-09-14,mayoral,general_vote_intention,decided_plus_leaners,832.1,,\n"
        "liaison_0905_dl,liaison-2026-09-05,mayoral,general_vote_intention,decided_plus_leaners,838,,\n"
        "pallas_dl,pallas-2026-08-21,mayoral,general_vote_intention,decided_plus_leaners,618,,\n"
        "liaison_0726_dl,liaison-2026-07-26,mayoral,general_vote_intention,decided_plus_leaners,805,,\n"
    )
    rows = ["poll_reading_id,response_kind,candidate_id,candidate_name,share"]
    for rid, shares in (
        (
            "mainstreet_dl",
            {
                "alexander": 0.096,
                "bradford": 0.377,
                "chow": 0.458,
                "other": 0.024,
                "sarah-mcvie": 0.025,
            },
        ),
        ("liaison_0905_dl", {"alexander": 0.10, "bradford": 0.39, "chow": 0.50, "other": 0.02}),
        ("pallas_dl", {"alexander": 0.081, "bradford": 0.393, "chow": 0.501, "other": 0.026}),
        ("liaison_0726_dl", {"bradford": 0.41, "chow": 0.49, "other": 0.10}),
    ):
        for slug, share in shares.items():
            kind = "other" if slug == "other" else "candidate"
            rows.append(f"{rid},{kind},{slug if kind == 'candidate' else ''},,{share}")
    (polls / "poll_responses.csv").write_text("\n".join(rows) + "\n")
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
    # Forecast history: one point per publication date, each a refit on the polls
    # published by then; the last point is the main fit itself.
    history = feed["history"]
    assert [h["date"] for h in history] == ["2026-08-25", "2026-09-09", "2026-09-18"]
    assert [h["poll_sample_ids"] for h in history] == [
        ["pallas-2026-08-21"],
        ["liaison-2026-09-05"],
        ["mainstreet-2026-09-14"],
    ]
    assert [h["polls"] for h in history] == [1, 2, 3]
    for point in history:
        assert set(point["win_probability"]) == {CHOW, BRAD, ALEX}
        assert sum(point["win_probability"].values()) == pytest.approx(1.0, abs=1e-6)
        assert point["diagnostics"]["divergences"] >= 0
    assert history[-1]["win_probability"] == {
        cid: card["probability"] for cid, card in feed["candidate_win"].items()
    }


def test_history_cutoffs_group_polls_by_publication_date() -> None:
    polls = tuple(
        Poll(f"r{i}", sid, "A", d, 900.0, (0, 1, 2), (0.5, 0.4, 0.1))
        for i, (sid, d) in enumerate(
            [("early", 60), ("fielded-first", 50), ("same-day", 45), ("late", 40)]
        )
    )
    campaign = CampaignPolls(
        "toronto-2026",
        ("a", "b", "c"),
        ("A", "B", "C"),
        date(2026, 10, 26),
        polls,
        None,
        None,
        (0, 1),
    )
    published = {
        "early": "2026-08-01",
        "fielded-first": "2026-09-23",  # released last, like Ipsos
        "same-day": "2026-08-20",
        "late": "2026-08-20",
    }
    cutoffs = history_cutoffs(campaign, published)
    assert [c.date for c in cutoffs] == ["2026-08-01", "2026-08-20", "2026-09-23"]
    assert [c.new_samples for c in cutoffs] == [["early"], ["late", "same-day"], ["fielded-first"]]
    assert [sorted(p.group for p in c.campaign.polls) for c in cutoffs] == [
        ["early"],
        ["early", "late", "same-day"],
        ["early", "fielded-first", "late", "same-day"],
    ]
    with pytest.raises(ValueError, match="publication date"):
        history_cutoffs(campaign, {k: v for k, v in published.items() if k != "late"})


def _without_timings(value):
    if isinstance(value, dict):
        return {k: _without_timings(v) for k, v in value.items() if k != "elapsed_seconds"}
    if isinstance(value, list):
        return [_without_timings(v) for v in value]
    return value


def test_concurrent_fits_build_the_same_feed_as_sequential_fits(tmp_path: Path, capsys) -> None:
    root = _fixture_root(tmp_path)
    fast = FitSettings(warmup=100, draws=100, chains=1, seed=5, target_accept=0.9)
    common = {
        "polls_dir": root / "polls",
        "analysis_cutoff": CUTOFF,
        "settings": fast,
        "sensitivity_settings": fast,
        "qualification": None,
    }
    sequential = build_compact_mayoral_forecast_feed(root, LIVE, fit_workers=1, **common)
    capsys.readouterr()
    concurrent = build_compact_mayoral_forecast_feed(root, LIVE, fit_workers=3, **common)
    log = capsys.readouterr().out
    assert _without_timings(concurrent) == _without_timings(sequential)
    # one timing line per fit: main, two earlier history points, two sensitivity refits
    assert log.count("[compact fit]") == 5


def test_fit_worker_count_fills_the_cores_without_oversubscribing(monkeypatch) -> None:
    from backend.model.compact_mayoral_feed import fit_worker_count

    monkeypatch.delenv("COMPACT_FIT_WORKERS", raising=False)
    assert fit_worker_count(chains=4, jobs=11, cpu_count=14) == 3
    assert fit_worker_count(chains=4, jobs=2, cpu_count=14) == 2
    assert fit_worker_count(chains=4, jobs=11, cpu_count=2) == 1
    monkeypatch.setenv("COMPACT_FIT_WORKERS", "1")
    assert fit_worker_count(chains=4, jobs=11, cpu_count=14) == 1


def test_history_points_are_reused_from_the_cache_and_match_a_fresh_fit(
    tmp_path: Path, capsys
) -> None:
    root = _fixture_root(tmp_path)
    fast = FitSettings(warmup=100, draws=100, chains=1, seed=5, target_accept=0.9)
    common = {
        "polls_dir": root / "polls",
        "analysis_cutoff": CUTOFF,
        "settings": fast,
        "sensitivity_settings": fast,
        "qualification": None,
        "fit_workers": 1,
    }
    cache = tmp_path / "history-cache"
    fresh = build_compact_mayoral_forecast_feed(root, LIVE, **common)
    capsys.readouterr()
    first = build_compact_mayoral_forecast_feed(root, LIVE, history_cache_dir=cache, **common)
    first_log = capsys.readouterr().out
    second = build_compact_mayoral_forecast_feed(root, LIVE, history_cache_dir=cache, **common)
    second_log = capsys.readouterr().out
    assert len(list(cache.glob("*.json"))) == 2  # the two earlier history points
    assert first_log.count(": cached") == 0 and first_log.count("[compact fit]") == 5
    # second build: main + two sensitivity refits fit; both history points come from the cache
    assert second_log.count(": cached") == 2
    assert second_log.count("[compact fit]") == 5
    assert _without_timings(second) == _without_timings(first) == _without_timings(fresh)


def test_history_cache_key_changes_with_every_input(tmp_path: Path) -> None:
    import dataclasses

    from backend.model.compact_mayoral.hyperpriors import population_hyperpriors
    from backend.model.compact_mayoral_feed import history_cache_key

    campaign = _campaign()
    cutoff = history_cutoffs(
        campaign, {"p0": "2026-08-01", "p1": "2026-08-10", "p2": "2026-08-20"}
    )[1]
    fast = FitSettings(warmup=100, draws=100, chains=1, seed=5, target_accept=0.9)
    hyper = population_hyperpriors()
    base = history_cache_key(cutoff, (), hyper, fast, qualified=True)
    assert base == history_cache_key(cutoff, (), hyper, fast, qualified=True)
    other_poll = dataclasses.replace(
        cutoff,
        campaign=dataclasses.replace(
            cutoff.campaign,
            polls=(
                dataclasses.replace(cutoff.campaign.polls[0], n_eff=931.0),
                *cutoff.campaign.polls[1:],
            ),
        ),
    )
    variants = [
        history_cache_key(other_poll, (), hyper, fast, qualified=True),
        history_cache_key(cutoff, (campaign,), hyper, fast, qualified=True),
        history_cache_key(cutoff, (), {**hyper, "extra": 1.0}, fast, qualified=True),
        history_cache_key(cutoff, (), hyper, dataclasses.replace(fast, seed=6), qualified=True),
        history_cache_key(cutoff, (), hyper, fast, qualified=False),
    ]
    assert base not in variants and len(set(variants)) == len(variants)


def test_history_cache_location_follows_the_environment(monkeypatch, tmp_path: Path) -> None:
    from backend.model.compact_mayoral_feed import history_cache_dir_from_env

    monkeypatch.setenv("COMPACT_HISTORY_CACHE", "off")
    assert history_cache_dir_from_env() is None
    monkeypatch.setenv("COMPACT_HISTORY_CACHE", str(tmp_path))
    assert history_cache_dir_from_env() == tmp_path
    monkeypatch.delenv("COMPACT_HISTORY_CACHE")
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "xdg"))
    assert (
        history_cache_dir_from_env()
        == tmp_path / "xdg" / "toronto-election-backend" / "compact-history"
    )
