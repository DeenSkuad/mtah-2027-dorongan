from mtah.report import coverage


def test_coverage_counts_graded_frames_outside_periods():
    # graded blocks are inclusive (first, last); periods are half-open [start, stop)
    line = coverage(periods=((10, 50), (70, 100)), n_frames=100, graded=((20, 59), (80, 89)))
    assert line == ("inferred periods: 2, covering 70% of frames; "
                    "graded frames outside periods: 10 of 50 (labelled D)")


def test_coverage_all_inside():
    line = coverage(periods=((0, 100),), n_frames=100, graded=((0, 99),))
    assert line.endswith("graded frames outside periods: 0 of 100 (labelled D)")
