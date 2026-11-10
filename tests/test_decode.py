import numpy as np

from mtah.decode import viterbi


def block(T, label, p=0.9):
    proba = np.full((T, 3), (1 - p) / 2)
    proba[:, "HAD".index(label)] = p
    return proba


def transitions(labels):
    return int((labels[1:] != labels[:-1]).sum())


def test_zero_costs_equal_argmax():
    rng = np.random.default_rng(0)
    proba = rng.dirichlet(np.ones(3), size=500)
    labels = viterbi(proba, ((0, 500),), switch_cost=0, dead_cost=0)
    assert "".join(labels) == "".join(np.array(list("HAD"))[proba.argmax(axis=1)])


def test_switch_cost_removes_short_flicker():
    proba = np.vstack([block(50, "H"), block(3, "A", p=0.6), block(47, "H")])
    labels = viterbi(proba, ((0, 100),), switch_cost=5, dead_cost=5)
    assert set(labels) == {"H"}


def test_long_switch_survives():
    proba = np.vstack([block(100, "H"), block(200, "A"), block(100, "H")])
    labels = viterbi(proba, ((0, 400),), switch_cost=5, dead_cost=5)
    assert transitions(labels) == 2
    assert (labels[100:300] == "A").all()


def test_dead_run_kept():
    proba = np.vstack([block(100, "H"), block(100, "D"), block(100, "H")])
    labels = viterbi(proba, ((0, 300),), switch_cost=5, dead_cost=5)
    assert (labels[100:200] == "D").all()
    assert transitions(labels) == 2


def test_periods_independent():
    proba = np.vstack([block(100, "H"), block(100, "A")])
    labels = viterbi(proba, ((0, 100), (100, 200)), switch_cost=1e6, dead_cost=1e6)
    assert (labels[:100] == "H").all() and (labels[100:] == "A").all()


def test_frames_outside_periods_are_dead():
    labels = viterbi(block(30, "H"), ((5, 25),), switch_cost=1, dead_cost=1)
    assert "".join(labels) == "D" * 5 + "H" * 20 + "D" * 5


def test_all_equal_proba():
    labels = viterbi(np.full((100, 3), 1 / 3), ((0, 60), (60, 100)), switch_cost=2, dead_cost=2)
    assert len(set(labels[:60])) == 1 and len(set(labels[60:])) == 1
    assert set(labels) <= {"H", "A", "D"}


def test_prior_shifts_decision():
    proba = np.tile([0.3, 0.2, 0.5], (50, 1))
    assert set(viterbi(proba, ((0, 50),), 0, 0)) == {"D"}
    prior = np.array([0.2, 0.2, 0.6])
    assert set(viterbi(proba, ((0, 50),), 0, 0, prior=prior)) == {"H"}
