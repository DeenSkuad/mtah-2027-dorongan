import pytest

from mtah.degrade import DegradeConfig
from mtah.eval.harness import bench
from mtah.predictors import PREDICTORS


@pytest.mark.network
def test_bench_runs():
    picks = {k: PREDICTORS[k] for k in ("baseline25", "baseline125")}
    table = bench(picks, ["J03WMX"], DegradeConfig(), seed=0)
    assert len(table) == 4
    assert table["spell_f1"].between(0, 1).all()


def test_means_are_per_source_never_pooled():
    import pandas as pd

    from mtah.eval.harness import summarise

    rows = pd.DataFrame({"predictor": ["p", "p", "p"],
                         "match": ["J03WMX", "J03WN1", "metrica1"],
                         "spell_f1": [0.2, 0.4, 0.9]})
    means = summarise(rows).set_index("match")["spell_f1"]
    assert means["MEAN idsse"] == pytest.approx(0.3)
    assert means["MEAN metrica"] == pytest.approx(0.9)
    assert "MEAN" not in means.index


def test_source_of():
    from mtah.eval.harness import source_of

    assert source_of("J03WMX") == "idsse"
    assert source_of("metrica2") == "metrica"


def test_bench_learned_folds_exclude_heldout(monkeypatch):
    import numpy as np

    from mtah.eval.harness import bench_learned
    from mtah.io import external
    from mtah.schema import MatchTracking

    sizes = {"J1": 200, "J2": 210, "J3": 220, "metrica1": 230}

    def fake_load(match_id):
        T = sizes[match_id]
        players = np.zeros((T, 2, 2), dtype=np.float32)
        ball = np.ones((T, 2), dtype=np.float32)
        track = MatchTracking(players, np.array([0, 1], dtype=np.int8), ball,
                              ((0, T // 2), (T // 2, T)), (105.0, 68.0), 25)
        return track, np.array(["H", "A"] * (T // 2), dtype="<U1")

    fits = []

    class Fake:
        def fit(self, tracks, labels):
            fits.append(sorted(t.n_frames() for t in tracks))
            return self

        def proba(self, track):
            return np.full((track.n_frames(), 3), 1 / 3)

        def decode(self, proba, periods, switch_cost=None, dead_cost=None):
            return np.full(len(proba), "H", dtype="<U1")

    monkeypatch.setattr(external, "load_external", fake_load)
    monkeypatch.setattr(external, "IDSSE_MATCHES", ("J1", "J2", "J3"))
    table = bench_learned(Fake, {"a": (1, 1), "b": (2, 2)}, list(sizes), DegradeConfig(), seed=0)

    assert fits == [[210, 220], [200, 220], [200, 210], [200, 210, 220]]
    per_match = table[~table["match"].str.startswith("MEAN")]
    assert len(per_match) == 2 * 4
    assert set(table["match"]) >= {"MEAN idsse", "MEAN metrica"}


def _fake_matches(monkeypatch, ids):
    import numpy as np

    from mtah.io import external
    from mtah.schema import MatchTracking

    def fake_load(match_id):
        T = 200
        track = MatchTracking(np.zeros((T, 2, 2), np.float32), np.array([0, 1], np.int8),
                              np.ones((T, 2), np.float32), ((0, T),), (105.0, 68.0), 25)
        return track, np.array(["H", "A"] * (T // 2), dtype="<U1")

    monkeypatch.setattr(external, "load_external", fake_load)
    monkeypatch.setattr(external, "IDSSE_MATCHES", tuple(ids))


class _Recorder:
    sizes: list = []

    def fit(self, tracks, labels):
        _Recorder.sizes.append(len(tracks))
        return self

    def proba(self, track):
        import numpy as np

        return np.full((track.n_frames(), 3), 1 / 3)

    def decode(self, proba, periods, switch_cost=None, dead_cost=None):
        import numpy as np

        return np.full(len(proba), "H", dtype="<U1")


def test_unknown_scenario_fails_before_loading(monkeypatch):
    from mtah.eval.harness import bench_learned
    from mtah.io import external

    def boom(match_id):
        raise AssertionError("loaded before validating scenarios")

    monkeypatch.setattr(external, "load_external", boom)
    with pytest.raises(KeyError):
        bench_learned(_Recorder, {"a": (1, 1)}, ["J1"], DegradeConfig(), eval_scenarios=["edgy"])


def test_train_scenarios_multiply_training_tracks_and_name_rows(monkeypatch):
    from mtah.eval.harness import bench_learned

    _fake_matches(monkeypatch, ["J1", "J2", "J3"])
    _Recorder.sizes = []
    table = bench_learned(_Recorder, {"a": (1, 1)}, ["J1", "J2", "J3"], DegradeConfig(),
                          train_scenarios=["default", "edge"], eval_scenarios=["default", "all"])
    assert _Recorder.sizes == [4, 4, 4]
    assert {"a@default", "a@all"} == set(table["predictor"])
