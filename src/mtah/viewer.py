"""Pack a MatchTracking + predicted labels into the compact JSON the local viewer page reads.

Positions are sampled every `step` frames and stored as little-endian int16 decimetres (base64),
NaN as NAN. Labels stay at full frame rate as run-length spells. For the match this file is
written by a human-run script into viewer/out/ (git-ignored) and never leaves the machine (R1).
"""

import base64

import numpy as np

from mtah.schema import MatchTracking

NAN = -32768


def rle(labels: np.ndarray) -> list[list]:
    """[[start, stop, label], ...] half-open runs covering every frame."""
    labels = np.asarray(labels)
    if not len(labels):
        return []
    edges = np.flatnonzero(labels[1:] != labels[:-1]) + 1
    starts = np.concatenate(([0], edges))
    stops = np.concatenate((edges, [len(labels)]))
    return [[int(a), int(b), str(labels[a])] for a, b in zip(starts, stops, strict=True)]


def _pack(values: np.ndarray) -> str:
    dm = np.where(np.isfinite(values), np.round(values * 10), NAN)
    return base64.b64encode(np.clip(dm, NAN, 32767).astype("<i2").tobytes()).decode()


def viewer_payload(track: MatchTracking, labels: np.ndarray, home: str, away: str,
                   truth: np.ndarray | None = None, step: int = 5, source: str = "") -> dict:
    keep = np.flatnonzero(track.team_of_slot >= 0)
    payload = {
        "meta": {"home": home, "away": away, "fps": track.fps, "step": step,
                 "n_frames": track.n_frames(), "pitch": list(track.pitch),
                 "periods": [list(p) for p in track.periods], "source": source},
        "team": track.team_of_slot[keep].astype(int).tolist(),
        "players": _pack(track.players[::step][:, keep]),
        "ball": _pack(track.ball[::step]),
        "pred": rle(labels),
    }
    if truth is not None:
        payload["truth"] = rle(truth)
    return payload
