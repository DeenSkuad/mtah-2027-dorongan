"""Make clean external tracking look like ours: ball dropout and tracklet identity switches.

Defaults come from the challenge docs (ball missing on 41% of graded frames) and literature.
Values measured on the match live in config/degradation.local.json, written locally by
scripts/measure_degradation.py and never read by Claude (rule R1).
"""

import json
from dataclasses import dataclass, replace

import numpy as np

from mtah.constants import REPO_ROOT
from mtah.schema import MatchTracking

CONFIG_DIR = REPO_ROOT / "config"


@dataclass(frozen=True)
class DegradeConfig:
    ball_missing_frac: float = 0.41
    gap_len_median_frames: int = 25
    gap_len_sigma: float = 1.0
    id_switch_per_min: float = 2.0


def load_config() -> DegradeConfig:
    local = CONFIG_DIR / "degradation.local.json"
    path = local if local.exists() else CONFIG_DIR / "degradation.default.json"
    return DegradeConfig(**json.loads(path.read_text()))


def in_play_mask(players: np.ndarray, min_players: int = 18) -> np.ndarray:
    """Frames with at least min_players tracked: drops pre-match, half-time and post-match."""
    return (~np.isnan(players[:, :, 0])).sum(axis=1) >= min_players


def _drop_ball(ball: np.ndarray, cfg: DegradeConfig, rng: np.random.Generator) -> np.ndarray:
    """Add log-normal-length gaps until the requested missing fraction is reached."""
    ball = ball.copy()
    T = len(ball)
    missing = np.isnan(ball[:, 0])
    target = int(round(cfg.ball_missing_frac * T))
    while missing.sum() < target:
        length = max(1, int(rng.lognormal(np.log(cfg.gap_len_median_frames), cfg.gap_len_sigma)))
        length = min(length, target - int(missing.sum()))
        start = int(rng.integers(0, T - length + 1))
        missing[start:start + length] = True
    ball[missing] = np.nan
    return ball


def _switch_ids(track: MatchTracking, cfg: DegradeConfig, rng: np.random.Generator) -> np.ndarray:
    """Swap the trajectories of two same-team slots from a random frame onward."""
    players = track.players.copy()
    n_switches = rng.poisson(cfg.id_switch_per_min * track.n_frames() / (track.fps * 60))
    for _ in range(n_switches):
        slots = np.flatnonzero(track.team_of_slot == int(rng.integers(0, 2)))
        if len(slots) < 2:
            continue
        a, b = rng.choice(slots, size=2, replace=False)
        t = int(rng.integers(0, track.n_frames()))
        players[t:, [a, b]] = players[t:, [b, a]]
    return players


def degrade(track: MatchTracking, cfg: DegradeConfig, rng: np.random.Generator) -> MatchTracking:
    """A new MatchTracking with ball gaps and same-team ID switches. The input is not modified."""
    return replace(track, ball=_drop_ball(track.ball, cfg, rng),
                   players=_switch_ids(track, cfg, rng))
