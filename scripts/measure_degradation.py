"""HUMAN-RUN ONLY (rule R1). Measure our tracking quality and write config/degradation.local.json.

The file is git-ignored and never read by Claude; mtah.degrade picks it up automatically, so the
external benchmark is degraded to match the real match without the numbers leaving this machine.
Prints nothing but "written".
"""

import json

import numpy as np

from mtah.degrade import CONFIG_DIR, in_play_mask
from mtah.io.match import load_match


def _runs(mask: np.ndarray) -> np.ndarray:
    edges = np.diff(np.concatenate(([0], mask.astype(np.int8), [0])))
    return np.flatnonzero(edges == -1) - np.flatnonzero(edges == 1)


def main() -> None:
    track = load_match()
    # Only frames with a full-ish pitch count: pre-match, half-time and post-match would inflate
    # the missing-ball fraction and add one ~20k-frame "gap" (review I2).
    in_play = in_play_mask(track.players)
    missing = np.isnan(track.ball[in_play, 0])
    gaps = _runs(missing)
    present = ~np.isnan(track.players[in_play, :, 0])
    # A tracklet that starts mid-match is a proxy for an identity break.
    starts = int((present[1:] & ~present[:-1]).sum())
    minutes = int(in_play.sum()) / (track.fps * 60)
    config = {
        "ball_missing_frac": float(missing.mean()),
        "gap_len_median_frames": int(np.median(gaps)) if len(gaps) else 1,
        "gap_len_sigma": float(np.std(np.log(gaps))) if len(gaps) > 1 else 1.0,
        "id_switch_per_min": float(starts / minutes / 2),
    }
    (CONFIG_DIR / "degradation.local.json").write_text(json.dumps(config, indent=2))
    print("written")


if __name__ == "__main__":
    main()
