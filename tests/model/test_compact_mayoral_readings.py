"""Compact mayoral model adapter over the Polling release: historical corpus and 2026 polls."""

import csv
import json
import shutil
from datetime import date
from pathlib import Path

import pytest

from backend.model.compact_mayoral.exits import Exit, kept_fraction_prior, load_cases
from backend.model.compact_mayoral.readings import (
    EXTRA_2026,
    CampaignPolls,
    Poll,
    current_campaign,
    current_reading_selection,
    historical_campaigns,
    with_horizon,
)

ELECTION_2026 = date(2026, 10, 26)
HISTORICAL_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "historical_polling"
CHOW = "per_chow0000000000000000000000000"
BRAD = "per_brad0000000000000000000000000"
ALEX = "per_alex0000000000000000000000000"


def _historical_polling(tmp_path: Path) -> Path:
    """A Polling release directory holding the 2010 and 2018 historical campaigns."""
    polling = tmp_path / "historical_polling"
    shutil.copytree(HISTORICAL_FIXTURE, polling)
    return polling


def test_historical_campaigns_read_the_polling_release_tables(tmp_path: Path) -> None:
    camps = historical_campaigns(_historical_polling(tmp_path))
    assert set(camps) == {"toronto_2010", "toronto_2018"}
    c = camps["toronto_2018"]
    assert {"John Tory", "Jennifer Keesmaat"} <= set(c.names)
    assert c.election_date == date(2018, 10, 22)
    assert sum(c.outcome_shares) == pytest.approx(1.0)
    for camp in camps.values():
        assert len({p.group for p in camp.polls}) == len(camp.polls)
        assert all(len(p.offered) >= 2 and p.n_eff > 0 for p in camp.polls)


def _candidates_feed(path: Path, *, alexander_suspended_on: str | None = None) -> Path:
    """The Results candidates feed at schema 6 (``campaign_suspended_on`` on every row)."""
    rows = [
        (CHOW, "Olivia Chow", None),
        (BRAD, "Brad Bradford", None),
        (ALEX, "Chris Alexander", alexander_suspended_on),
        ("per_mcvie000000000000000000000000", "Sarah McVie", None),
    ]
    path.write_text(
        json.dumps(
            {
                "schema_version": 6,
                "ballot_certified": True,
                "candidates": [
                    {"person_id": pid, "display_name": name, "campaign_suspended_on": day}
                    for pid, name, day in rows
                ],
            }
        )
    )
    return path


def _bundle_inputs(tmp_path: Path) -> tuple[Path, Path]:
    """A polling-bundle directory (samples, readings, responses) and the certified field."""
    candidates = _candidates_feed(tmp_path / "mayoral_candidates.json")
    polling = tmp_path / "polling"
    polling.mkdir()

    def write(name: str, columns: list[str], rows: list[dict]) -> None:
        with (polling / name).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)

    def sample(sid, firm, end, n, geography="citywide", status="extracted"):
        return {
            "poll_sample_id": sid,
            "election_cycle_id": "toronto-2026",
            "pollster": firm,
            "geography_type": geography,
            "fieldwork_end": end,
            "recruited_sample_size": n,
            "extraction_status": status,
        }

    def reading(
        rid,
        sid,
        semantics,
        weighted="",
        reported="",
        unweighted="",
        purpose="general_vote_intention",
    ):
        return {
            "poll_reading_id": rid,
            "poll_sample_id": sid,
            "contest_type": "mayoral",
            "reading_purpose": purpose,
            "denominator_semantics": semantics,
            "weighted_base": weighted,
            "reported_base": reported,
            "unweighted_base": unweighted,
        }

    def responses(rid, shares: dict[str, float]):
        return [
            {
                "poll_reading_id": rid,
                "response_kind": "candidate"
                if key not in {"other", "undecided", "would_not_vote"}
                else key,
                "person_id": {
                    "chow": CHOW,
                    "bradford": BRAD,
                    "alexander": ALEX,
                    "sarah-mcvie": "per_mcvie000000000000000000000000",
                }.get(key, ""),
                "source_candidate_id": key
                if key not in {"other", "undecided", "would_not_vote"}
                else "",
                "candidate_name": {
                    "chow": "Olivia Chow",
                    "bradford": "Brad Bradford",
                    "alexander": "Chris Alexander",
                    "sarah-mcvie": "Sarah McVie",
                }.get(key, ""),
                "share": str(value),
            }
            for key, value in shares.items()
        ]

    write(
        "poll_samples.csv",
        [
            "poll_sample_id",
            "election_cycle_id",
            "pollster",
            "geography_type",
            "fieldwork_end",
            "recruited_sample_size",
            "extraction_status",
        ],
        [
            sample("liaison-2026-07-26", "Liaison Strategies", "2026-07-26", "1000"),
            sample("liaison-2026-09-05", "Liaison Strategies", "2026-09-05", "1000"),
            sample("ipsos-2026-09-08", "Ipsos", "2026-09-08", "1006"),
            sample("mainstreet-2026-09-14", "Mainstreet Research", "2026-09-17", "1000"),
            sample("forum_w13_2026", "Forum Research", "2026-09-10", "300", geography="ward"),
            sample("abacus-2026-01-27", "Abacus Data", "2026-01-27", "1001", status="blocked"),
        ],
    )
    write(
        "poll_readings.csv",
        [
            "poll_reading_id",
            "poll_sample_id",
            "contest_type",
            "reading_purpose",
            "denominator_semantics",
            "weighted_base",
            "reported_base",
            "unweighted_base",
        ],
        [
            reading(
                "liaison_0726_dl", "liaison-2026-07-26", "decided_plus_leaners", weighted="805"
            ),
            reading("liaison_0905_all", "liaison-2026-09-05", "all_respondents", weighted="1000"),
            reading(
                "liaison_0905_dl", "liaison-2026-09-05", "decided_plus_leaners", weighted="900"
            ),
            reading("ipsos_0908_all", "ipsos-2026-09-08", "all_respondents", weighted="1006"),
            reading("ipsos_0908_likely", "ipsos-2026-09-08", "other", weighted="578"),
            reading(
                "mainstreet_0914_dl",
                "mainstreet-2026-09-14",
                "decided_plus_leaners",
                weighted="832.1",
            ),
            reading(
                "mainstreet_0914_ctx",
                "mainstreet-2026-09-14",
                "all_respondents",
                weighted="1000",
                purpose="context_only",
            ),
            reading("forum_w13_mayor", "forum_w13_2026", "all_respondents", unweighted="300"),
        ],
    )
    write(
        "poll_responses.csv",
        [
            "poll_reading_id",
            "response_kind",
            "person_id",
            "source_candidate_id",
            "candidate_name",
            "share",
        ],
        [
            *responses("liaison_0726_dl", {"chow": 0.49, "bradford": 0.41, "other": 0.10}),
            *responses(
                "liaison_0905_all",
                {
                    "chow": 0.45,
                    "bradford": 0.35,
                    "alexander": 0.09,
                    "other": 0.02,
                    "undecided": 0.09,
                },
            ),
            *responses(
                "liaison_0905_dl",
                {"chow": 0.50, "bradford": 0.39, "alexander": 0.10, "other": 0.01},
            ),
            *responses(
                "ipsos_0908_all",
                {
                    "chow": 0.36,
                    "bradford": 0.21,
                    "alexander": 0.04,
                    "other": 0.05,
                    "undecided": 0.30,
                    "would_not_vote": 0.03,
                },
            ),
            *responses(
                "ipsos_0908_likely",
                {
                    "chow": 0.42,
                    "bradford": 0.27,
                    "alexander": 0.04,
                    "other": 0.04,
                    "undecided": 0.23,
                },
            ),
            *responses(
                "mainstreet_0914_dl",
                {
                    "chow": 0.458,
                    "bradford": 0.377,
                    "alexander": 0.096,
                    "sarah-mcvie": 0.025,
                    "other": 0.044,
                },
            ),
            *responses(
                "mainstreet_0914_ctx",
                {"chow": 0.40, "bradford": 0.30, "alexander": 0.08, "undecided": 0.22},
            ),
            *responses("forum_w13_mayor", {"chow": 0.5, "bradford": 0.4, "alexander": 0.1}),
        ],
    )
    # Polling's 2026 reading classification: every reading classified once.
    with (polling / "poll_readings.csv").open(encoding="utf-8") as handle:
        ids = [r["poll_reading_id"] for r in csv.DictReader(handle)]
    write(
        "reading_classification.csv",
        ["poll_reading_id", "scope", "measurement_class"],
        [
            {
                "poll_reading_id": rid,
                "scope": "citywide_mayoral",
                "measurement_class": "campaign_vote_intention",
            }
            for rid in ids
        ],
    )
    # Polling's model exclusions: none unless a test adds one (ADR 0062).
    (polling / "model_exclusions.csv").write_text(
        "poll_sample_id,decided_on,reasons,explanation,notes\n", encoding="utf-8"
    )
    return polling, candidates


def _append(polling: Path, name: str, rows: list[dict]) -> None:
    """Append rows to a bundle table, filling absent columns with blanks."""
    with (polling / name).open(encoding="utf-8") as handle:
        columns = next(csv.reader(handle))
    with (polling / name).open("a", newline="", encoding="utf-8") as handle:
        csv.DictWriter(handle, fieldnames=columns, restval="").writerows(rows)


def _add_sample(polling, sid, end, readings, *, firm="Forum Research", start=None, n="1000"):
    """One citywide 2026 sample with its readings: (id, semantics, base, class, shares)."""
    _append(
        polling,
        "poll_samples.csv",
        [
            {
                "poll_sample_id": sid,
                "election_cycle_id": "toronto-2026",
                "pollster": firm,
                "geography_type": "citywide",
                "fieldwork_end": end,
                "recruited_sample_size": n,
                "extraction_status": "extracted",
            }
        ],
    )
    slugs = {"chow": CHOW, "bradford": BRAD, "alexander": ALEX}
    for rid, semantics, base, measurement, shares in readings:
        _append(
            polling,
            "poll_readings.csv",
            [
                {
                    "poll_reading_id": rid,
                    "poll_sample_id": sid,
                    "contest_type": "mayoral",
                    "reading_purpose": "general_vote_intention",
                    "denominator_semantics": semantics,
                    "weighted_base": base,
                }
            ],
        )
        _append(
            polling,
            "poll_responses.csv",
            [
                {
                    "poll_reading_id": rid,
                    "response_kind": "candidate",
                    "person_id": slugs[key],
                    "source_candidate_id": key,
                    "share": str(value),
                }
                for key, value in shares.items()
            ],
        )
        _append(
            polling,
            "reading_classification.csv",
            [
                {
                    "poll_reading_id": rid,
                    "scope": "citywide_mayoral",
                    "measurement_class": measurement,
                }
            ],
        )


CUTOFF_2026 = date(2026, 10, 7)
FULL = "campaign_vote_intention"
H2H = "alternative_ballot"


def _post_exit_inputs(tmp_path: Path) -> tuple[Path, Path]:
    """The bundle plus Alexander's Suspended Campaign (Oct 6) and five later samples."""
    polling, candidates = _bundle_inputs(tmp_path)
    _candidates_feed(candidates, alexander_suspended_on="2026-10-06")
    # Fieldwork ends the day before the exit and omits Alexander: still pre-exit, so
    # it needs all three named candidates and is left out.
    _add_sample(
        polling,
        "liaison-2026-10-05",
        "2026-10-05",
        [("liaison_1005_dl", "decided_plus_leaners", "900", FULL, {"chow": 0.5, "bradford": 0.4})],
        firm="Liaison Strategies",
    )
    # Ends on the exit day without naming him: a Post-Suspension Reading.
    _add_sample(
        polling,
        "forum-2026-10-06",
        "2026-10-06",
        [("forum_1006_dl", "decided_plus_leaners", "1400", FULL, {"chow": 0.46, "bradford": 0.42})],
    )
    # Still names him: his share is set aside, and the base scales with what remains.
    _add_sample(
        polling,
        "mainstreet-2026-10-08",
        "2026-10-08",
        [
            (
                "mainstreet_1008_dl",
                "decided_plus_leaners",
                "800",
                FULL,
                {"chow": 0.47, "bradford": 0.43, "alexander": 0.02},
            )
        ],
        firm="Mainstreet Research",
    )
    # Full field and a head-to-head in one sample: the full field wins even though the
    # head-to-head has the better denominator.
    _add_sample(
        polling,
        "pallas-2026-10-09",
        "2026-10-09",
        [
            ("pallas_1009_all", "all_respondents", "700", FULL, {"chow": 0.40, "bradford": 0.35}),
            (
                "pallas_1009_h2h",
                "decided_plus_leaners",
                "650",
                H2H,
                {"chow": 0.52, "bradford": 0.48},
            ),
        ],
        firm="Pallas Data",
    )
    # A head-to-head that is the sample's only general vote-intention reading counts.
    _add_sample(
        polling,
        "nanos-2026-10-10",
        "2026-10-10",
        [("nanos_1010_h2h", "decided_only", "600", H2H, {"chow": 0.55, "bradford": 0.45})],
        firm="Nanos Research",
    )
    return polling, candidates


def test_last_poll_offering_thomson_enters_the_2010_campaign(tmp_path: Path) -> None:
    # backend#35: Ipsos Reid, Sept 24-26, 2010 (fieldwork midpoint 30 days out), the
    # last poll that offered Thomson before her campaign was suspended, enters as
    # its all-respondents topline; the same-sample two-way is not an ordinary reading.
    c = historical_campaigns(_historical_polling(tmp_path))["toronto_2010"]
    poll = next(p for p in c.polls if p.group == "ipsos_city_2010_09_26_n400")
    assert poll.reading_id == "ipsos_2010-09-27_release__r1"
    assert poll.days_before_election == 30
    assert {c.names[i] for i in poll.offered} == {
        "Rob Ford",
        "George Smitherman",
        "Joe Pantalone",
        "Rocco Rossi",
        "Sarah Thomson",
    }
    assert len(c.polls) == 10


def test_historical_selection_follows_each_readings_own_denominator(tmp_path: Path) -> None:
    # One rule for every campaign (ADR 0057, 0060): a sample's ordinary reading is
    # chosen by its own denominator_semantics; two "other" readings tie and go to
    # the reading naming more candidates, then to id.
    polling = _historical_polling(tmp_path)
    with (polling / "historical_mayoral_poll_readings.csv").open(encoding="utf-8") as handle:
        semantics = {
            r["poll_reading_id"]: r["denominator_semantics"] for r in csv.DictReader(handle)
        }
    assert semantics["probit_2018_all"] == semantics["probit_2018_undecideds_removed"] == "other"
    c = historical_campaigns(polling)["toronto_2018"]
    probit = [p for p in c.polls if p.group.startswith("probit_")]
    assert [p.reading_id for p in probit] == ["probit_2018_all"]


def test_current_campaign_selects_one_reading_per_sample_by_denominator_rank(
    tmp_path: Path,
) -> None:
    polling, candidates = _bundle_inputs(tmp_path)
    c = current_campaign(polling, candidates, election_date=ELECTION_2026, cutoff=CUTOFF_2026)
    assert c.key == "toronto-2026"
    assert c.candidates == (CHOW, BRAD, ALEX)
    assert c.names == ("Olivia Chow", "Brad Bradford", "Chris Alexander")
    # Oldest first; the pre-certified two-way poll, the ward poll, the blocked sample
    # and the context-only reading are all out.
    assert [p.group for p in c.polls] == [
        "liaison-2026-09-05",
        "ipsos-2026-09-08",
        "mainstreet-2026-09-14",
    ]
    assert [p.reading_id for p in c.polls] == [
        "liaison_0905_dl",
        "ipsos_0908_all",
        "mainstreet_0914_dl",
    ]
    liaison, ipsos, mainstreet = c.polls
    # Decided-and-leaning beats all-respondents; its own base sets the weight.
    assert liaison.n_eff == pytest.approx(900 * 0.99)
    assert liaison.shares == pytest.approx((0.50 / 0.99, 0.39 / 0.99, 0.10 / 0.99))
    # All-respondents beats a turnout screen ("other"); undecideds come out in the weight.
    assert ipsos.n_eff == pytest.approx(1006 * 0.61)
    assert ipsos.shares == pytest.approx((0.36 / 0.61, 0.21 / 0.61, 0.04 / 0.61))
    # The reading's weighted base, not the recruited sample, is the base.
    assert mainstreet.n_eff == pytest.approx(832.1 * (0.458 + 0.377 + 0.096))
    assert mainstreet.days_before_election == (ELECTION_2026 - date(2026, 9, 17)).days
    assert c.outcome_shares is None and c.leaders == (0, 1)


def test_current_campaign_can_widen_to_the_pre_certified_field(tmp_path: Path) -> None:
    polling, candidates = _bundle_inputs(tmp_path)
    wide = current_campaign(
        polling,
        candidates,
        election_date=ELECTION_2026,
        cutoff=CUTOFF_2026,
        require_full_field=False,
    )
    assert wide.polls[0].group == "liaison-2026-07-26"
    assert wide.polls[0].offered == (0, 1)
    assert wide.polls[0].n_eff == pytest.approx(805 * 0.90)
    assert len(wide.polls) == 4


def test_current_campaign_can_name_minor_candidates(tmp_path: Path) -> None:
    polling, candidates = _bundle_inputs(tmp_path)
    c = current_campaign(
        polling,
        candidates,
        election_date=ELECTION_2026,
        cutoff=CUTOFF_2026,
        extra_named=EXTRA_2026[:1],
    )
    assert c.names[-1] == "Sarah McVie" and c.candidates[-1] == "per_mcvie000000000000000000000000"
    assert c.polls[-1].offered == (0, 1, 2, 3)
    assert c.polls[0].offered == (0, 1, 2)


def test_current_reading_selection_is_published_for_the_feed(tmp_path: Path) -> None:
    polling, candidates = _bundle_inputs(tmp_path)
    chosen = current_reading_selection(polling, candidates, cutoff=CUTOFF_2026)
    assert [row["poll_sample_id"] for row in chosen] == [
        "liaison-2026-09-05",
        "ipsos-2026-09-08",
        "mainstreet-2026-09-14",
    ]
    liaison = chosen[0]
    assert liaison["poll_reading_id"] == "liaison_0905_dl"
    assert liaison["denominator_semantics"] == "decided_plus_leaners"
    assert liaison["base"] == pytest.approx(900)
    assert liaison["named_share"] == pytest.approx(0.99)
    assert all(row["post_suspension"] is False and row["set_aside"] == [] for row in chosen)


def test_without_a_suspended_campaign_the_current_campaign_has_no_exit(tmp_path: Path) -> None:
    polling, candidates = _bundle_inputs(tmp_path)
    c = current_campaign(polling, candidates, election_date=ELECTION_2026, cutoff=CUTOFF_2026)
    assert c.exits == ()


def test_post_suspension_readings_enter_over_the_remaining_candidates(tmp_path: Path) -> None:
    polling, candidates = _post_exit_inputs(tmp_path)
    c = current_campaign(polling, candidates, election_date=ELECTION_2026, cutoff=CUTOFF_2026)
    # The exit: Alexander, Oct 6, 20 days out, with the ten-case kept-fraction prior.
    mu, sigma = kept_fraction_prior(load_cases())
    assert c.exits == (Exit(2, date(2026, 10, 6), 20, mu, sigma),)
    by_group = {p.group: p for p in c.polls}
    assert "liaison-2026-10-05" not in by_group  # pre-exit, two names only
    assert [p.group for p in c.polls][:3] == [
        "liaison-2026-09-05",
        "ipsos-2026-09-08",
        "mainstreet-2026-09-14",
    ]
    assert by_group["ipsos-2026-09-08"].offered == (0, 1, 2)  # pre-exit readings unchanged
    forum = by_group["forum-2026-10-06"]
    assert forum.offered == (0, 1) and forum.days_before_election == 20
    assert forum.shares == pytest.approx((0.46 / 0.88, 0.42 / 0.88))
    assert forum.n_eff == pytest.approx(1400 * 0.88)
    mainstreet = by_group["mainstreet-2026-10-08"]
    assert mainstreet.offered == (0, 1)  # his 2% is set aside
    assert mainstreet.shares == pytest.approx((0.47 / 0.90, 0.43 / 0.90))
    assert mainstreet.n_eff == pytest.approx(800 * 0.90)
    pallas = by_group["pallas-2026-10-09"]
    assert pallas.reading_id == "pallas_1009_all"  # full field beats the head-to-head
    assert pallas.n_eff == pytest.approx(700 * 0.75)
    assert by_group["nanos-2026-10-10"].reading_id == "nanos_1010_h2h"


def test_post_suspension_selection_is_published_for_the_feed(tmp_path: Path) -> None:
    polling, candidates = _post_exit_inputs(tmp_path)
    chosen = {
        row["poll_sample_id"]: row
        for row in current_reading_selection(polling, candidates, cutoff=CUTOFF_2026)
    }
    assert chosen["ipsos-2026-09-08"]["post_suspension"] is False
    assert chosen["ipsos-2026-09-08"]["set_aside"] == []
    assert chosen["forum-2026-10-06"]["post_suspension"] is True
    assert chosen["forum-2026-10-06"]["set_aside"] == []  # it did not name him
    assert chosen["mainstreet-2026-10-08"]["set_aside"] == [ALEX]
    assert chosen["mainstreet-2026-10-08"]["named_share"] == pytest.approx(0.90)
    assert chosen["pallas-2026-10-09"]["poll_reading_id"] == "pallas_1009_all"
    assert "liaison-2026-10-05" not in chosen


def test_an_excluded_sample_never_enters_the_fit(tmp_path: Path) -> None:
    polling, candidates = _post_exit_inputs(tmp_path)
    before = {
        p.group
        for p in current_campaign(
            polling, candidates, election_date=ELECTION_2026, cutoff=CUTOFF_2026
        ).polls
    }
    _append(
        polling,
        "model_exclusions.csv",
        [
            {
                "poll_sample_id": "forum-2026-10-06",
                "decided_on": "2026-10-08",
                "reasons": "methodology_confidence",
                "explanation": "Listed for the record only.",
            }
        ],
    )
    c = current_campaign(polling, candidates, election_date=ELECTION_2026, cutoff=CUTOFF_2026)
    assert {p.group for p in c.polls} == before - {"forum-2026-10-06"}
    chosen = {
        row["poll_sample_id"]
        for row in current_reading_selection(polling, candidates, cutoff=CUTOFF_2026)
    }
    assert "forum-2026-10-06" not in chosen
    assert c.exits  # the exit itself does not depend on any one poll


def test_the_forecast_requires_the_model_exclusions_table(tmp_path: Path) -> None:
    polling, candidates = _bundle_inputs(tmp_path)
    (polling / "model_exclusions.csv").unlink()
    with pytest.raises(FileNotFoundError):
        current_campaign(polling, candidates, election_date=ELECTION_2026, cutoff=CUTOFF_2026)


def test_a_suspended_campaign_after_the_cutoff_is_not_applied(tmp_path: Path) -> None:
    polling, candidates = _post_exit_inputs(tmp_path)
    c = current_campaign(polling, candidates, election_date=ELECTION_2026, cutoff=date(2026, 10, 5))
    assert c.exits == ()
    # Before the exit is known every reading still needs all three named candidates.
    assert {p.group for p in c.polls} == {
        "liaison-2026-09-05",
        "ipsos-2026-09-08",
        "mainstreet-2026-09-14",
        "mainstreet-2026-10-08",
    }


def test_the_forecast_requires_the_results_feed_at_schema_6(tmp_path: Path) -> None:
    polling, candidates = _bundle_inputs(tmp_path)
    feed = json.loads(candidates.read_text())
    candidates.write_text(json.dumps({**feed, "schema_version": 5}))
    with pytest.raises(ValueError, match="schema 6"):
        current_campaign(polling, candidates, election_date=ELECTION_2026, cutoff=CUTOFF_2026)


def test_the_forecast_requires_the_2026_reading_classification(tmp_path: Path) -> None:
    polling, candidates = _bundle_inputs(tmp_path)
    (polling / "reading_classification.csv").unlink()
    with pytest.raises(FileNotFoundError):
        current_campaign(polling, candidates, election_date=ELECTION_2026, cutoff=CUTOFF_2026)


def test_with_horizon_truncates_and_recomputes_leaders() -> None:
    polls = tuple(
        Poll(f"p{i}", f"p{i}", "A", d, 900.0, (0, 1, 2), s)
        for i, (d, s) in enumerate(
            [(60, (0.5, 0.4, 0.1)), (40, (0.5, 0.4, 0.1)), (5, (0.2, 0.7, 0.1))]
        )
    )
    c = CampaignPolls(
        "s", ("a", "b", "c"), ("A", "B", "C"), ELECTION_2026, polls, None, None, (1, 0)
    )
    assert with_horizon(c, 39).leaders == (0, 1)
    assert [p.days_before_election for p in with_horizon(c, 39).polls] == [60, 40]
    with pytest.raises(ValueError):
        with_horizon(c, 61)
