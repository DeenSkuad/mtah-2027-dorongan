import importlib

from mtah import constants
from mtah.constants import LABELS, A, D, H, X, official_metrics


def test_codes_match_official():
    metrics = official_metrics()
    assert metrics.LABELS == LABELS
    assert (H, A, D, X) == (0, 1, 2, 3)
    assert (metrics.H, metrics.A, metrics.D, metrics.X) == (H, A, D, X)


def test_data_dir_env(monkeypatch, tmp_path):
    monkeypatch.setenv("MTAH_DATA_DIR", str(tmp_path))
    reloaded = importlib.reload(constants)
    assert reloaded.DATA_DIR == tmp_path
    monkeypatch.delenv("MTAH_DATA_DIR")
    importlib.reload(constants)
