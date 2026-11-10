import numpy as np
import pytest

from mtah.schema import MatchTracking

PITCH = (105.0, 68.0)


def synthetic(seed: int, T: int = 3000):
    """Ball wanders; label = team of the nearest player, D while the ball is off the pitch."""
    rng = np.random.default_rng(seed)
    players = rng.uniform((0, 0), PITCH, size=(1, 6, 2)) + np.cumsum(
        rng.normal(0, 0.15, size=(T, 6, 2)), axis=0)
    players = np.clip(players, 1, (104, 67)).astype(np.float32)
    team = np.array([0, 0, 0, 1, 1, 1], dtype=np.int8)
    owner = np.repeat(rng.integers(0, 6, size=T // 100 + 1), 100)[:T]
    ball = players[np.arange(T), owner] + np.float32(0.4)
    out = np.zeros(T, dtype=bool)
    for start in rng.integers(0, T - 60, size=6):
        out[start:start + 50] = True
    ball[out] = (-3.0, 30.0)
    labels = np.where(out, "D", np.where(team[owner] == 0, "H", "A")).astype("<U1")
    half = T // 2
    return MatchTracking(players, team, ball, ((0, half), (half, T)), PITCH, 25), labels


@pytest.fixture(scope="module")
def train():
    pairs = [synthetic(s) for s in (1, 2)]
    return [p[0] for p in pairs], [p[1] for p in pairs]


def test_fit_predict_learns_simple_rule(train):
    from mtah.predictors.learned import LearnedPredictor

    model = LearnedPredictor(max_iter=60).fit(*train)
    track, labels = synthetic(3)
    assert (model(track) == labels).mean() > 0.9


def test_deterministic(train):
    from mtah.predictors.learned import LearnedPredictor

    track, _ = synthetic(3)
    first = LearnedPredictor(max_iter=30).fit(*train)(track)
    second = LearnedPredictor(max_iter=30).fit(*train)(track)
    assert np.array_equal(first, second)


def test_labels_alphabet_and_length_with_empty_frames(train):
    from mtah.predictors.learned import LearnedPredictor

    model = LearnedPredictor(max_iter=30).fit(*train)
    track, _ = synthetic(4)
    players = track.players.copy()
    players[100:200] = np.nan
    blank = MatchTracking(players, track.team_of_slot, track.ball, track.periods, PITCH, 25)
    labels = model(blank)
    assert len(labels) == blank.n_frames()
    assert set(labels) <= {"H", "A", "D"}


def test_decode_override_costs(train):
    from mtah.predictors.learned import LearnedPredictor

    model = LearnedPredictor(max_iter=30).fit(*train)
    track, _ = synthetic(3)
    proba = model.proba(track)
    assert proba.shape == (track.n_frames(), 3)
    np.testing.assert_allclose(proba.sum(axis=1), 1, atol=1e-6)
    expected = np.array(list("HAD"))[(np.log(proba + 1e-6) - np.log(model.prior)).argmax(axis=1)]
    got = model.decode(proba, track.periods, switch_cost=0, dead_cost=0)
    assert np.array_equal(got, expected)


def test_registry_trains_once_lazily(monkeypatch):
    from mtah.predictors import PREDICTORS, learned

    calls = []

    class Fitted:
        def __call__(self, track):
            return np.full(track.n_frames(), "H", dtype="<U1")

    def fake_train(**kw):
        calls.append(kw)
        return Fitted()

    monkeypatch.setattr(learned, "train_on_external", fake_train)
    monkeypatch.setattr(learned, "_FITTED", None)
    track, _ = synthetic(5, T=200)
    assert set(PREDICTORS["learned"](track)) == {"H"}
    PREDICTORS["learned"](track)
    assert len(calls) == 1


def test_defaults_are_the_bench_winner():
    """Run 4 in docs/EXPERIMENTS.md picked switch 8, dead 8 on MEAN idsse. Change both together."""
    from mtah.predictors.learned import LearnedPredictor

    model = LearnedPredictor()
    assert (model.switch_cost, model.dead_cost) == (8.0, 8.0)


def test_train_on_external_records_config_tag(monkeypatch, train):
    from mtah.degrade import DegradeConfig
    from mtah.predictors import learned

    monkeypatch.setattr(learned, "degraded_external", lambda ids, seed, cfg: train)
    a = learned.train_on_external(cfg=DegradeConfig(), max_iter=5)
    b = learned.train_on_external(cfg=DegradeConfig(ball_missing_frac=0.5), max_iter=5)
    assert len(a.trained_with) == 8 and a.trained_with != b.trained_with
    assert learned.config_tag(DegradeConfig()) == a.trained_with
