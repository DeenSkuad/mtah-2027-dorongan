"""Download + cache the external bench matches (7 IDSSE + 2 Metrica) and print a per-match summary.

External, openly licensed data (IDSSE CC-BY, Metrica public samples) — safe to show Claude,
unlike the match (rule R1).
"""

import numpy as np

from mtah.io.external import EXTERNAL_MATCHES, load_external

if __name__ == "__main__":
    print(f"{'match':9} {'frames':>8} {'periods':>7} {'H':>6} {'A':>6} {'D':>6} {'ball%':>6}")
    for match_id in EXTERNAL_MATCHES:
        track, labels = load_external(match_id)
        ball = 100 * np.isfinite(track.ball[:, 0]).mean()
        shares = [100 * (labels == k).mean() for k in "HAD"]
        print(f"{match_id:9} {track.n_frames():8d} {len(track.periods):7d} "
              + " ".join(f"{s:6.1f}" for s in shares) + f" {ball:6.1f}")
