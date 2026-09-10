"""Certified mayoral ballot and canonical past-election histories."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from backend.model.council_hints import (
    CandidacyRecord,
    past_election_history,
    past_election_to_dict,
    resolve_person_id,
)
from backend.model.mayoral_candidate_ids import mayoral_candidate_id

MAYORAL_CANDIDATES_FEED_SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class MayoralRegistration:
    first_name: str
    last_name: str
    status: str
    date_nomination: str

    @property
    def display_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()


def load_registered_mayoral_candidates(
    path: str | Path,
) -> tuple[MayoralRegistration, ...]:
    with Path(path).open(newline="", encoding="utf-8") as handle:
        rows = tuple(
            MayoralRegistration(
                first_name=row["first_name"].strip(),
                last_name=row["last_name"].strip(),
                status=row["status"].strip(),
                date_nomination=row["date_nomination"].strip(),
            )
            for row in csv.DictReader(handle)
        )
    if any(not row.first_name or not row.last_name for row in rows):
        raise ValueError("mayoral registration is missing a name")
    return rows


def build_mayoral_candidates_feed(
    registrations: tuple[MayoralRegistration, ...],
    live_cycle: dict,
    officeholding: tuple[dict[str, list[CandidacyRecord]], dict[str, set[frozenset[str]]]],
) -> dict:
    certified = bool(live_cycle["field_certified"])
    feed = {
        "schema_version": MAYORAL_CANDIDATES_FEED_SCHEMA_VERSION,
        "election_cycle_id": live_cycle["election_cycle_id"],
        "ballot_certified": certified,
        "candidates": [],
    }
    if not certified:
        return feed

    history_by_person, name_variants = officeholding
    incumbent_id = live_cycle.get("incumbent_candidate_id")
    candidates: list[dict] = []
    seen_ids: set[str] = set()
    active = (row for row in registrations if row.status.lower() == "active")
    for registration in sorted(
        active, key=lambda row: (row.last_name.casefold(), row.first_name.casefold())
    ):
        candidate_id = mayoral_candidate_id(registration.first_name, registration.last_name)
        if candidate_id in seen_ids:
            raise ValueError(f"duplicate mayoral candidate id: {candidate_id}")
        seen_ids.add(candidate_id)
        person_id = resolve_person_id(
            registration.first_name, registration.last_name, name_variants
        )
        is_matched = person_id is not None and person_id in history_by_person
        elections = past_election_history(history_by_person[person_id]) if is_matched else ()
        candidates.append(
            {
                "candidate_id": candidate_id,
                "display_name": registration.display_name,
                "status": registration.status,
                "person_id": person_id if is_matched else None,
                "is_matched": is_matched,
                "is_incumbent": candidate_id == incumbent_id,
                "past_elections": [past_election_to_dict(race) for race in elections],
            }
        )
    feed["candidates"] = candidates
    return feed
