import numpy as np
import pytest

from mtah.schema import MatchTracking


def make(T=100, N=4, periods=((0, 50), (50, 100))):
    return MatchTracking(
        players=np.zeros((T, N, 2), np.float32),
        team_of_slot=np.array([0, 0, 1, 1], np.int8)[:N],
        ball=np.zeros((T, 2), np.float32),
        periods=periods,
        pitch=(105.0, 68.0),
    )


def test_validate_ok():
    track = make()
    track.validate()
    assert track.n_frames() == 100


@pytest.mark.parametrize("kwargs", [
    {"ball": np.zeros((99, 2), np.float32)},
    {"team_of_slot": np.array([0, 1, 1], np.int8)},
    {"periods": ((0, 60), (50, 100))},
    {"periods": ((0, 101),)},
])
def test_validate_rejects(kwargs):
    base = make()
    fields = {f: getattr(base, f) for f in ("players", "team_of_slot", "ball", "periods", "pitch")}
    fields.update(kwargs)
    with pytest.raises(ValueError):
        MatchTracking(**fields).validate()
