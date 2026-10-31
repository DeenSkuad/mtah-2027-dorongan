from types import SimpleNamespace as NS

import numpy as np
import pytest

from mtah.io.external import IDSSE_MATCHES, _labels_from_frames, load_idsse

HOME, AWAY = NS(name="home"), NS(name="away")


def frame(state, owner):
    return NS(ball_state=NS(value=state), ball_owning_team=owner)


def test_label_mapping():
    frames = [frame("alive", HOME), frame("alive", AWAY), frame("dead", HOME),
              frame("alive", None), frame("alive", HOME)]
    assert "".join(_labels_from_frames(frames, HOME)) == "HADAH"


def test_owner_missing_carries_last_alive_owner():
    frames = [frame("alive", AWAY), frame("alive", None), frame("alive", None)]
    assert "".join(_labels_from_frames(frames, HOME)) == "AAA"


def test_match_list():
    assert len(IDSSE_MATCHES) == 7


@pytest.mark.network
def test_load_one(tmp_path):
    track, labels = load_idsse(IDSSE_MATCHES[0])
    track.validate()
    assert set(np.unique(labels)) <= {"H", "A", "D"}
    assert 0.3 < (labels == "H").mean() < 0.7
    assert (labels == "D").mean() > 0.05
    assert len(track.periods) == 2
