"""The upstream reference baseline on MatchTracking: nearest player to the ball, then a vote.

Kept bit-for-bit compatible with starter/baseline.py (see the parity test) so every new method
is compared against exactly the floor the organisers published.
"""

import numpy as np

from mtah.schema import MatchTracking

_HOME, _AWAY, _NOBODY = 0, 1, -1


def _nearest_codes(track: MatchTracking) -> np.ndarray:
    """Per frame: team of the closest tracked player to the ball, -1 when there is no ball."""
    outfield = track.team_of_slot >= 0
    delta = track.players[:, outfield, :] - track.ball[:, None, :]
    distance = np.einsum("tnk,tnk->tn", delta, delta)
    distance = np.where(np.isnan(distance), np.inf, distance)
    best = distance.argmin(axis=1)
    codes = track.team_of_slot[outfield][best].astype(np.int8)
    no_answer = np.isnan(track.ball[:, 0]) | np.isinf(distance.min(axis=1))
    codes[no_answer] = _NOBODY
    return codes


def _vote(codes: np.ndarray, window: int) -> np.ndarray:
    """Majority vote over +/- window frames; D where nobody has the ball; ties go home."""
    if window <= 0:
        return np.where(codes == _HOME, "H", np.where(codes == _AWAY, "A", "D")).astype("<U1")
    home = np.concatenate(([0], np.cumsum(codes == _HOME)))
    away = np.concatenate(([0], np.cumsum(codes == _AWAY)))
    index = np.arange(len(codes))
    low, high = np.maximum(0, index - window), np.minimum(len(codes), index + window + 1)
    n_home, n_away = home[high] - home[low], away[high] - away[low]
    labels = np.full(len(codes), "D", dtype="<U1")
    seen = (n_home + n_away) > 0
    labels[seen] = np.where(n_home[seen] >= n_away[seen], "H", "A")
    return labels


def nearest_player(track: MatchTracking, window: int = 125) -> np.ndarray:
    return _vote(_nearest_codes(track), window)
