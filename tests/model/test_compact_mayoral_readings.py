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
    historical_campaigns,
    with_horizon,
)

ELECTION_2026 = date(2026, 10, 26)
CHOW = "per_chow0000000000000000000000000"
BRAD = "per_brad0000000000000000000000000"
ALEX = "per_alex0000000000000000000000000"


def test_tracked_classification_table_covers_every_register_reading() -> None:
    rows = list(csv.DictReader(CLASSIFICATION.open(encoding="utf-8")))
    assert len(rows) == 332
    assert {r["measurement_class"] for r in rows} >= {
        "campaign_vote_intention",
        "alternative_ballot",
    }
    provenance = json.loads(CLASSIFICATION.with_suffix(".provenance.json").read_text())
    assert provenance["rows"] == 332 and len(provenance["source_sha256"]) == 64


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


def _release_inputs(tmp_path: Path) -> tuple[Path, Path]:
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
    polls = tmp_path / "polls.csv"
    polls.write_text(
        "poll_id,firm,date_conducted,sample_size,field_tested,alexander,bradford,chow,other,sarah-mcvie\n"
        'mainstreet-2026-09-14,Mainstreet Research,2026-09-17,1000,"alexander,bradford,chow,other,sarah-mcvie",0.096,0.377,0.458,0.024,0.025\n'
        'liaison-2026-09-05,Liaison Strategies,2026-09-05,1000,"alexander,bradford,chow,other",0.10,0.39,0.50,0.02,\n'
        'liaison-2026-07-26,Liaison Strategies,2026-07-26,1000,"bradford,chow,other",,0.41,0.49,0.10,\n'
    )
    return polls, candidates


def test_current_campaign_uses_certified_field_polls_from_the_release(tmp_path: Path) -> None:
    polls, candidates = _release_inputs(tmp_path)
    c = current_campaign(polls, candidates, election_date=ELECTION_2026)
    assert c.key == "toronto-2026"
    assert c.candidates == (CHOW, BRAD, ALEX)
    assert c.names == ("Olivia Chow", "Brad Bradford", "Chris Alexander")
    assert [p.reading_id for p in c.polls] == ["liaison-2026-09-05", "mainstreet-2026-09-14"]
    ms = c.polls[-1]
    named = 0.458 + 0.377 + 0.096
    assert ms.shares == pytest.approx((0.458 / named, 0.377 / named, 0.096 / named))
    assert ms.n_eff == pytest.approx(1000 * named)
    assert ms.days_before_election == (ELECTION_2026 - date(2026, 9, 17)).days
    assert c.outcome_shares is None and c.leaders == (0, 1)
    wide = current_campaign(
        polls, candidates, election_date=ELECTION_2026, require_full_field=False
    )
    assert len(wide.polls) == 3


def test_current_campaign_can_name_minor_candidates(tmp_path: Path) -> None:
    polls, candidates = _release_inputs(tmp_path)
    c = current_campaign(polls, candidates, election_date=ELECTION_2026, extra_named=EXTRA_2026[:1])
    assert c.names[-1] == "Sarah McVie" and c.candidates[-1] == "per_mcvie000000000000000000000000"
    assert c.polls[-1].offered == (0, 1, 2, 3)
    assert c.polls[0].offered == (0, 1, 2)


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
