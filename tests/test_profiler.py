from data_quality.profiler import profile_table


def test_profiler_callable() -> None:
    assert callable(profile_table)
