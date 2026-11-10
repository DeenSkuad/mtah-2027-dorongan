"""Per-frame features for the learned predictor: MatchTracking -> (T, F) float32, NaN allowed.

Every feature is a team aggregate (nearest, count, mean), so nothing depends on slot order or
slot count; slots with team -1 are ignored. x is mirrored per period so home always attacks +x.
Nothing carries across a period boundary.
"""

import numpy as np

from mtah.schema import MatchTracking

CAP = 250  # frames, for since_seen / until_seen
NEAR = 3.0  # metres, for n_home3 / n_away3
BALL_SPEED_MAX, PLAYER_SPEED_MAX, SLOW = 40.0, 12.0, 1.0  # m/s
WINDOWS = (25, 125)
ROLLED = ("ball_seen", "ball_speed", "d_diff", "v_home", "v_away", "slow_frac", "ball_out")

BASE_NAMES = ("ball_seen", "ball_x", "ball_y", "ball_speed", "ball_out", "since_seen",
              "until_seen", "d_home", "d_away", "d_diff", "n_home3", "n_away3", "cx_home",
              "cx_away", "cx_gap", "v_home", "v_away", "slow_frac", "n_tracked", "last_side")
FEATURE_NAMES = BASE_NAMES + tuple(f"{f}_m{w}" for w in WINDOWS for f in ROLLED)


def _ratio(num: np.ndarray, den: np.ndarray) -> np.ndarray:
    out = np.full(num.shape, np.nan)
    np.divide(num, den, out=out, where=den > 0)
    return out


def _sorted_sum(values: np.ndarray) -> np.ndarray:
    """Row sums with NaN as 0, added in sorted order so the result ignores slot order."""
    return np.sort(np.nan_to_num(values, nan=0.0), axis=1).sum(axis=1)


def _team_mean(values: np.ndarray, in_team: np.ndarray) -> np.ndarray:
    v = np.where(in_team[None, :], values, np.nan)
    return _ratio(_sorted_sum(v), np.isfinite(v).sum(axis=1))


def _step(xy: np.ndarray, fps: int) -> np.ndarray:
    """Speed between consecutive frames (m/s); NaN on the first frame. xy is (T, ..., 2)."""
    speed = np.full(xy.shape[:-1], np.nan)
    speed[1:] = np.linalg.norm(np.diff(xy, axis=0), axis=-1) * fps
    return speed


def _since(seen: np.ndarray) -> np.ndarray:
    index = np.arange(len(seen))
    last = np.maximum.accumulate(np.where(seen, index, -1))
    return np.where(last >= 0, np.minimum(index - last, CAP), CAP)


def _forward_fill(values: np.ndarray, valid: np.ndarray) -> np.ndarray:
    index = np.maximum.accumulate(np.where(valid, np.arange(len(values)), -1))
    return np.where(index >= 0, values[np.maximum(index, 0)], np.nan)


def _rolling_mean(values: np.ndarray, window: int) -> np.ndarray:
    finite = np.isfinite(values)
    total = np.concatenate(([0.0], np.cumsum(np.where(finite, values, 0.0))))
    count = np.concatenate(([0], np.cumsum(finite)))
    index = np.arange(len(values))
    low = np.maximum(0, index - window)
    high = np.minimum(len(values), index + window + 1)
    return _ratio(total[high] - total[low], count[high] - count[low])


def _period_features(players: np.ndarray, team: np.ndarray, ball: np.ndarray,
                     pitch: tuple[float, float], fps: int) -> dict[str, np.ndarray]:
    length, width = pitch
    home, away = team == 0, team == 1
    px = players[:, :, 0]
    with np.errstate(all="ignore"):
        home_med = np.nanmedian(px[:, home]) if np.isfinite(px[:, home]).any() else np.nan
        away_med = np.nanmedian(px[:, away]) if np.isfinite(px[:, away]).any() else np.nan
    if away_med < home_med:  # home attacks -x in this period: mirror
        players = players.copy()
        players[:, :, 0] = length - players[:, :, 0]
        ball = ball.copy()
        ball[:, 0] = length - ball[:, 0]

    seen = np.isfinite(ball[:, 0])
    f = {"ball_seen": seen.astype(float), "ball_x": ball[:, 0].astype(float),
         "ball_y": ball[:, 1].astype(float)}
    f["ball_speed"] = np.minimum(_step(ball.astype(float), fps), BALL_SPEED_MAX)
    outside = np.maximum.reduce([-ball[:, 0], ball[:, 0] - length, -ball[:, 1],
                                 ball[:, 1] - width, np.zeros(len(ball))])
    f["ball_out"] = np.where(seen, outside, np.nan)
    f["since_seen"] = _since(seen).astype(float)
    f["until_seen"] = _since(seen[::-1])[::-1].astype(float)

    distance = np.linalg.norm(players - ball[:, None, :], axis=-1)
    for name, in_team in (("home", home), ("away", away)):
        d = np.where(in_team[None, :] & np.isfinite(distance), distance, np.inf)
        nearest = d.min(axis=1) if d.shape[1] else np.full(len(d), np.inf)
        f[f"d_{name}"] = np.where(np.isfinite(nearest), nearest, np.nan)
        f[f"n_{name}3"] = np.where(seen, (d < NEAR).sum(axis=1), np.nan)
        f[f"cx_{name}"] = _team_mean(players[:, :, 0].astype(float), in_team)
    f["d_diff"] = f["d_home"] - f["d_away"]
    f["cx_gap"] = f["cx_away"] - f["cx_home"]

    speed = np.minimum(_step(players.astype(float), fps), PLAYER_SPEED_MAX)
    f["v_home"] = _team_mean(speed, home)
    f["v_away"] = _team_mean(speed, away)
    outfield = team >= 0
    valid_speed = np.isfinite(speed[:, outfield])
    f["slow_frac"] = _ratio((valid_speed & (speed[:, outfield] < SLOW)).sum(axis=1),
                            valid_speed.sum(axis=1))
    f["n_tracked"] = np.isfinite(players[:, outfield, 0]).sum(axis=1).astype(float)
    side = np.sign(f["d_diff"])
    f["last_side"] = _forward_fill(side, np.isfinite(side))

    for window in WINDOWS:
        for name in ROLLED:
            f[f"{name}_m{window}"] = _rolling_mean(f[name], window)
    return f


def frame_features(track: MatchTracking) -> np.ndarray:
    """(T, len(FEATURE_NAMES)) float32. Frames outside every period are NaN."""
    out = np.full((track.n_frames(), len(FEATURE_NAMES)), np.nan, dtype=np.float32)
    for start, stop in track.periods:
        f = _period_features(track.players[start:stop], track.team_of_slot,
                             track.ball[start:stop], track.pitch, track.fps)
        out[start:stop] = np.column_stack([f[name] for name in FEATURE_NAMES])
    return out
