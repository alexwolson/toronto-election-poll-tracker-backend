import csv
import shutil
from dataclasses import replace
from pathlib import Path

import pytest

from backend.model.council_race_card import WardPollCandidateReading, WardPollReading
from backend.model.ward_poll_context import historical_benchmark, poll_contexts

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "data/raw/polls/historical_council/poll_responses.csv"
RESULTS = ROOT / "data/raw/canonical/election_results.csv"


def test_audited_historical_errors_keep_candidate_identity_and_source_rounding():
    b = historical_benchmark(CORPUS, RESULTS)
    assert (b["sample_count"], b["contest_count"], b["cycle_count"], b["pollster_count"]) == (
        6,
        6,
        1,
        1,
    )
    assert b["candidate_comparisons"] == 26
    assert b["error_lower"] == pytest.approx(-0.16521877486077963)
    assert b["error_upper"] == pytest.approx(0.2556404136833731)
    lhamo = next(e for e in b["errors"] if e["candidate_name"] == "Chemi Lhamo")
    assert lhamo["poll_share"] == 0.06
    assert lhamo["result_share"] == pytest.approx(0.3156404136833731)
    assert len(b["leave_one_contest_out"]) == 6
    assert all(
        s["lower"] >= b["error_lower"] and s["upper"] <= b["error_upper"]
        for s in b["leave_one_contest_out"]
    )


def test_repeated_samples_stay_in_one_contest_and_latest_eligible_is_selected(tmp_path):
    with CORPUS.open(newline="") as handle:
        reader = csv.DictReader(handle)
        rows, fields = list(reader), reader.fieldnames
    extra = [
        dict(row, poll_sample_id="repeat", fieldwork_end="2022-09-20")
        for row in rows
        if row["ward"] == "4"
    ]
    shutil.copy2(CORPUS.parent / "source_documents.json", tmp_path / "source_documents.json")
    path = tmp_path / "corpus.csv"
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows + extra)
    b = historical_benchmark(path, RESULTS)
    assert b["contest_count"] == 6
    assert sum(s["ward"] == "4" for s in b["sources"]) == 1
    assert next(s for s in b["sources"] if s["ward"] == "4")["sample_id"] == "repeat"
    assert b["candidate_comparisons"] == 26


def _csv(path, rows):
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def test_source_bases_and_published_shares_are_preserved_without_other_allocation(tmp_path):
    _csv(
        tmp_path / "poll_samples.csv",
        [
            {
                "poll_sample_id": "s",
                "geography_type": "ward",
                "geography_id": "toronto-ward-4",
                "fieldwork_end": "2026-09-27",
                "pollster": "Forum Research",
            }
        ],
    )
    _csv(
        tmp_path / "poll_readings.csv",
        [
            {
                "poll_sample_id": "s",
                "poll_reading_id": "r",
                "contest_type": "council",
                "unweighted_base": "307",
                "weighted_base": "331",
                "reported_base": "",
            }
        ],
    )
    _csv(
        tmp_path / "poll_responses.csv",
        [
            {
                "poll_reading_id": "r",
                "candidate_name": "Candidate",
                "response_kind": "candidate",
                "share": "0.06",
            },
            {
                "poll_reading_id": "r",
                "candidate_name": "",
                "response_kind": "other",
                "share": "0.94",
            },
        ],
    )
    poll = WardPollReading(
        "4",
        "p",
        "Forum Research",
        "2026-09-27",
        "2026-10-02",
        464,
        "mixed",
        "decided/leaning",
        "final_ballot_candidates",
        None,
        (
            WardPollCandidateReading("a", "Candidate", 0.06, False, False, "registered"),
            WardPollCandidateReading("other", "Other", 0.94, False, True, "residual"),
        ),
    )
    b = {"error_lower": -0.16521877486077963, "error_upper": 0.2556404136833731}
    c = poll_contexts({"4": (poll,)}, tmp_path, b)["p"]
    assert c["unweighted_base"] == 307 and c["weighted_base"] == 331
    assert c["reported_base"] is None
    assert len(c["rows"]) == 1
    assert c["rows"][0]["reported_share"] == 0.06
    assert c["rows"][0]["lower"] == 0
    assert c["rows"][0]["upper"] == pytest.approx(0.3156404136833731)
    assert (
        poll_contexts(
            {"4": (replace(poll, ballot_status="different_candidate_field"),)}, tmp_path, b
        )
        == {}
    )
    with pytest.raises(ValueError, match="expected one audited council reading"):
        poll_contexts({"4": (replace(poll, date_conducted="2026-09-26"),)}, tmp_path, b)
