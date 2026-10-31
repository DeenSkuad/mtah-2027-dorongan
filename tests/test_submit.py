import numpy as np
import pytest

from mtah.constants import N_MATCH_FRAMES
from mtah.submit import write_submission


def good():
    return np.full(N_MATCH_FRAMES, "H", dtype="<U1")


def test_rejects_bad_length(tmp_path):
    with pytest.raises(ValueError):
        write_submission(good()[:-1], tmp_path / "t.csv")
    assert not (tmp_path / "t.csv").exists()


def test_rejects_bad_label(tmp_path):
    labels = good()
    labels[10] = "Q"
    with pytest.raises(ValueError):
        write_submission(labels, tmp_path / "t.csv")
    assert not (tmp_path / "t.csv").exists()


def test_roundtrip_valid(tmp_path):
    labels = good()
    labels[::7] = "D"
    path = write_submission(labels, tmp_path / "team.csv")
    first = path.read_text().splitlines()[:2]
    assert first == ["frame,label", "0,D"]
