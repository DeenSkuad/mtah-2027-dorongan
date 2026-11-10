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
    # Realism knobs (defaults = off, output unchanged). All measurable on the match without labels.
    edge_boost: float = 1.0          # gap-start weight when the ball is within 3 m of a line/out
    slow_boost: float = 1.0          # gap-start weight when >60% of players are slower than 1 m/s
    offpitch_visible: bool = True    # False: the ball vanishes whenever it is off the pitch
    player_missing_frac: float = 0.0  # share of team player-frames hidden in log-normal gaps


SCENARIOS = {
    "default": {},
    "edge": {"edge_boost": 4.0, "offpitch_visible": False},
    "slow": {"slow_boost": 4.0},
    "players": {"player_missing_frac": 0.15},
}
SCENARIOS["all"] = {**SCENARIOS["edge"], **SCENARIOS["slow"], **SCENARIOS["players"]}


def scenario(cfg: DegradeConfig, name: str) -> DegradeConfig:
    """cfg with a stress scenario's overrides applied; KeyError on an unknown name."""
    return replace(cfg, **SCENARIOS[name])


def near_edge(ball: np.ndarray, pitch, margin: float = 3.0) -> np.ndarray:
    """Visible ball within `margin` metres of a boundary line, or outside the pitch."""
    length, width = pitch
    x, y = ball[:, 0], ball[:, 1]
    with np.errstate(invalid="ignore"):
        return (x < margin) | (x > length - margin) | (y < margin) | (y > width - margin)


def slow_play(players: np.ndarray, fps: int, share: float = 0.6, speed: float = 1.0) -> np.ndarray:
    """Frames where more than `share` of the tracked players move slower than `speed` m/s."""
    step = np.full(players.shape[:2], np.nan)
    step[1:] = np.linalg.norm(np.diff(players, axis=0), axis=-1) * fps
    valid = np.isfinite(step)
    slow = (valid & (np.nan_to_num(step, nan=np.inf) < speed)).sum(axis=1)
    return slow > share * np.maximum(valid.sum(axis=1), 1)


def load_config() -> DegradeConfig:
    local = CONFIG_DIR / "degradation.local.json"
    path = local if local.exists() else CONFIG_DIR / "degradation.default.json"
    return DegradeConfig(**json.loads(path.read_text()))


def in_play_mask(players: np.ndarray, min_players: int = 18) -> np.ndarray:
    """Frames with at least min_players tracked: drops pre-match, half-time and post-match."""
    return (~np.isnan(players[:, :, 0])).sum(axis=1) >= min_players


def _drop_ball(ball: np.ndarray, cfg: DegradeConfig, rng: np.random.Generator,
               weights: np.ndarray | None = None) -> np.ndarray:
    """Add log-normal-length gaps until the requested missing fraction is reached. With
    weights, gap starts are drawn in proportion to them (None = uniform, the original path)."""
    ball = ball.copy()
    T = len(ball)
    missing = np.isnan(ball[:, 0])
    target = int(round(cfg.ball_missing_frac * T))
    cumulative = None if weights is None else np.cumsum(weights)
    while missing.sum() < target:
        length = max(1, int(rng.lognormal(np.log(cfg.gap_len_median_frames), cfg.gap_len_sigma)))
        length = min(length, target - int(missing.sum()))
        if cumulative is None:
            start = int(rng.integers(0, T - length + 1))
        else:
            last = cumulative[T - length]
            start = int(np.searchsorted(cumulative, rng.uniform(0, last), side="right"))
            start = min(start, T - length)
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


def _drop_players(players: np.ndarray, team: np.ndarray, frac: float,
                  rng: np.random.Generator) -> np.ndarray:
    """Hide log-normal gaps (median 2 s) in team-0/1 slots until `frac` of their visible
    player-frames are hidden. Referee / unknown slots are never touched."""
    players = players.copy()
    slots = np.flatnonzero(team >= 0)
    T = len(players)
    target = frac * np.isfinite(players[:, slots, 0]).sum()
    hidden = 0
    while hidden < target and len(slots):
        slot = int(rng.choice(slots))
        length = min(T, max(1, int(rng.lognormal(np.log(50), 1.0))))
        start = int(rng.integers(0, T - length + 1))
        hidden += int(np.isfinite(players[start:start + length, slot, 0]).sum())
        players[start:start + length, slot] = np.nan
    return players


def degrade(track: MatchTracking, cfg: DegradeConfig, rng: np.random.Generator) -> MatchTracking:
    """A new MatchTracking with ball gaps and same-team ID switches (plus the optional realism
    knobs). The input is not modified; default knobs reproduce the original output exactly."""
    ball = track.ball
    if not cfg.offpitch_visible:
        length, width = track.pitch
        with np.errstate(invalid="ignore"):
            out = ((ball[:, 0] < 0) | (ball[:, 0] > length) | (ball[:, 1] < 0)
                   | (ball[:, 1] > width))
        ball = np.where(out[:, None], np.nan, ball).astype(ball.dtype)
    weights = None
    if cfg.edge_boost != 1.0 or cfg.slow_boost != 1.0:
        weights = np.ones(track.n_frames())
        weights[near_edge(track.ball, track.pitch)] *= cfg.edge_boost
        weights[slow_play(track.players, track.fps)] *= cfg.slow_boost
    ball = _drop_ball(ball, cfg, rng, weights)
    players = _switch_ids(track, cfg, rng)
    if cfg.player_missing_frac > 0:
        players = _drop_players(players, track.team_of_slot, cfg.player_missing_frac, rng)
    return replace(track, ball=ball, players=players)


def _start_rate_ratio(started: np.ndarray, visible: np.ndarray, condition: np.ndarray) -> float:
    """(gap starts per visible frame where condition) / (same where not), clipped to [1, 10]."""
    inside, outside = visible & condition, visible & ~condition
    if not inside.any() or not outside.any():
        return 1.0
    if not started[outside].any():
        return 10.0 if started[inside].any() else 1.0
    ratio = started[inside].mean() / started[outside].mean()
    return float(np.clip(ratio, 1.0, 10.0))


def measure_knobs(track: MatchTracking) -> dict:
    """The realism knobs measured from tracking alone (no labels), over in-play frames.

    A gap start is a visible ball frame followed by a missing one; its edge / slow condition is
    read on that last visible frame."""
    in_play = in_play_mask(track.players)
    ball, players = track.ball[in_play], track.players[in_play]
    visible = np.isfinite(ball[:, 0])
    started = np.zeros(len(ball), dtype=bool)
    started[:-1] = visible[:-1] & ~visible[1:]
    length, width = track.pitch
    with np.errstate(invalid="ignore"):
        off = visible & ((ball[:, 0] < 0) | (ball[:, 0] > length) | (ball[:, 1] < 0)
                         | (ball[:, 1] > width))
    team = track.team_of_slot >= 0
    tracked = np.isfinite(players[:, team, 0]).sum(axis=1)
    return {
        "edge_boost": _start_rate_ratio(started, visible, near_edge(ball, track.pitch)),
        "slow_boost": _start_rate_ratio(started, visible, slow_play(players, track.fps)),
        "offpitch_visible": bool(visible.any() and off.sum() / visible.sum() > 0.002),
        "player_missing_frac": float(np.clip(1 - tracked.mean() / 22, 0.0, 0.6))
        if len(tracked) else 0.0,
    }
