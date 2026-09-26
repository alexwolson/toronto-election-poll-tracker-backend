from pathlib import Path

from backend.model.council_endorsements import load_endorsements

ENDORSERS = (
    "endorser_id,canonical_name,endorser_type,person_id,is_panel_endorser,panel_basis,"
    "eligibility_start_date,mayor_applicable,councillor_applicable,panel_evidence_url\n"
    "edr_pt,Progress Toronto,organization,,true,x,,true,true,\n"
    "edr_star,Toronto Star Editorial Board,editorial_board,,true,x,,true,true,\n"
)
ENDORSEMENTS = (
    "endorsement_id,endorser_id,contest_id,candidacy_id\n"
    "end_1,edr_pt,con_w5,can_padovani\n"
    "end_2,edr_star,con_w5,can_padovani\n"
    "end_3,edr_pt,con_w4,can_mcnally\n"
)
ASSERTIONS = (
    "assertion_id,endorsement_id,endorser_id,contest_id,candidacy_id,review_state,endorsement_kind,"
    "announcement_date,date_precision,source_type,source_url,secondary_source_url,"
    "asserted_candidate_name,curation_key\n"
    "asr_1,end_1,edr_pt,con_w5,can_padovani,confirmed,progressive_champion,,unknown,"
    "first_party_slate,https://pt.example/champions,,Chiara Padovani,k1\n"
    "asr_2,end_2,edr_star,con_w5,can_padovani,confirmed,editorial_choice,2026-10-17,day,"
    "publisher_editorial,https://star.example/ed,,Chiara Padovani,k2\n"
    "asr_3,end_3,edr_pt,con_w4,can_mcnally,confirmed,progressive_champion,,unknown,"
    "first_party_slate,https://pt.example/champions,,Diana Chan McNally,k3\n"
    "asr_4,,edr_pt,con_w9,,unresolved,progressive_champion,,unknown,"
    "first_party_slate,https://pt.example/champions,,Someone Unmatched,k4\n"
)


def _write(tmp_path: Path) -> Path:
    (tmp_path / "endorsers.csv").write_text(ENDORSERS)
    (tmp_path / "endorsements.csv").write_text(ENDORSEMENTS)
    (tmp_path / "endorsement_assertions.csv").write_text(ASSERTIONS)
    return tmp_path


def test_confirmed_endorsements_are_grouped_by_candidacy_with_their_source(tmp_path: Path) -> None:
    facts = load_endorsements(_write(tmp_path))
    assert set(facts) == {"can_padovani", "can_mcnally"}
    assert [e["endorser_name"] for e in facts["can_padovani"]] == [
        "Progress Toronto",
        "Toronto Star Editorial Board",
    ]
    progress = facts["can_padovani"][0]
    assert progress == {
        "endorser_id": "edr_pt",
        "endorser_name": "Progress Toronto",
        "endorser_type": "organization",
        "kind": "progressive_champion",
        "announced": None,
        "date_precision": "unknown",
        "source_url": "https://pt.example/champions",
    }
    assert facts["can_padovani"][1]["announced"] == "2026-10-17"


def test_missing_tables_mean_no_endorsements(tmp_path: Path) -> None:
    assert load_endorsements(tmp_path) == {}
