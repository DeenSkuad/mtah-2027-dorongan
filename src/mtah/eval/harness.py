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


def bench_learned(make_model, decoders: dict, match_ids, cfg, seed: int = 0,
                  train_scenarios=("default",), eval_scenarios=("default",)):
    """Bench a trainable predictor. Each IDSSE match is scored by a model fitted on the other
    IDSSE matches; other sources by one model fitted on all of them. Every IDSSE match is
    degraded once per training scenario (seed + 1 + index); scored tracks use seed, once per eval
    scenario. decoders maps a name to (switch_cost, dead_cost); rows are named
    '<decoder>@<eval scenario>'. Each fold and scenario computes probabilities once."""
    import pandas as pd

    from mtah.degrade import SCENARIOS, degrade, scenario
    from mtah.io import external

    for name in (*train_scenarios, *eval_scenarios):
        SCENARIOS[name]  # KeyError before any loading

    def degraded(match_id: str, run_seed: int, scenario_name: str):
        clean, labels = external.load_external(match_id)
        rng = np.random.default_rng(match_seed(run_seed, match_id))
        return degrade(clean, scenario(cfg, scenario_name), rng), labels

    pool = list(external.IDSSE_MATCHES)
    train = {m: [degraded(m, seed + 1 + i, name) for i, name in enumerate(train_scenarios)]
             for m in pool}

    def fit(exclude: str | None):
        kept = [pair for m in pool if m != exclude for pair in train[m]]
        return make_model().fit([t for t, _ in kept], [lab for _, lab in kept])

    rows, full_model = [], None
    for match_id in match_ids:
        if match_id in train:
            model = fit(exclude=match_id)
        else:
            full_model = full_model or fit(exclude=None)
            model = full_model
        for eval_name in eval_scenarios:
            track, labels = degraded(match_id, seed, eval_name)
            proba = model.proba(track)
            for name, (switch_cost, dead_cost) in decoders.items():
                pred = model.decode(proba, track.periods, switch_cost=switch_cost,
                                    dead_cost=dead_cost)
                rows.append({"predictor": f"{name}@{eval_name}", "match": match_id,
                             **score(labels, pred, track.periods)})
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
