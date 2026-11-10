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
