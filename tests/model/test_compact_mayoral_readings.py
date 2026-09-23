"""Compact mayoral model adapter over the backend-tracked corpus and the release polls."""

import csv
import json
from datetime import date
from pathlib import Path

import pytest

from backend.model.compact_mayoral.readings import (
    CLASSIFICATION,
    EXTRA_2026,
    CampaignPolls,
    Poll,
    current_campaign,
    current_reading_selection,
    historical_campaigns,
    with_horizon,
)

ELECTION_2026 = date(2026, 10, 26)
CHOW = "per_chow0000000000000000000000000"
BRAD = "per_brad0000000000000000000000000"
ALEX = "per_alex0000000000000000000000000"


def test_tracked_classification_table_covers_every_register_reading() -> None:
    rows = list(csv.DictReader(CLASSIFICATION.open(encoding="utf-8")))
    assert len(rows) == 265
    assert {r["corpus"] for r in rows} == {"historical"}
    assert {r["measurement_class"] for r in rows} >= {
        "campaign_vote_intention",
        "alternative_ballot",
    }
    provenance = json.loads(CLASSIFICATION.with_suffix(".provenance.json").read_text())
    assert provenance["rows"] == 265 and len(provenance["source_sha256"]) == 64


def test_historical_campaigns_from_backend_tracked_inputs() -> None:
    camps = historical_campaigns()
    assert set(camps) == {f"toronto_{y}" for y in (2003, 2006, 2010, 2014, 2018, 2022, 2023)}
    assert sum(len(c.polls) for c in camps.values()) == 97
    c = camps["toronto_2014"]
    assert set(c.names) == {"John Tory", "Doug Ford", "Olivia Chow"}
    assert c.election_date == date(2014, 10, 27)
    assert sum(c.outcome_shares) == pytest.approx(1.0)
    assert c.outcome_tail == pytest.approx(0.029, abs=0.003)
    ipsos = next(p for p in c.polls if p.group == "ipsos_city_2014_09_12_16_n596")
    got = {c.names[i]: s for i, s in zip(ipsos.offered, ipsos.shares)}
    assert got["John Tory"] == pytest.approx(0.43, abs=0.01)
    assert ipsos.days_before_election == (date(2014, 10, 27) - date(2014, 9, 14)).days
    for camp in camps.values():
        assert len({p.group for p in camp.polls}) == len(camp.polls)
        assert all(len(p.offered) >= 2 and p.n_eff > 0 for p in camp.polls)


def _bundle_inputs(tmp_path: Path) -> tuple[Path, Path]:
    """A polling-bundle directory (samples, readings, responses) and the certified field."""
    candidates = tmp_path / "mayoral_candidates.json"
    candidates.write_text(
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
                ],
            }
        )
    )
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
                "candidate_id": key if key not in {"other", "undecided", "would_not_vote"} else "",
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
        ["poll_reading_id", "response_kind", "candidate_id", "candidate_name", "share"],
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
    return polling, candidates


def test_current_campaign_selects_one_reading_per_sample_by_denominator_rank(
    tmp_path: Path,
) -> None:
    polling, candidates = _bundle_inputs(tmp_path)
    c = current_campaign(polling, candidates, election_date=ELECTION_2026)
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
        polling, candidates, election_date=ELECTION_2026, require_full_field=False
    )
    assert [p.group for p in wide.polls][0] == "liaison-2026-07-26"
    assert wide.polls[0].offered == (0, 1)
    assert wide.polls[0].n_eff == pytest.approx(805 * 0.90)
    assert len(wide.polls) == 4


def test_current_campaign_can_name_minor_candidates(tmp_path: Path) -> None:
    polling, candidates = _bundle_inputs(tmp_path)
    c = current_campaign(
        polling, candidates, election_date=ELECTION_2026, extra_named=EXTRA_2026[:1]
    )
    assert c.names[-1] == "Sarah McVie" and c.candidates[-1] == "per_mcvie000000000000000000000000"
    assert c.polls[-1].offered == (0, 1, 2, 3)
    assert c.polls[0].offered == (0, 1, 2)


def test_current_reading_selection_is_published_for_the_feed(tmp_path: Path) -> None:
    polling, _ = _bundle_inputs(tmp_path)
    chosen = current_reading_selection(polling)
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
