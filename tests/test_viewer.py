import base64

import numpy as np

from mtah.schema import MatchTracking
from mtah.viewer import NAN, rle, viewer_payload


def track(T=100):
    players = np.full((T, 3, 2), np.nan, dtype=np.float32)
    players[:, 0] = (10.0, 20.0)
    players[:, 1] = (60.0, 30.0)
    players[:, 2] = (52.0, 34.0)  # referee
    ball = np.full((T, 2), np.nan, dtype=np.float32)
    ball[::2] = (11.0, 21.0)
    return MatchTracking(players, np.array([0, 1, -1], np.int8), ball, ((0, 50), (50, 100)),
                         (105.0, 68.0), 25)


def decode(b64, shape):
    return np.frombuffer(base64.b64decode(b64), dtype="<i2").reshape(shape)


def test_rle_covers_every_frame():
    labels = np.array(list("HHHDDAAH"))
    assert rle(labels) == [[0, 3, "H"], [3, 5, "D"], [5, 7, "A"], [7, 8, "H"]]


def test_payload_samples_every_step_and_drops_referee():
    t = track()
    labels = np.array(["H"] * 40 + ["D"] * 20 + ["A"] * 40)
    p = viewer_payload(t, labels, home="BAR", away="ATH", step=5)
    assert p["meta"]["n_frames"] == 100 and p["meta"]["step"] == 5
    assert p["meta"]["periods"] == [[0, 50], [50, 100]]
    assert p["team"] == [0, 1]
    players = decode(p["players"], (20, 2, 2))
    assert (players[:, 0] == (100, 200)).all()  # decimetres
    ball = decode(p["ball"], (20, 2))
    assert (ball[0] == (110, 210)).all()
    assert (ball[1] == NAN).all()
    assert p["pred"] == [[0, 40, "H"], [40, 60, "D"], [60, 100, "A"]]
    assert "truth" not in p


def test_truth_included_only_when_given():
    t = track()
    labels = np.array(["H"] * 100)
    assert viewer_payload(t, labels, "A", "B", truth=labels)["truth"] == [[0, 100, "H"]]
