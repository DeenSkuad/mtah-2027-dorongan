import numpy as np
import pandas as pd
import pytest

from mtah.io.metrica import METRICA_MATCHES, _labels_from_events, load_metrica

COLUMNS = ["Team", "Type", "Subtype", "Period", "Start Frame", "End Frame"]


def events(*rows):
    return pd.DataFrame(rows, columns=COLUMNS)


def labels(evs, n, period_ids=None):
    frame_ids = np.arange(1, n + 1)
    period_ids = np.ones(n, dtype=int) if period_ids is None else np.asarray(period_ids)
    return "".join(_labels_from_events(evs, frame_ids, period_ids))


def test_owner_carries_forward_until_the_other_team_acts():
    evs = events(("Away", "SET PIECE", "KICK OFF", 1, 2, 2),
                 ("Away", "PASS", None, 1, 2, 4),
                 ("Away", "BALL LOST", "INTERCEPTION", 1, 5, 7),
                 ("Home", "RECOVERY", None, 1, 7, 7))
    assert labels(evs, 9) == "DAAAAAHHH"


def test_ball_out_is_dead_from_its_end_frame_until_the_restart():
    evs = events(("Home", "PASS", None, 1, 1, 1),
                 ("Home", "BALL OUT", "CLEARANCE", 1, 2, 4),
                 ("Away", "SET PIECE", "THROW IN", 1, 7, 7))
    assert labels(evs, 8) == "HHHDDDAA"


def test_foul_is_dead_from_its_start_frame():
    evs = events(("Home", "PASS", None, 1, 1, 1),
                 ("Away", "FAULT RECEIVED", None, 1, 3, 3),
                 ("Away", "SET PIECE", "FREE KICK", 1, 5, 5))
    assert labels(evs, 6) == "HHDDAA"


def test_goal_and_off_target_shots_end_play_but_saved_shots_do_not():
    goal = events(("Home", "SHOT", "ON TARGET-GOAL", 1, 1, 3),
                  ("Away", "SET PIECE", "KICK OFF", 1, 6, 6))
    assert labels(goal, 6) == "HHDDDA"
    out = events(("Home", "SHOT", "HEAD-OFF TARGET-OUT", 1, 1, 2))
    assert labels(out, 3) == "HDD"
    saved = events(("Home", "SHOT", "ON TARGET-SAVED", 1, 1, 2))
    assert labels(saved, 3) == "HHH"


def test_challenges_and_cards_do_not_change_possession():
    evs = events(("Home", "PASS", None, 1, 1, 1),
                 ("Away", "CHALLENGE", "GROUND-LOST", 1, 2, 2),
                 ("Away", "CARD", "YELLOW", 1, 3, 3))
    assert labels(evs, 4) == "HHHH"


def test_nothing_carries_across_a_period_boundary():
    evs = events(("Home", "PASS", None, 1, 1, 1),
                 ("Away", "SET PIECE", "KICK OFF", 2, 5, 5))
    assert labels(evs, 6, period_ids=[1, 1, 1, 2, 2, 2]) == "HHHDAA"


def test_match_list():
    assert METRICA_MATCHES == ("metrica1", "metrica2")


def test_external_registry_dispatches_by_match_id(monkeypatch):
    from mtah.io import external, metrica

    monkeypatch.setattr(metrica, "load_metrica", lambda m: ("metrica", m))
    monkeypatch.setattr(external, "load_idsse", lambda m: ("idsse", m))
    assert external.EXTERNAL_MATCHES == external.IDSSE_MATCHES + METRICA_MATCHES
    assert external.load_external("metrica2") == ("metrica", "metrica2")
    assert external.load_external("J03WMX") == ("idsse", "J03WMX")


@pytest.mark.network
@pytest.mark.parametrize("match_id", METRICA_MATCHES)
def test_load_one(match_id):
    track, labs = load_metrica(match_id)
    track.validate()
    assert len(labs) == track.n_frames()
    assert set(np.unique(labs)) <= {"H", "A", "D"}
    alive = labs != "D"
    assert 0.3 < (labs[alive] == "H").mean() < 0.7
    assert 0.05 < (labs == "D").mean() < 0.5
    assert len(track.periods) == 2
    assert track.fps == 25
