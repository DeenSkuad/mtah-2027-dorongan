"""Viterbi decoding of per-frame P(H, A, D) into a label path with transition costs.

Staying costs nothing, an H<->A switch costs switch_cost, and any alive<->dead change costs
dead_cost (natural-log units, same scale as the emission scores). Periods decode independently.
"""

import numpy as np

STATES = np.array(["H", "A", "D"])


def _decode_span(score: np.ndarray, cost: np.ndarray) -> np.ndarray:
    """Max-score path for one span. score is (T, 3), cost the 3x3 transition-cost matrix."""
    T = len(score)
    back = np.empty((T, 3), dtype=np.int8)
    rows = score.tolist()
    c = cost.tolist()
    best = rows[0][:]
    for t in range(1, T):
        prev = best
        best = [0.0, 0.0, 0.0]
        for j in range(3):
            candidates = [prev[0] - c[0][j], prev[1] - c[1][j], prev[2] - c[2][j]]
            k = max(range(3), key=candidates.__getitem__)
            back[t, j] = k
            best[j] = candidates[k] + rows[t][j]
    path = np.empty(T, dtype=np.int8)
    path[-1] = max(range(3), key=best.__getitem__)
    for t in range(T - 1, 0, -1):
        path[t - 1] = back[t, path[t]]
    return path


def viterbi(proba: np.ndarray, periods, switch_cost: float, dead_cost: float,
            prior: np.ndarray | None = None) -> np.ndarray:
    """(T, 3) probabilities in column order H, A, D -> <U1 labels. Outside periods: D."""
    prior = np.full(3, 1 / 3) if prior is None else np.asarray(prior, dtype=float)
    score = np.log(np.asarray(proba, dtype=float) + 1e-6) - np.log(prior)
    cost = np.array([[0.0, switch_cost, dead_cost],
                     [switch_cost, 0.0, dead_cost],
                     [dead_cost, dead_cost, 0.0]])
    labels = np.full(len(proba), "D", dtype="<U1")
    for start, stop in periods:
        if stop > start:
            labels[start:stop] = STATES[_decode_span(score[start:stop], cost)]
    return labels
