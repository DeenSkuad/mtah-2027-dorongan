"""Project-wide constants. Label codes mirror evaluation/possession_metrics.py exactly."""

import os
import sys
from pathlib import Path

LABELS = ("H", "A", "D", "X")
H, A, D, X = 0, 1, 2, 3

FPS = 25
MATCH_PITCH = (105.3, 68.0)  # metres (length, width); ATD coordinates are normalised 0-1
N_MATCH_FRAMES = 199_319

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.environ.get("MTAH_DATA_DIR", REPO_ROOT / "data"))
RESULTS_DIR = REPO_ROOT / "evaluation" / "results"


def official_metrics():
    """The upstream metric module, imported from evaluation/ without copying it."""
    evaluation = str(REPO_ROOT / "evaluation")
    if evaluation not in sys.path:
        sys.path.insert(0, evaluation)
    import possession_metrics

    return possession_metrics
