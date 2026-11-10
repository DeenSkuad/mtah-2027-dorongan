"""Learned predictor: tracking features -> gradient-boosted P(H, A, D) -> Viterbi decoding.

Trained only on external matches (IDSSE), degraded the same way as the bench. Never on the match
(R2) and never on the public 5 minutes (R3). Deterministic: random_state=0, no early stopping.
"""

import numpy as np

from mtah.decode import viterbi
from mtah.features import frame_features
from mtah.schema import MatchTracking

CLASSES = np.array(["H", "A", "D"])


class LearnedPredictor:
    def __init__(self, switch_cost: float = 8.0, dead_cost: float = 4.0, max_iter: int = 300):
        self.switch_cost = switch_cost
        self.dead_cost = dead_cost
        self.max_iter = max_iter
        self.model = None
        self.prior = np.full(3, 1 / 3)

    def fit(self, tracks: list[MatchTracking], labels: list[np.ndarray]) -> "LearnedPredictor":
        from sklearn.ensemble import HistGradientBoostingClassifier

        xs, ys = [], []
        for track, label in zip(tracks, labels, strict=True):
            features = frame_features(track)
            inside = np.zeros(track.n_frames(), dtype=bool)
            for start, stop in track.periods:
                inside[start:stop] = True
            keep = inside & np.isin(label, CLASSES)
            xs.append(features[keep])
            ys.append(np.select([label[keep] == c for c in CLASSES], [0, 1, 2]))
        x, y = np.concatenate(xs), np.concatenate(ys)
        self.model = HistGradientBoostingClassifier(
            max_iter=self.max_iter, learning_rate=0.05, max_leaf_nodes=63,
            l2_regularization=1.0, early_stopping=False, random_state=0).fit(x, y)
        self.prior = np.bincount(y, minlength=3) / len(y)
        return self

    def proba(self, track: MatchTracking) -> np.ndarray:
        """(T, 3) probabilities, columns H, A, D."""
        raw = self.model.predict_proba(frame_features(track))
        proba = np.zeros((len(raw), 3))
        proba[:, self.model.classes_] = raw
        return proba

    def decode(self, proba: np.ndarray, periods, switch_cost: float | None = None,
               dead_cost: float | None = None) -> np.ndarray:
        return viterbi(proba, periods,
                       self.switch_cost if switch_cost is None else switch_cost,
                       self.dead_cost if dead_cost is None else dead_cost,
                       prior=self.prior)

    def __call__(self, track: MatchTracking) -> np.ndarray:
        return self.decode(self.proba(track), track.periods)


def degraded_external(match_ids, seed: int):
    """(tracks, labels) for external matches, each degraded with its own reproducible seed."""
    from mtah.degrade import degrade, load_config
    from mtah.eval.harness import match_seed
    from mtah.io.external import load_external

    cfg = load_config()
    tracks, labels = [], []
    for match_id in match_ids:
        clean, label = load_external(match_id)
        tracks.append(degrade(clean, cfg, np.random.default_rng(match_seed(seed, match_id))))
        labels.append(label)
    return tracks, labels


def train_on_external(seed: int = 1, **params) -> LearnedPredictor:
    """Fit on all 7 IDSSE matches (degraded with `seed`); what the submission uses."""
    from mtah.io.external import IDSSE_MATCHES

    return LearnedPredictor(**params).fit(*degraded_external(IDSSE_MATCHES, seed))
