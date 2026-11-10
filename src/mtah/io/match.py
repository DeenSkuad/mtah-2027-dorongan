"""BAR-ATH tactical tracking -> MatchTracking. HUMAN-RUN ONLY: it reads match data (rule R1).

Format as documented in docs/challenge/DATA.md and parsed by starter/baseline.py:
one line per frame, "frame_id:slot;slot;...:ball", each group "x,y,speed" normalised 0-1 or NaN.
frame_id counts from 1; submission row i is video frame i = frame_id - 1.
"""

import importlib.util
import sys
from pathlib import Path

import numpy as np

from mtah.constants import DATA_DIR, MATCH_PITCH, N_MATCH_FRAMES, REPO_ROOT
from mtah.schema import MatchTracking, infer_periods


def _ensure_repo_root_on_path() -> None:
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))


def _import_games():
    """The upstream games module lives at the repo root, which an editable install omits."""
    _ensure_repo_root_on_path()
    import games

    return games


def _upstream(name: str):
    _ensure_repo_root_on_path()
    spec = importlib.util.spec_from_file_location(f"upstream_{name}",
                                                  REPO_ROOT / "starter" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _xy(group: str) -> tuple[float, float]:
    if group[0] == "N":
        return np.nan, np.nan
    try:
        x, y = group.split(",")[:2]
        return float(x), float(y)
    except ValueError:
        # Never echo the raw value: tracebacks get pasted into chats (rule R1).
        raise ValueError("unparseable coordinate group in tracking file") from None


def load_match(data_dir: Path = DATA_DIR) -> MatchTracking:
    games = _import_games()
    baseline = _upstream("baseline")
    paths = games.asset_paths(data_dir=str(data_dir))
    team_of_slot = baseline.team_of_each_track(paths["atd_meta"]).astype(np.int8)
    length, width = MATCH_PITCH
    scale = np.array([length, width], dtype=np.float32)

    players = np.full((N_MATCH_FRAMES, team_of_slot.size, 2), np.nan, dtype=np.float32)
    ball = np.full((N_MATCH_FRAMES, 2), np.nan, dtype=np.float32)
    with open(paths["atd_raw"]) as handle:
        for line in handle:
            parts = line.rstrip("\n").split(":")
            if len(parts) != 3:
                continue
            t = int(parts[0]) - 1
            if not 0 <= t < N_MATCH_FRAMES:
                raise ValueError("frame id outside the submission range")
            players[t] = [_xy(group) for group in parts[1].split(";")]
            ball[t] = _xy(parts[2])
    players *= scale
    ball *= scale
    # Halves come from player presence: the learned features need the true period split.
    return MatchTracking(players, team_of_slot, ball, infer_periods(players), MATCH_PITCH)
