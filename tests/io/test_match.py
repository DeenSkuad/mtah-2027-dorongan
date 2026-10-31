"""HUMAN-RUN ONLY (rule R1): `pytest -m match`. Assertions never print data values."""

import pytest

from mtah.constants import N_MATCH_FRAMES


@pytest.mark.match
def test_load_match_shape():
    from mtah.io.match import load_match

    track = load_match()
    track.validate()
    assert track.n_frames() == N_MATCH_FRAMES, "frame count differs from the submission contract"
    assert track.team_of_slot.size == 46, "unexpected number of track slots"
