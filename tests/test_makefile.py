"""`make submission` must build the submitted model under the team name, after `make measure`.

Dry run only (`make -n`): nothing is executed and no match data is read.
"""

import shutil
import subprocess

import pytest

from mtah.constants import REPO_ROOT

pytestmark = pytest.mark.skipif(shutil.which("make") is None, reason="make not installed")


def _dry_run(target: str) -> list[str]:
    out = subprocess.run(["make", "-n", target], cwd=REPO_ROOT, capture_output=True, text=True,
                         check=True).stdout
    return out.splitlines()


def test_submission_measures_first_then_builds_learned_dorongan_and_validates():
    lines = _dry_run("submission")
    measure = next(i for i, line in enumerate(lines) if "measure_degradation.py" in line)
    build = next(i for i, line in enumerate(lines) if "make_submission.py" in line)
    assert measure < build
    assert "--predictor learned" in lines[build]
    assert "--name Dorongan" in lines[build]
    assert any("validate_submission.py evaluation/results/Dorongan.csv" in line
               for line in lines[build:])


def test_setup_installs_the_pinned_lock():
    assert any("-r requirements/lock.txt" in line for line in _dry_run("setup"))
