"""HUMAN-RUN ONLY (rule R1): `pytest -m match`. Failures never print data values."""

import pytest

from mtah.constants import N_MATCH_FRAMES


@pytest.mark.match
def test_load_match_shape():
    from mtah.io.match import load_match

    track = load_match()
    track.validate()
    # pytest.fail instead of assert: assertion rewriting would print the actual values.
    if track.n_frames() != N_MATCH_FRAMES:
        pytest.fail("frame count differs from the submission contract", pytrace=False)
    if track.team_of_slot.size != 46:
        pytest.fail("unexpected number of track slots", pytrace=False)


@pytest.mark.match
def test_match_has_two_inferred_halves():
    from mtah.io.match import load_match

    if len(load_match().periods) != 2:
        pytest.fail("inferred period count is not 2", pytrace=False)
