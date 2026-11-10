"""Score label arrays with the official metric (evaluation/possession_metrics.py)."""

import zlib
from collections.abc import Callable

import numpy as np

from mtah.constants import official_metrics
from mtah.schema import MatchTracking

Predictor = Callable[[MatchTracking], np.ndarray]

_KEYS = {
    "spell_f1": "spell_f1_mean",
    "macro_f1": "macro_f1",
    "n_gt_spells": "n_gt_spells",
    "n_pred_spells": "n_pred_spells",
    "mean_spell_s": "mean_spell_duration_s",
    "gt_mean_spell_s": "gt_mean_spell_duration_s",
}


def _join_periods(labels: np.ndarray, periods) -> np.ndarray:
    """Concatenate the periods with one X frame between them, so valid_runs splits them."""
    pieces = []
    for index, (start, stop) in enumerate(periods):
        if index:
            pieces.append(np.array(["X"], dtype="<U1"))
        pieces.append(labels[start:stop])
    return np.concatenate(pieces)


def score(gt: np.ndarray, pred: np.ndarray, periods) -> dict:
    """Aggregate scores for one prediction. gt/pred are <U1 arrays over H/A/D/X."""
    if len(gt) != len(pred):
        raise ValueError(f"length mismatch: gt {len(gt)} vs pred {len(pred)}")
    metrics = official_metrics()
    gt_codes = metrics.label_codes(_join_periods(gt, periods))
    pred_codes = metrics.label_codes(_join_periods(pred, periods))
    result = metrics.evaluate(gt_codes, pred_codes)
    return {ours: float(result[theirs]) for ours, theirs in _KEYS.items()}


def match_seed(seed: int, match_id: str) -> int:
    """Per-match RNG seed that does not depend on which other matches are in the run."""
    return seed * 1_000_003 + zlib.crc32(match_id.encode())


def bench(predictors: dict, match_ids, cfg, seed: int = 0):
    """Score every predictor on every external match after degradation; adds a MEAN row each."""
    import pandas as pd

    from mtah.degrade import degrade
    from mtah.io.external import load_external

    rows = []
    for match_id in match_ids:
        clean, labels = load_external(match_id)
        track = degrade(clean, cfg, np.random.default_rng(match_seed(seed, match_id)))
        for name, predictor in predictors.items():
            rows.append({"predictor": name, "match": match_id,
                         **score(labels, predictor(track), track.periods)})
    return summarise(pd.DataFrame(rows))


def source_of(match_id: str) -> str:
    return "metrica" if match_id.startswith("metrica") else "idsse"


def summarise(table):
    """Append one 'MEAN <source>' row per predictor and source. Sources are never pooled:
    Metrica's event-derived labels score far higher, and IDSSE is the one that tracks the board."""
    import pandas as pd

    sources = table["match"].map(source_of)
    means = (table.assign(source=sources)
             .groupby(["predictor", "source"], sort=False).mean(numeric_only=True).reset_index())
    means.insert(1, "match", "MEAN " + means.pop("source"))
    return pd.concat([table, means], ignore_index=True)
