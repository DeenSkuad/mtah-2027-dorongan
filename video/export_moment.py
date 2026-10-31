"""Export a short IDSSE (CC-BY) sequence to JSON for Blender. External data only, never the match.

    python video/export_moment.py J03WMX 13222 100 75   # match, switch frame, frames before/after
"""

import json
import sys
from pathlib import Path

import numpy as np

from mtah.io.external import load_idsse


def main() -> None:
    match_id = sys.argv[1]
    center, before, after = (int(v) for v in sys.argv[2:5])
    track, labels = load_idsse(match_id)
    window = slice(center - before, center + after)
    players = track.players[window]
    active = np.flatnonzero(np.isfinite(players[:, :, 0]).all(axis=0))
    out = {
        "source": f"IDSSE/DFL {match_id} (CC-BY 4.0)",
        "fps": track.fps,
        "pitch": list(track.pitch),
        "switch_frame": before,
        "teams": [int(track.team_of_slot[i]) for i in active],
        "players": np.round(players[:, active], 3).tolist(),
        "ball": np.round(track.ball[window], 3).tolist(),
        "labels": labels[window].tolist(),
    }
    path = Path(__file__).parent / "out" / f"moment_{match_id}_{center}.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out))
    print(path.name, len(active), "players", players.shape[0], "frames")


if __name__ == "__main__":
    main()
