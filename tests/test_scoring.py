from data_quality.scoring import confidence_from_profile


def test_scoring_returns_label() -> None:
    score = confidence_from_profile({"row_count": 10, "missing_values": {"a": 0}, "duplicate_groups": 0})
    assert score in {"High", "Medium", "Low"}
