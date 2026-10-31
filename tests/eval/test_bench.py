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
