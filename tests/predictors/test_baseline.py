import importlib.util

import numpy as np

from mtah.constants import REPO_ROOT
from mtah.predictors import PREDICTORS
from mtah.predictors.baseline import nearest_player
from mtah.schema import MatchTracking


def _starter_smooth():
    spec = importlib.util.spec_from_file_location("starter_baseline",
                                                  REPO_ROOT / "starter" / "baseline.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def track(T=400, seed=0, ball_nan=0.4):
    rng = np.random.default_rng(seed)
    players = rng.uniform(0, 60, (T, 4, 2)).astype(np.float32)
    players[rng.random((T, 4)) < 0.1] = np.nan
    ball = rng.uniform(0, 60, (T, 2)).astype(np.float32)
    ball[rng.random(T) < ball_nan] = np.nan
    return MatchTracking(players, np.array([0, 0, 1, 1], np.int8), ball, ((0, T),), (105.0, 68.0))


def test_all_ball_missing():
    out = nearest_player(track(ball_nan=1.0), window=25)
    assert out.dtype == np.dtype("<U1") and (out == "D").all()


def test_parity_with_starter_smoothing():
    starter = _starter_smooth()
    t = track()
    raw = nearest_player(t, window=0)
    codes = np.select([raw == "H", raw == "A"], [starter.HOME, starter.AWAY], starter.NOBODY)
    expected = starter.smooth(codes.astype(np.int8), 25)
    np.testing.assert_array_equal(nearest_player(t, window=25), expected)


def test_registry():
    assert {"baseline25", "baseline50", "baseline125"} <= set(PREDICTORS)
