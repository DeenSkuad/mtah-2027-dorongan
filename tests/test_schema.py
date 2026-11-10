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


def _presence(pattern):
    """players array where each (n_frames, n_players) chunk has that many tracked players."""
    import numpy as np

    T = sum(n for n, _ in pattern)
    players = np.full((T, 22, 2), np.nan, dtype=np.float32)
    t = 0
    for n, k in pattern:
        players[t:t + n, :k] = 1.0
        t += n
    return players


def test_infer_periods_splits_at_long_empty_gap():
    from mtah.schema import infer_periods

    players = _presence([(500, 0), (10000, 22), (20000, 4), (11000, 22), (300, 0)])
    assert infer_periods(players) == ((500, 10500), (30500, 41500))


def test_infer_periods_bridges_short_dropouts_and_drops_short_runs():
    from mtah.schema import infer_periods

    players = _presence([(9000, 22), (1000, 10), (9000, 22), (8000, 0), (2000, 22)])
    assert infer_periods(players) == ((0, 19000),)


def test_infer_periods_never_empty():
    from mtah.schema import infer_periods

    assert infer_periods(_presence([(100, 3)])) == ((0, 100),)
