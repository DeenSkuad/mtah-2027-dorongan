"""Write a submission CSV that is valid by construction, then prove it with the official check."""

from pathlib import Path

import numpy as np

from mtah.constants import LABELS, N_MATCH_FRAMES, official_metrics


def write_submission(labels: np.ndarray, path: Path) -> Path:
    """Refuse before writing if the labels break the contract; re-validate after writing."""
    labels = np.asarray(labels).astype("<U1")
    if len(labels) != N_MATCH_FRAMES:
        raise ValueError(f"need {N_MATCH_FRAMES} labels, got {len(labels)}")
    bad = sorted(set(np.unique(labels)) - set(LABELS))
    if bad:
        raise ValueError(f"labels outside {LABELS}: {bad[:5]}")

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        handle.write("frame,label\n")
        handle.writelines(f"{frame},{label}\n" for frame, label in enumerate(labels))

    metrics = official_metrics()
    reason = metrics.validate_submission(metrics.read_label_csv(path), N_MATCH_FRAMES)
    if reason:
        raise ValueError(f"written file failed official validation: {reason}")
    return path
