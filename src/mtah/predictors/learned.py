"""Learned predictor: tracking features -> gradient-boosted P(H, A, D) -> Viterbi decoding.

Trained only on external matches (IDSSE), degraded the same way as the bench. Never on the match
(R2) and never on the public 5 minutes (R3). Deterministic: random_state=0, no early stopping.
"""

import numpy as np

from mtah.decode import viterbi
from mtah.features import FEATURE_NAMES, frame_features
from mtah.schema import MatchTracking

CLASSES = np.array(["H", "A", "D"])


class LearnedPredictor:
    def __init__(self, switch_cost: float = 8.0, dead_cost: float = 8.0, max_iter: int = 300,
                 drop: tuple[str, ...] = (), stride: int = 1):
        unknown = set(drop) - set(FEATURE_NAMES)
        if unknown:
            raise ValueError(f"unknown features to drop: {sorted(unknown)}")
        self.keep = np.array([i for i, n in enumerate(FEATURE_NAMES) if n not in drop])
        self.stride = stride  # train on every stride-th labelled frame
        self.n_train = 0
        self.switch_cost = switch_cost
        self.dead_cost = dead_cost
        self.max_iter = max_iter
        self.model = None
        self.prior = np.full(3, 1 / 3)
        self.trained_with = ""  # config_tag of the degradation used for training

    def fit(self, tracks: list[MatchTracking], labels: list[np.ndarray]) -> "LearnedPredictor":
        from sklearn.ensemble import HistGradientBoostingClassifier

        xs, ys = [], []
        for track, label in zip(tracks, labels, strict=True):
            features = frame_features(track)[:, self.keep]
            inside = np.zeros(track.n_frames(), dtype=bool)
            for start, stop in track.periods:
                inside[start:stop] = True
            keep = inside & np.isin(label, CLASSES)
            xs.append(features[keep])
            ys.append(np.select([label[keep] == c for c in CLASSES], [0, 1, 2]))
        x, y = np.concatenate(xs)[::self.stride], np.concatenate(ys)[::self.stride]
        self.n_train = len(y)
        self.model = HistGradientBoostingClassifier(
            max_iter=self.max_iter, learning_rate=0.05, max_leaf_nodes=63,
            l2_regularization=1.0, early_stopping=False, random_state=0).fit(x, y)
        self.prior = np.bincount(y, minlength=3) / len(y)
        return self

    def proba(self, track: MatchTracking) -> np.ndarray:
        """(T, 3) probabilities, columns H, A, D."""
        raw = self.model.predict_proba(frame_features(track)[:, self.keep])
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


def config_tag(cfg) -> str:
    """Short hash of a DegradeConfig: says which config trained a model without printing it."""
    import hashlib
    import json
    from dataclasses import asdict

    return hashlib.sha256(json.dumps(asdict(cfg), sort_keys=True).encode()).hexdigest()[:8]


def degraded_external(match_ids, seed: int, cfg):
    """(tracks, labels) for external matches, each degraded with its own reproducible seed."""
    from mtah.degrade import degrade
    from mtah.eval.harness import match_seed
    from mtah.io.external import load_external

    tracks, labels = [], []
    for match_id in match_ids:
        clean, label = load_external(match_id)
        tracks.append(degrade(clean, cfg, np.random.default_rng(match_seed(seed, match_id))))
        labels.append(label)
    return tracks, labels


def train_on_external(seed: int = 1, cfg=None, scenarios=None, **params) -> LearnedPredictor:
    """Fit on all 7 IDSSE matches, each degraded once per scenario (seed + index), every
    `len(scenarios)`-th frame kept. This is what the submission uses. Defaults: all SCENARIOS
    (run 5, D-003) on top of load_config(), i.e. the measured local config when present."""
    from mtah.degrade import SCENARIOS, load_config, scenario
    from mtah.io.external import IDSSE_MATCHES

    cfg = load_config() if cfg is None else cfg
    scenarios = list(SCENARIOS) if scenarios is None else list(scenarios)
    tracks, labels = [], []
    for index, name in enumerate(scenarios):
        t, lab = degraded_external(IDSSE_MATCHES, seed + index, scenario(cfg, name))
        tracks += t
        labels += lab
    params.setdefault("stride", len(scenarios))
    model = LearnedPredictor(**params).fit(tracks, labels)
    model.trained_with = config_tag(cfg)
    return model


_FITTED = None


def predict_learned(track: MatchTracking) -> np.ndarray:
    """Registry entry: fit on all external IDSSE matches once per process, then predict."""
    global _FITTED
    if _FITTED is None:
        _FITTED = train_on_external()
    return _FITTED(track)
