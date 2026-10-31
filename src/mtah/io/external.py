"""IDSSE / DFL Bundesliga open data (Bassek et al. 2025, CC-BY) -> MatchTracking + H/A/D labels.

These 7 matches carry per-frame BallPossession and BallStatus, i.e. exactly our label set, which is
what makes them the internal validation set (rule R3: never tune on the public 5 minutes).
Files are fetched once into a cache outside the repository (default ~/.cache/mtah/idsse).
"""

import subprocess
from pathlib import Path

import numpy as np

from mtah.schema import MatchTracking

IDSSE_MATCHES = ("J03WMX", "J03WN1", "J03WOH", "J03WOY", "J03WPY", "J03WQQ", "J03WR9")
DEFAULT_CACHE = Path.home() / ".cache" / "mtah" / "idsse"


def _url(match_id: str, kind: str) -> str:
    from kloppy._providers.sportec import get_IDSSE_url

    return get_IDSSE_url(match_id, kind)


def fetch_idsse(match_id: str, cache_dir: Path = DEFAULT_CACHE) -> tuple[Path, Path]:
    """Download (resumably) the meta and tracking XML for one match; return their paths."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for kind in ("meta", "tracking"):
        url = _url(match_id, kind)
        path = cache_dir / url.rsplit("/", 1)[-1]
        if not path.exists() or path.stat().st_size == 0:
            subprocess.run(["curl", "-sSL", "-C", "-", "--retry", "5", "-o", str(path), url],
                           check=True)
        paths.append(path)
    return paths[0], paths[1]


def _labels_from_frames(frames, home_team) -> np.ndarray:
    """D when the ball is dead; else the owning team. A missing owner keeps the last owner."""
    labels = np.empty(len(frames), dtype="<U1")
    last_owner = "D"
    for index, frame in enumerate(frames):
        if frame.ball_state is None or frame.ball_state.value != "alive":
            labels[index] = "D"
            continue
        owner = frame.ball_owning_team
        if owner is not None:
            last_owner = "H" if owner is home_team else "A"
        labels[index] = last_owner
    return labels


def _to_track(dataset) -> MatchTracking:
    length = float(dataset.metadata.pitch_dimensions.pitch_length)
    width = float(dataset.metadata.pitch_dimensions.pitch_width)
    home, away = dataset.metadata.teams[0], dataset.metadata.teams[1]
    roster = [p for p in home.players] + [p for p in away.players]
    slot_of = {p.player_id: i for i, p in enumerate(roster)}
    team_of_slot = np.array([0] * len(home.players) + [1] * len(away.players), dtype=np.int8)

    frames = dataset.frames
    T, N = len(frames), len(roster)
    players = np.full((T, N, 2), np.nan, dtype=np.float32)
    ball = np.full((T, 2), np.nan, dtype=np.float32)
    period_ids = np.empty(T, dtype=np.int16)
    for t, frame in enumerate(frames):
        period_ids[t] = frame.period.id
        if frame.ball_coordinates is not None:
            ball[t] = (frame.ball_coordinates.x * length, frame.ball_coordinates.y * width)
        for player, data in frame.players_data.items():
            if data.coordinates is not None and player.player_id in slot_of:
                players[t, slot_of[player.player_id]] = (data.coordinates.x * length,
                                                         data.coordinates.y * width)

    edges = np.flatnonzero(np.diff(period_ids)) + 1
    bounds = np.concatenate(([0], edges, [T]))
    periods = tuple((int(a), int(b)) for a, b in zip(bounds[:-1], bounds[1:], strict=True))
    return MatchTracking(players, team_of_slot, ball, periods, (length, width),
                         int(round(dataset.metadata.frame_rate)))


def load_idsse(match_id: str, cache_dir: Path = DEFAULT_CACHE) -> tuple[MatchTracking, np.ndarray]:
    """One IDSSE match as (MatchTracking, labels). Parsed once, then served from an .npz cache."""
    cached = cache_dir / f"{match_id}.npz"
    if cached.exists():
        z = np.load(cached)
        periods = tuple(map(tuple, z["periods"].tolist()))
        track = MatchTracking(z["players"], z["team_of_slot"], z["ball"], periods,
                              tuple(z["pitch"].tolist()), int(z["fps"]))
        return track, z["labels"]

    from kloppy import sportec

    meta, raw = fetch_idsse(match_id, cache_dir)
    dataset = sportec.load_tracking(meta_data=str(meta), raw_data=str(raw),
                                    coordinates="kloppy", only_alive=False)
    track = _to_track(dataset)
    labels = _labels_from_frames(dataset.frames, dataset.metadata.teams[0])
    track.validate()
    np.savez_compressed(cached, players=track.players, team_of_slot=track.team_of_slot,
                        ball=track.ball, periods=np.array(track.periods),
                        pitch=np.array(track.pitch), fps=track.fps, labels=labels)
    return track, labels
