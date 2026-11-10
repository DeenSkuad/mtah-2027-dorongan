"""MatchTracking: the one data contract every loader produces and every predictor consumes."""

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class MatchTracking:
    players: np.ndarray       # (T, N, 2) float32 metres, NaN when the slot is absent
    team_of_slot: np.ndarray  # (N,) int8: 0 home, 1 away, -1 other (referee / unknown)
    ball: np.ndarray          # (T, 2) float32 metres, NaN when the ball is missing
    periods: tuple[tuple[int, int], ...]  # half-open frame spans, sorted, non-overlapping
    pitch: tuple[float, float]            # (length, width) metres, origin at a corner
    fps: int = 25

    def n_frames(self) -> int:
        return int(self.players.shape[0])

    def validate(self) -> None:
        T = self.n_frames()
        if self.players.ndim != 3 or self.players.shape[2] != 2:
            raise ValueError(f"players must be (T, N, 2), got {self.players.shape}")
        if self.ball.shape != (T, 2):
            raise ValueError(f"ball must be ({T}, 2), got {self.ball.shape}")
        if self.team_of_slot.shape != (self.players.shape[1],):
            raise ValueError("team_of_slot length must equal the number of player slots")
        previous_stop = 0
        for start, stop in self.periods:
            if not (previous_stop <= start < stop <= T):
                raise ValueError(f"periods must be sorted, non-overlapping, within 0..{T}")
            previous_stop = stop


def infer_periods(players: np.ndarray, min_players: int = 18, bridge: int = 3000,
                  min_len: int = 7500) -> tuple[tuple[int, int], ...]:
    """Playing periods from player presence alone (no frame constants, rule R4).

    A frame is active when at least min_players slots are tracked. Active runs closer than
    `bridge` frames (2 min at 25 fps) are joined; joined runs shorter than `min_len` (5 min)
    are dropped. Pre-match, half-time and post-match fall outside every period. Falls back to
    one period over everything when nothing qualifies."""
    active = (~np.isnan(players[:, :, 0])).sum(axis=1) >= min_players
    edges = np.flatnonzero(np.diff(np.concatenate(([0], active.astype(np.int8), [0]))))
    runs = []
    for start, stop in zip(edges[::2], edges[1::2], strict=True):
        if runs and start - runs[-1][1] < bridge:
            runs[-1][1] = int(stop)
        else:
            runs.append([int(start), int(stop)])
    periods = tuple((a, b) for a, b in runs if b - a >= min_len)
    return periods or ((0, len(players)),)
