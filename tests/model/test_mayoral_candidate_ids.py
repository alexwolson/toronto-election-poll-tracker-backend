from backend.model.mayoral_candidate_ids import mayoral_candidate_id


def test_major_candidates_keep_poll_compatible_ids() -> None:
    assert mayoral_candidate_id("Olivia", "Chow") == "chow"
    assert mayoral_candidate_id("Brad", "Bradford") == "bradford"
    assert mayoral_candidate_id("Chris", "Alexander") == "alexander"


def test_minor_candidate_ids_are_normalized_name_slugs() -> None:
    assert mayoral_candidate_id("José María", "Núñez") == "jose-maria-nunez"
    assert (
        mayoral_candidate_id("  Odessa Paloma ", " Parker ") == "odessa-paloma-parker"
    )
