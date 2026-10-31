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
from mtah.schema import MatchTracking


def _upstream(name: str):
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    spec = importlib.util.spec_from_file_location(f"upstream_{name}",
                                                  REPO_ROOT / "starter" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _xy(group: str) -> tuple[float, float]:
    if group[0] == "N":
        return np.nan, np.nan
    x, y = group.split(",")[:2]
    return float(x), float(y)


def load_match(data_dir: Path = DATA_DIR) -> MatchTracking:
    import games

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
            players[t] = [_xy(group) for group in parts[1].split(";")]
            ball[t] = _xy(parts[2])
    players *= scale
    ball *= scale
    return MatchTracking(players, team_of_slot, ball, ((0, N_MATCH_FRAMES),), MATCH_PITCH)
