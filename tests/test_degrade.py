import numpy as np

from mtah.degrade import DegradeConfig, degrade, load_config
from mtah.schema import MatchTracking


def synthetic(T=30_000, N=6, seed=1):
    rng = np.random.default_rng(seed)
    players = rng.uniform(0, 60, (T, N, 2)).astype(np.float32)
    ball = rng.uniform(0, 60, (T, 2)).astype(np.float32)
    ball[100:300] = np.nan  # pre-existing gap
    return MatchTracking(players, np.array([0, 0, 0, 1, 1, 1], np.int8), ball,
                         ((0, T // 2), (T // 2, T)), (105.0, 68.0))


def test_missing_fraction():
    out = degrade(synthetic(), DegradeConfig(ball_missing_frac=0.41), np.random.default_rng(0))
    assert abs(np.isnan(out.ball[:, 0]).mean() - 0.41) <= 0.02


def test_never_unhides():
    track = synthetic()
    out = degrade(track, DegradeConfig(), np.random.default_rng(0))
    assert np.isnan(out.ball[100:300]).all()


def test_deterministic():
    a = degrade(synthetic(), DegradeConfig(), np.random.default_rng(7))
    b = degrade(synthetic(), DegradeConfig(), np.random.default_rng(7))
    np.testing.assert_array_equal(a.ball, b.ball)
    np.testing.assert_array_equal(a.players, b.players)


def test_team_preserved():
    track = synthetic()
    out = degrade(track, DegradeConfig(id_switch_per_min=20.0), np.random.default_rng(0))
    for team in (0, 1):
        cols = track.team_of_slot == team
        before = np.sort(track.players[:, cols, 0], axis=1)
        after = np.sort(out.players[:, cols, 0], axis=1)
        np.testing.assert_array_equal(before, after)
    assert not np.array_equal(track.players, out.players)


def test_input_not_mutated():
    track = synthetic()
    ball = track.ball.copy()
    degrade(track, DegradeConfig(), np.random.default_rng(0))
    np.testing.assert_array_equal(track.ball, ball)


def test_load_default_config():
    assert load_config().ball_missing_frac == 0.41
