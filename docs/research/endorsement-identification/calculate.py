"""Reproduce descriptive endorsement checks; no causal coefficient is fitted.

Run with Python containing pandas/openpyxl:
    python calculate.py /path/to/toronto-election-results

Reads the upstream corpus and writes results.json beside this script. No workbook,
canonical data, or forecast is modified. The pretrend inputs are transcribed from
the primary sources cited in the accompanying memo.
"""

from __future__ import annotations

import csv
import hashlib
import json
import statistics
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

EVENT = datetime(2023, 6, 21)
SERIES = {
    "Forum": {
        "dates": ["2023-05-26", "2023-06-02", "2023-06-09", "2023-06-16"],
        "shares": [9, 8, 10, 13],
        "post_start": "2023-06-23",
        "post_end": "2023-06-23",
        "post_share": 20,
    },
    "Liaison": {
        "dates": ["2023-05-26", "2023-06-03", "2023-06-10", "2023-06-12", "2023-06-17"],
        "ends": ["2023-05-27", "2023-06-04", "2023-06-11", "2023-06-13", "2023-06-18"],
        "shares": [10, 9, 10, 11, 12],
        "post_start": "2023-06-22",
        "post_end": "2023-06-23",
        "post_share": 17,
    },
}


def midpoint(start, end):
    a, b = (datetime.fromisoformat(value) for value in (start, end))
    return ((a + (b - a) / 2) - EVENT).total_seconds() / 86400


def pretrends():
    results = []
    for firm, data in SERIES.items():
        points = list(
            zip(
                [
                    midpoint(a, b)
                    for a, b in zip(data["dates"], data.get("ends", data["dates"]), strict=True)
                ],
                data["shares"],
                strict=True,
            )
        )
        post = midpoint(data["post_start"], data["post_end"])
        for window in (14, 21, 28):
            before = [(x, y) for x, y in points if -window <= x < 0]
            slope, intercept = statistics.linear_regression(*zip(*before, strict=True))
            projected = intercept + slope * post
            results.append(
                {
                    "firm": firm,
                    "window_days": window,
                    "n_polls": len(before),
                    "slope_pp_per_day": slope,
                    "projected_share": projected,
                    "observed_share": data["post_share"],
                    "excess_pp": data["post_share"] - projected,
                }
            )
    # Independent hand-worked check: 10→13 in seven days projects 16 after seven more.
    assert results[0]["projected_share"] == 16
    return results


def council_modes(root):
    paths = {}

    def read(name):
        path = root / "data/out" / f"{name}.csv"
        paths[name] = path
        with path.open() as file:
            return list(csv.DictReader(file))

    outcomes, endorsements, endorsers = (
        read(n) for n in ("election_results", "endorsements", "endorsers")
    )
    ids = {r["canonical_name"]: r["endorser_id"] for r in endorsers}
    endorsed = {
        name: {r["candidacy_id"] for r in endorsements if r["endorser_id"] == ids[name]}
        for name in ("Toronto Star Editorial Board", "John Tory")
    }
    lookup = {}
    for row in outcomes:
        if row["election_year"] == "2022" and row["office_type"] == "councillor":
            key = (row["official_district_id"], row["candidate_name_raw"])
            assert key not in lookup, key
            lookup[key] = row

    path = root / "data/raw/results/extracted/2022/2022_Toronto_Poll_By_Poll_Councillor.xlsx"
    paths["official_2022_council_workbook"] = path
    records = []
    with pd.ExcelFile(path) as book:
        for sheet in book.sheet_names:
            raw = book.parse(sheet, header=None)
            ward = int(sheet.split()[-1])
            header = raw.iloc[1]
            assert header.iloc[0] == "Subdivision"
            columns = {
                int(value): col
                for col, value in header.items()
                if col and pd.notna(pd.to_numeric(value, errors="coerce"))
            }
            assert {97, 98, 99}.issubset(columns)
            total_col = next(col for col, value in header.items() if value == "Total")
            ward_records = []
            for index in range(3, len(raw) - 1):
                source = lookup[(f"ward-{ward}", raw.iloc[index, 0])]
                totals = {"advance": 0, "mail": 0, "election_day": 0}
                for sub, col in columns.items():
                    value = raw.iloc[index, col]
                    assert pd.notna(value) and value >= 0 and value == int(value)
                    mode = "advance" if sub in (98, 99) else "mail" if sub == 97 else "election_day"
                    totals[mode] += int(value)
                assert (
                    sum(totals.values()) == int(raw.iloc[index, total_col]) == int(source["votes"])
                )
                ward_records.append(
                    {
                        "candidacy_id": source["candidacy_id"],
                        "candidate": source["candidate_name"],
                        "ward": ward,
                        "incumbent": source["incumbent"],
                        "star": source["candidacy_id"] in endorsed["Toronto Star Editorial Board"],
                        "recorded_tory": source["candidacy_id"] in endorsed["John Tory"],
                        "comparator_exclusion": (
                            "Ward 23: Cynthia Lai died October 21; her votes were excluded "
                            "from official totals, including advance ballots cast before her death."
                            if ward == 23
                            else None
                        ),
                        **totals,
                    }
                )
            for mode in ("advance", "mail", "election_day"):
                denominator = sum(r[mode] for r in ward_records)
                assert denominator > 0
                for row in ward_records:
                    row[mode + "_denominator"] = denominator
                    row[mode + "_share"] = row[mode] / denominator * 100
            for row in ward_records:
                row["difference_pp"] = row["election_day_share"] - row["advance_share"]
            records.extend(ward_records)
    assert len(records) == len(lookup)
    selected = [r for r in records if r["star"]]
    assert len(selected) == 22
    summaries = []
    for name, subset in (
        ("All Star council recipients", selected),
        ("Excluding Ward 23 ballot-field change", [r for r in selected if r["ward"] != 23]),
        ("Incumbents", [r for r in selected if r["incumbent"] == "True"]),
        ("Nonincumbents", [r for r in selected if r["incumbent"] == "False"]),
        (
            "Nonincumbents excluding Ward 23",
            [r for r in selected if r["incumbent"] == "False" and r["ward"] != 23],
        ),
        ("Also recorded as Tory endorsed", [r for r in selected if r["recorded_tory"]]),
        ("No recorded Tory endorsement", [r for r in selected if not r["recorded_tory"]]),
    ):
        values = [r["difference_pp"] for r in subset]
        summaries.append(
            {
                "group": name,
                "n": len(values),
                "mean_pp": statistics.mean(values),
                "median_pp": statistics.median(values),
                "min_pp": min(values),
                "max_pp": max(values),
                "positive": sum(value > 0 for value in values),
            }
        )
    provenance = {
        name: {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        for name, path in paths.items()
    }
    return records, summaries, provenance


if __name__ == "__main__":
    root = Path(sys.argv[1]).resolve()
    records, summaries, provenance = council_modes(root)
    report = {
        "interpretation": (
            "Descriptive pretrend residuals and voting-mode contrasts, not causal effects."
        ),
        "pretrend_inputs": SERIES,
        "pretrends": pretrends(),
        "council_records": records,
        "council_summaries": summaries,
        "provenance": provenance,
    }
    Path(__file__).with_name("results.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    )
    print(json.dumps({"pretrends": report["pretrends"], "council_summaries": summaries}, indent=2))
