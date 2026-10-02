"""Audited historical errors and conditional named-set ward modelling (ADR 0059)."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from datetime import date
from pathlib import Path

import numpy as np

from backend.model.council_race_card import WardPollReading
from backend.model.ward_poll_model import (
    METHOD,
    cohorts,
    fit,
    logistic_normal_prediction,
    model_audit,
    summary,
)


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _base(reading: dict[str, str], key: str) -> int | None:
    return int(reading[key]) if reading[key].strip() else None


def _name(name: str) -> str:
    return " ".join(sorted(re.findall(r"[a-z]+", name.casefold())))


def historical_benchmark(corpus: Path, results: Path) -> dict:
    """Match audited named responses to official results, one sample per contest.

    The registered benchmark window is 21–45 days out, matching the current
    campaign stage. Repeated samples and alternate denominators cannot multiply
    calibration outcomes. No result-dependent sample choice or normalization.
    """
    raw = _rows(corpus)
    audit = json.loads((corpus.parent / "source_documents.json").read_text())
    docs = {d["source_document_id"]: d for d in audit["documents"]}
    for row in raw:
        doc = docs[row["source_doc_id"]]
        if (
            doc["sha256"] != row["sha256"]
            or doc["visual_qa_status"] != "passed"
            or doc["visually_reviewed_pages"] != list(range(1, doc["page_count"] + 1))
        ):
            raise ValueError(f"unaudited historical source: {row['source_doc_id']}")
    outcomes = {}
    for row in _rows(results):
        if (
            row["office_type"] == "councillor"
            and row["represented_body"] == "toronto_city_council"
            and row["election_type"] == "general"
            and row["result_status"] == "final"
        ):
            key = (
                row["election_year"],
                row["official_district_id"].removeprefix("ward-"),
                _name(row["candidate_name"]),
            )
            if key in outcomes:
                raise ValueError(f"ambiguous historical result: {key}")
            outcomes[key] = row
    samples: dict[str, list[dict[str, str]]] = {}
    for row in raw:
        samples.setdefault(row["poll_sample_id"], []).append(row)
    chosen: dict[tuple[str, str], tuple[str, list[dict[str, str]]]] = {}
    for sid, rows in samples.items():
        head = rows[0]
        for row in rows:
            if any(
                row[key] != head[key]
                for key in [
                    "year",
                    "ward",
                    "fieldwork_end",
                    "pollster",
                    "source_doc_id",
                    "reading_base",
                ]
            ):
                raise ValueError(f"inconsistent historical sample metadata: {sid}")
        if len(
            {_name(r["candidate_name"]) for r in rows if r["response_kind"] == "candidate"}
        ) != sum(r["response_kind"] == "candidate" for r in rows):
            raise ValueError(f"duplicate historical candidate: {sid}")
        total = sum(float(r["share"]) for r in rows)
        if abs(total - 1) > 0.005 * len(rows):
            raise ValueError(f"historical shares exceed rounding tolerance: {sid}")
        names = [r for r in rows if r["response_kind"] == "candidate"]
        if not names:
            raise ValueError(f"historical sample lacks named responses: {sid}")
        matched = [outcomes[(r["year"], r["ward"], _name(r["candidate_name"]))] for r in names]
        day = date.fromisoformat(matched[0]["election_date"])
        end = date.fromisoformat(head["fieldwork_end"])
        if not 21 <= (day - end).days <= 45:
            continue
        contest = (head["year"], head["ward"])
        previous = chosen.get(contest)
        if previous is None or (head["fieldwork_end"], sid) > (
            previous[1][0]["fieldwork_end"],
            previous[0],
        ):
            chosen[contest] = (sid, rows)
    errors = []
    sources = []
    for sid, rows in sorted(chosen.values()):
        for row in rows:
            if row["response_kind"] != "candidate":
                continue
            share = float(row["share"])
            if not math.isfinite(share) or not 0 <= share <= 1:
                raise ValueError(f"invalid historical share: {sid}")
            actual = outcomes[(row["year"], row["ward"], _name(row["candidate_name"]))]
            errors.append(
                {
                    "sample_id": sid,
                    "candidate_name": row["candidate_name"],
                    "poll_share": share,
                    "result_share": float(actual["vote_share"]),
                    "error": float(actual["vote_share"]) - share,
                }
            )
        sources.append(
            {
                "sample_id": sid,
                "year": int(rows[0]["year"]),
                "ward": rows[0]["ward"],
                "fieldwork_end": rows[0]["fieldwork_end"],
                "pollster": rows[0]["pollster"],
                "source_url": rows[0]["source_url"],
                "retrieved_url": rows[0]["retrieved_url"],
            }
        )
    if len(chosen) < 6:
        raise ValueError("historical ward comparison requires the six audited reference contests")
    lower, upper = min(e["error"] for e in errors), max(e["error"] for e in errors)
    sensitivity = []
    for sid, _ in sorted(chosen.values()):
        remaining = [e["error"] for e in errors if e["sample_id"] != sid]
        sensitivity.append(
            {"omitted_sample": sid, "lower": min(remaining), "upper": max(remaining)}
        )
    return {
        "method": METHOD,
        "model": model_audit(errors),
        "sample_count": len(chosen),
        "contest_count": len(chosen),
        "cycle_count": len({s["year"] for s in sources}),
        "pollster_count": len({s["pollster"] for s in sources}),
        "candidate_comparisons": len(errors),
        "lead_days_min": 21,
        "lead_days_max": 45,
        "error_lower": lower,
        "error_upper": upper,
        "corpus_sha256": hashlib.sha256(corpus.read_bytes()).hexdigest(),
        "sources": sources,
        "errors": errors,
        "leave_one_contest_out": sensitivity,
    }


def poll_contexts(
    polls: dict[str, tuple[WardPollReading, ...]], source_dir: Path, benchmark: dict
) -> dict[str, dict]:
    """Attach auditable bases and joint named-set ranges to matching final-field polls."""
    samples = {r["poll_sample_id"]: r for r in _rows(source_dir / "poll_samples.csv")}
    readings = _rows(source_dir / "poll_readings.csv")
    responses = _rows(source_dir / "poll_responses.csv")
    contexts = {}
    records = cohorts(benchmark["errors"])
    fitted = fit(records)
    alternatives = {
        "lower_concentration_prior": fit(records, prior_median=10),
        "higher_concentration_prior": fit(records, prior_median=100),
        "less_ward_heterogeneity": fit(records, tau_scale=0.5),
    }
    for ward, items in polls.items():
        for poll in items:
            if poll.ballot_status != "final_ballot_candidates":
                continue
            matches = []
            for reading in readings:
                sample = samples[reading["poll_sample_id"]]
                if (
                    sample["geography_type"] == "ward"
                    and sample["geography_id"] == f"toronto-ward-{ward}"
                    and sample["fieldwork_end"] == poll.date_conducted
                    and sample["pollster"] == poll.firm
                    and reading["contest_type"] == "council"
                ):
                    published = {
                        r["candidate_name"]: float(r["share"])
                        for r in responses
                        if r["poll_reading_id"] == reading["poll_reading_id"]
                        and r["response_kind"] == "candidate"
                    }
                    display = {
                        c.candidate_name: c.share for c in poll.candidates if not c.is_residual
                    }
                    if published == display:
                        matches.append((sample, reading))
            if len(matches) != 1:
                raise ValueError(
                    f"expected one audited council reading for {poll.poll_id}, got {len(matches)}"
                )
            sample, reading = matches[0]
            named = [c for c in poll.candidates if not c.is_residual]
            values = np.array([c.share for c in named])
            named_shares = values / values.sum()
            prediction = summary(fitted.predict(values))
            replicate = summary(fitted.predict(values, seed=20261003))
            mc_difference = max(
                abs(a - b)
                for key in ["lower", "median", "upper"]
                for a, b in zip(prediction[key], replicate[key], strict=True)
            )
            if mc_difference > 0.01:
                raise ValueError("ward predictive quantiles are not numerically stable")
            sensitivities = {
                key: summary(alternative.predict(values))
                for key, alternative in alternatives.items()
            }
            sensitivities["logistic_normal_shape"] = summary(
                logistic_normal_prediction(records, values)
            )
            bands = [
                {
                    "candidate_id": c.candidate_id,
                    "candidate_name": c.candidate_name,
                    "reported_share": c.share,
                    "named_share": float(named_shares[index]),
                    "median": prediction["median"][index],
                    "lower": prediction["lower"][index],
                    "upper": prediction["upper"][index],
                }
                for index, c in enumerate(named)
            ]
            contexts[poll.poll_id] = {
                "reading_id": reading["poll_reading_id"],
                "sample_id": sample["poll_sample_id"],
                "unweighted_base": _base(reading, "unweighted_base"),
                "weighted_base": _base(reading, "weighted_base"),
                "reported_base": _base(reading, "reported_base"),
                "denominator": "named_candidates",
                "interval_mass": 0.8,
                "rows": bands,
                "sensitivity": sensitivities,
                "quantile_replication_max_difference": mc_difference,
            }
    return contexts
