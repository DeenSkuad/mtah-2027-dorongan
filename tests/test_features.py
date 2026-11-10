import warnings

import numpy as np
import pytest

from mtah.features import FEATURE_NAMES, frame_features
from mtah.schema import MatchTracking

PITCH = (105.0, 68.0)


def col(features, name):
    return features[:, FEATURE_NAMES.index(name)]


def make_track(period_len=(300, 300), flip_second=False, ball=None):
    """2 home + 2 away + 1 referee. Home left, away right (swapped in period 2 if flip_second).
    The ball sits next to home player 0, who jogs along y."""
    T = sum(period_len)
    players = np.full((T, 5, 2), np.nan, dtype=np.float32)
    t = np.arange(T)
    jog = 20 + 0.05 * (t % 200)
    left, right = 30.0, 75.0
    for start, stop, flipped in ((0, period_len[0], False),
                                 (period_len[0], T, flip_second)):
        home_x, away_x = (right, left) if flipped else (left, right)
        sl = slice(start, stop)
        players[sl, 0] = np.c_[np.full(stop - start, home_x), jog[sl]]
        players[sl, 1] = np.c_[np.full(stop - start, home_x - 5), np.full(stop - start, 40)]
        players[sl, 2] = np.c_[np.full(stop - start, away_x), np.full(stop - start, 30)]
        players[sl, 3] = np.c_[np.full(stop - start, away_x + 5), np.full(stop - start, 50)]
    players[:, 4] = (52.0, 34.0)
    if ball is None:
        ball = players[:, 0] + np.float32(0.5)
    team = np.array([0, 0, 1, 1, -1], dtype=np.int8)
    periods = ((0, period_len[0]), (period_len[0], T))
    return MatchTracking(players, team, ball.astype(np.float32), periods, PITCH, 25)


def test_shape_and_names():
    features = frame_features(make_track())
    assert features.shape == (600, len(FEATURE_NAMES))
    assert features.dtype == np.float32
    assert len(set(FEATURE_NAMES)) == len(FEATURE_NAMES)


def test_ball_owner_side():
    features = frame_features(make_track())
    assert (col(features, "d_diff") < 0).all()
    assert (col(features, "n_home3") >= 1).all()
    assert (col(features, "last_side") < 0).all()


def test_direction_mirrored():
    features = frame_features(make_track(flip_second=True))
    assert (col(features, "cx_gap") > 0).all()


def test_ball_out_positive_outside():
    track = make_track()
    ball = track.ball.copy()
    ball[10] = (-2.0, 30.0)
    features = frame_features(MatchTracking(track.players, track.team_of_slot, ball,
                                            track.periods, PITCH, 25))
    assert col(features, "ball_out")[10] == pytest.approx(2.0)
    assert col(features, "ball_out")[11] == 0


def test_missing_ball_period_is_nan_safe():
    track = make_track()
    ball = track.ball.copy()
    ball[300:] = np.nan
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        features = frame_features(MatchTracking(track.players, track.team_of_slot, ball,
                                                track.periods, PITCH, 25))
    assert (col(features, "ball_seen")[300:] == 0).all()
    assert np.isnan(col(features, "d_diff")[300:]).all()
    assert np.isnan(col(features, "last_side")[300:]).all()  # never carried into period 2
    assert (col(features, "since_seen")[300:] == 250).all()


def test_short_period():
    features = frame_features(make_track(period_len=(300, 10)))
    assert np.isfinite(col(features, "v_home_m125")[-10:]).all()


def test_slot_permutation_and_referee_invariant():
    track = make_track()
    order = np.array([3, 4, 1, 0, 2])
    extra = np.full((track.n_frames(), 1, 2), np.nan, dtype=np.float32)
    permuted = MatchTracking(np.concatenate([track.players[:, order], extra], axis=1),
                             np.append(track.team_of_slot[order], -1).astype(np.int8),
                             track.ball, track.periods, PITCH, 25)
    np.testing.assert_array_equal(frame_features(track), frame_features(permuted))


def test_empty_frames():
    track = make_track()
    players = track.players.copy()
    players[50:60] = np.nan
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        features = frame_features(MatchTracking(players, track.team_of_slot, track.ball,
                                                track.periods, PITCH, 25))
    assert (col(features, "n_tracked")[50:60] == 0).all()
    assert np.isnan(col(features, "cx_home")[50:60]).all()
    assert np.isnan(col(features, "d_home")[50:60]).all()
