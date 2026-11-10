"""Metrica Sports sample games 1-2 (github.com/metrica-sports) -> MatchTracking + labels.

A second provider for the bench, next to IDSSE. Metrica publishes no per-frame possession, so the
H/A/D labels are rebuilt from the hand-tagged event file:

- PASS, BALL LOST, RECOVERY, SET PIECE, SHOT: that team owns the ball from the event's start frame
  until another event says otherwise (ball in flight stays with the last owner, as in IDSSE).
- BALL OUT and SHOT ...GOAL / ...OUT: dead from the end frame (when the ball crosses the line).
- FAULT RECEIVED: dead from the whistle (start frame).
- Dead lasts until the next owning event, normally the SET PIECE restart.
- CHALLENGE and CARD do not change possession. Nothing carries across a period boundary.

Event tags are coarser than IDSSE's per-frame flags, so this ground truth is noisier. Read the
Metrica rows of the bench as a check that a predictor generalises, not as a fine score.
Files are fetched once into ~/.cache/mtah/metrica (about 127 MB for both games).
"""

import subprocess
from pathlib import Path

import numpy as np

from mtah.io.external import METRICA_IDS, _load_cached, _save_cached, _to_track
from mtah.schema import MatchTracking

METRICA_MATCHES = METRICA_IDS
DEFAULT_CACHE = Path.home() / ".cache" / "mtah" / "metrica"
CACHE_VERSION = 1  # bump whenever parsing or label semantics change
_RAW = "https://raw.githubusercontent.com/metrica-sports/sample-data/master/data"

OWNING = {"PASS", "BALL LOST", "RECOVERY", "SET PIECE", "SHOT"}


def _game(match_id: str) -> int:
    return int(match_id.removeprefix("metrica"))


def fetch_metrica(match_id: str, cache_dir: Path = DEFAULT_CACHE) -> tuple[Path, Path, Path]:
    """Download (resumably) home tracking, away tracking and events CSV; return their paths."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    game = _game(match_id)
    names = (f"Sample_Game_{game}_RawTrackingData_Home_Team.csv",
             f"Sample_Game_{game}_RawTrackingData_Away_Team.csv",
             f"Sample_Game_{game}_RawEventsData.csv")
    paths = []
    for name in names:
        path = cache_dir / name
        if not path.exists() or path.stat().st_size == 0:
            url = f"{_RAW}/Sample_Game_{game}/{name}"
            subprocess.run(["curl", "-sSL", "-C", "-", "--retry", "5", "-o", str(path), url],
                           check=True)
        paths.append(path)
    return paths[0], paths[1], paths[2]


def _labels_from_events(events, frame_ids: np.ndarray, period_ids: np.ndarray) -> np.ndarray:
    """Per-frame H/A/D from Metrica events (columns Team, Type, Subtype, Period, Start Frame,
    End Frame). frame_ids are Metrica frame numbers, period_ids the period of each frame."""
    changes = []  # (frame, event order, state, period); later events win ties
    for order, ev in enumerate(events.itertuples(index=False)):
        kind = ev.Type
        subtype = ev.Subtype if isinstance(ev.Subtype, str) else ""  # NaN when untagged
        start, end = int(ev[4]), max(int(ev[4]), int(ev[5]))
        if kind in OWNING:
            changes.append((start, order, "H" if ev.Team == "Home" else "A", ev.Period))
        if kind == "BALL OUT" or (kind == "SHOT" and subtype.endswith(("GOAL", "OUT"))):
            changes.append((end, order, "D", ev.Period))
        elif kind == "FAULT RECEIVED":
            changes.append((start, order, "D", ev.Period))
    if not changes:
        return np.full(len(frame_ids), "D", dtype="<U1")
    changes.sort(key=lambda c: (c[0], c[1]))
    change_frames = np.array([c[0] for c in changes])
    states = np.array([c[2] for c in changes], dtype="<U1")
    change_periods = np.array([c[3] for c in changes])

    last = np.searchsorted(change_frames, frame_ids, side="right") - 1
    valid = last >= 0
    valid[valid] = change_periods[last[valid]] == np.asarray(period_ids)[valid]
    labels = np.full(len(frame_ids), "D", dtype="<U1")
    labels[valid] = states[last[valid]]
    return labels


def _cache_path(match_id: str, cache_dir: Path) -> Path:
    return cache_dir / f"{match_id}.v{CACHE_VERSION}.npz"


def load_metrica(match_id: str,
                 cache_dir: Path = DEFAULT_CACHE) -> tuple[MatchTracking, np.ndarray]:
    """One Metrica sample game as (MatchTracking, labels), cached as .npz after the first parse."""
    if match_id not in METRICA_MATCHES:
        raise ValueError(f"unknown Metrica match {match_id!r}")
    cached = _cache_path(match_id, cache_dir)
    if cached.exists():
        return _load_cached(cached)

    import pandas as pd
    from kloppy import metrica

    home, away, events_csv = fetch_metrica(match_id, cache_dir)
    dataset = metrica.load_tracking_csv(home_data=str(home), away_data=str(away),
                                        coordinates="kloppy")
    track = _to_track(dataset)
    frame_ids = np.array([f.frame_id for f in dataset.frames])
    period_ids = np.array([f.period.id for f in dataset.frames])
    events = pd.read_csv(events_csv)[["Team", "Type", "Subtype", "Period",
                                      "Start Frame", "End Frame"]]
    labels = _labels_from_events(events, frame_ids, period_ids)
    track.validate()
    _save_cached(cached, track, labels)
    return track, labels
