import csv
import json
import subprocess
import sys
from pathlib import Path

import pytest

from backend.analysis.endorsement_scenarios import build_analysis, calculate_scenario

BASELINE = {"chow": 50.0, "bradford": 39.0, "alexander": 8.0, "residual": 3.0}


def test_six_points_from_chow_puts_bradford_one_point_ahead():
    result = calculate_scenario(BASELINE, "bradford", 6, chow_fraction=1)

    assert result["shares"] == pytest.approx(
        {"chow": 44, "bradford": 45, "alexander": 8, "residual": 3}
    )
    assert result["recipient_margin_pp"] == pytest.approx(1)
    assert result["leaders"] == ["bradford"]


def test_nine_points_cannot_come_from_an_eight_point_donor():
    result = calculate_scenario(BASELINE, "bradford", 9, chow_fraction=0)

    assert result["feasible"] is False
    assert result["shares"] is None
    assert "Chris Alexander" in result["reason"]
    assert result["max_gain_pp"] == 8


@pytest.mark.parametrize(
    ("recipient", "chow_fraction", "required", "reachable"),
    [
        ("bradford", 1, 5.5, True),
        ("bradford", 0, 11, False),
        ("alexander", 1, 31, True),
        ("alexander", 0, 42, False),
    ],
)
def test_tie_threshold_accounts_for_all_opponents_and_available_support(
    recipient, chow_fraction, required, reachable
):
    result = calculate_scenario(BASELINE, recipient, 0, chow_fraction=chow_fraction)

    assert result["tie_gain_pp"] == pytest.approx(required)
    assert result["tie_reachable"] is reachable


def test_adverse_effect_reverses_flows_and_applies_explicit_retention():
    result = calculate_scenario(BASELINE, "bradford", -3, chow_fraction=0.5, retained_fraction=0.5)

    assert result["shares"] == pytest.approx(
        {"chow": 50.75, "bradford": 37.5, "alexander": 8.75, "residual": 3}
    )
    assert result["realized_effect_pp"] == -1.5
    assert BASELINE["bradford"] == 39


@pytest.mark.parametrize(
    "kwargs",
    [
        {"effect_pp": float("nan")},
        {"effect_pp": float("inf")},
        {"recipient": "chow"},
        {"chow_fraction": -0.1},
        {"chow_fraction": 1.1},
        {"retained_fraction": -0.1},
        {"retained_fraction": 1.1},
        {"baseline": {**BASELINE, "chow": 51}},
        {"baseline": {**BASELINE, "residual": float("nan")}},
    ],
)
def test_invalid_assumptions_are_rejected(kwargs):
    args = {"baseline": BASELINE, "recipient": "bradford", "effect_pp": 3, "chow_fraction": 0.5}
    args.update(kwargs)
    with pytest.raises(ValueError):
        calculate_scenario(**args)


def test_report_preserves_published_readings_and_discloses_rounding():
    report = build_analysis(Path(__file__).resolve().parents[2])
    pallas, liaison = report["baselines"]

    assert pallas["reported_shares"] == {
        "chow": 50.1,
        "bradford": 39.3,
        "alexander": 8.1,
        "residual": 2.6,
    }
    assert pallas["reported_total"] == 100.1
    assert liaison["reported_total"] == 101
    assert sum(pallas["shares"].values()) == pytest.approx(100)
    assert pallas["shares"]["chow"] == pytest.approx(50.04995004995)
    assert pallas["fieldwork_start"] == "2026-08-19"
    assert pallas["fieldwork_end"] == "2026-08-21"
    assert pallas["reading_id"] == "pallas_20260819_21_mayor_decided_leaning"
    assert all(len(value) == 64 for value in report["input_sha256"].values())
    assert len(report["scenarios"]) == 360


def test_command_exports_a_reproducible_grid_with_impossible_cases_explicit(tmp_path):
    root = Path(__file__).resolve().parents[2]
    completed = subprocess.run(
        [
            sys.executable,
            str(root / "scripts/analyze_tory_endorsement.py"),
            "--output-dir",
            str(tmp_path),
        ],
        cwd=root,
        check=False,
        text=True,
        capture_output=True,
    )
    assert completed.returncode == 0, completed.stderr
    report = json.loads((tmp_path / "scenarios.json").read_text())
    assert len(report["scenarios"]) == 360
    with (tmp_path / "scenarios.csv").open() as file:
        rows = list(csv.DictReader(file))
    row = next(
        row
        for row in rows
        if row["baseline_id"] == "pallas-2026-08-21"
        and row["recipient"] == "bradford"
        and row["effect_pp"] == "9"
        and row["flow_id"] == "challenger"
        and row["event_date"] == "2026-10-21"
        and row["retained_fraction"] == "1"
    )
    assert row["feasible"] == "False"
    assert row["bradford"] == ""
    assert "Chris Alexander" in row["reason"]
    html = (tmp_path / "index.html").read_text()
    assert "@@DATA@@" not in html
    assert 'id="scenario-data"' in html
    assert "Conditional scenario" in html
    assert (tmp_path / "README.md").is_file()
