"""Download + cache the 7 IDSSE Bundesliga matches and print a per-match summary.

External, openly licensed data (CC-BY) — safe to show Claude, unlike the match (rule R1).
"""

import numpy as np

from mtah.io.external import IDSSE_MATCHES, load_idsse

if __name__ == "__main__":
    print(f"{'match':8} {'frames':>8} {'periods':>7} {'H':>6} {'A':>6} {'D':>6} {'ball%':>6}")
    for match_id in IDSSE_MATCHES:
        track, labels = load_idsse(match_id)
        ball = 100 * np.isfinite(track.ball[:, 0]).mean()
        shares = [100 * (labels == k).mean() for k in "HAD"]
        print(f"{match_id:8} {track.n_frames():8d} {len(track.periods):7d} "
              + " ".join(f"{s:6.1f}" for s in shares) + f" {ball:6.1f}")
