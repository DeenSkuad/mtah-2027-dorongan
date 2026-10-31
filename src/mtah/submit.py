"""Write a submission CSV that is valid by construction, then prove it with the official check."""

import os
import tempfile
from pathlib import Path

import numpy as np

from mtah.constants import LABELS, N_MATCH_FRAMES, official_metrics


def write_submission(labels: np.ndarray, path: Path) -> Path:
    """Refuse before writing if the labels break the contract; replace the target atomically.

    Labels are checked as given — never truncated first, so "Home" is an error, not an H — and
    the file is written to a temporary sibling and validated before it replaces `path`, so a bad
    run can never overwrite a previous good submission.
    """
    labels = np.asarray(labels)
    if labels.ndim != 1 or len(labels) != N_MATCH_FRAMES:
        raise ValueError(f"need a 1-D array of {N_MATCH_FRAMES} labels, got shape {labels.shape}")
    as_text = np.array([str(v) for v in labels], dtype=object)
    bad = sorted(set(as_text) - set(LABELS))
    if bad:
        raise ValueError(f"labels outside {LABELS}: {bad[:5]}")

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, tmp = tempfile.mkstemp(dir=path.parent, suffix=".csv.tmp")
    try:
        with os.fdopen(handle, "w") as out:
            out.write("frame,label\n")
            out.writelines(f"{frame},{label}\n" for frame, label in enumerate(as_text))
        metrics = official_metrics()
        reason = metrics.validate_submission(metrics.read_label_csv(tmp), N_MATCH_FRAMES)
        if reason:
            raise ValueError(f"written file failed official validation: {reason}")
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    return path
