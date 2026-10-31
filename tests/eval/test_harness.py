import numpy as np
import pytest

from mtah.constants import N_MATCH_FRAMES, REPO_ROOT, official_metrics
from mtah.eval.harness import score
from mtah.report import summary


def labels(text):
    return np.array(list(text), dtype="<U1")


def test_perfect():
    gt = labels("HHHHHAAAAADDDHHHH")
    result = score(gt, gt.copy(), ((0, len(gt)),))
    assert result["spell_f1"] == 1.0
    assert result["n_gt_spells"] == 3


def test_period_boundary_not_merged():
    gt = labels("H" * 100)
    result = score(gt, gt.copy(), ((0, 50), (50, 100)))
    assert result["n_gt_spells"] == 2
    assert result["spell_f1"] == 1.0


def test_matches_official_on_public_gt():
    metrics = official_metrics()
    gt = metrics.read_label_csv(REPO_ROOT / "evaluation/gt/BAR-ATH_possession_gt_public.csv")
    pred = metrics.read_label_csv(REPO_ROOT / "evaluation/results/baseline_smooth125.csv")
    result = score(gt["label"].to_numpy(dtype="<U1"), pred["label"].to_numpy(dtype="<U1"),
                   ((0, N_MATCH_FRAMES),))
    assert result["spell_f1"] == pytest.approx(0.4242, abs=1e-4)


def test_summary_has_no_arrays():
    gt = labels("HHHAAA")
    line = summary("x", score(gt, gt.copy(), ((0, 6),)))
    assert "[" not in line and len(line) < 200


def test_match_seed_independent_of_order():
    from mtah.eval.harness import match_seed

    assert match_seed(0, "J03WN1") == match_seed(0, "J03WN1")
    assert match_seed(0, "J03WN1") != match_seed(0, "J03WMX")
    assert match_seed(1, "J03WN1") != match_seed(0, "J03WN1")
