"""R1 guard: no tool call may point Claude at match data."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "guard_match_data.py"


def _load_hook():
    spec = importlib.util.spec_from_file_location("guard_match_data", HOOK)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BLOCKED = [
    ("Read", {"file_path": "/x/barcelona/data/tactical/BAR-ATH_tactical_atd.txt"}),
    ("Grep", {"pattern": "ball", "path": "data/"}),
    ("Glob", {"pattern": "data/**/*.csv"}),
    ("Bash", {"command": "head -5 data/tactical/BAR-ATH_tactical_atd.txt"}),
    ("Bash", {"command": "python -c \"open('data/x')\""}),
    ("Bash", {"command": "ffmpeg -i BAR-ATH_tactical.mp4 f.png"}),
    ("Bash", {"command": "cat ~/mtah/BAR-ATH_broadcast_homography.csv"}),
    ("Read", {"file_path": "config/degradation.local.json"}),
    ("NotebookEdit", {"notebook_path": "data/x.ipynb"}),
    # review C3: bypasses that must also be blocked
    ("Bash", {"command": "make submission"}),
    ("Bash", {"command": "make measure"}),
    ("Bash", {"command": "make baseline"}),
    ("Bash", {"command": "make eval"}),
    ("Bash", {"command": ".venv/bin/python -m pytest -m match -q"}),
    ("Bash", {"command": "cd data && cat x"}),
    ("Bash", {"command": "cat \"data\"/x"}),
    ("Bash", {"command": "D=data; cat $D/x"}),
    ("Bash", {"command": "git show HEAD:data/x"}),
    ("Bash", {"command": "cat x.MP4"}),
    ("Bash", {"command": "cat config/*.local*"}),
    ("Bash", {"command": "grep -r ball ."}),
    ("Bash", {"command": "find . -name '*.txt'"}),
    ("Bash", {"command": "python scripts/make_submission.py"}),
    ("Bash", {"command": "python scripts/measure_degradation.py"}),
    ("Grep", {"pattern": "x", "path": "data"}),
]

ALLOWED = [
    ("Read", {"file_path": "evaluation/gt/BAR-ATH_possession_gt_public.csv"}),
    ("Read", {"file_path": "data/README.md"}),
    ("Bash", {"command": "make bench"}),
    ("Bash", {"command": "pytest -q"}),
    ("Bash", {"command": "make test && make lint"}),
    ("Bash", {"command": "echo $MTAH_DATA_DIR"}),
    ("Read", {"file_path": "src/mtah/io/metadata.py"}),
    # file *content* is code Claude writes, never match data: only paths/commands are scanned
    ("Write", {"file_path": "tests/test_x.py", "content": "p = 'data/tactical/x_atd.txt'"}),
]


@pytest.mark.parametrize("tool,tool_input", BLOCKED)
def test_blocks(tool, tool_input):
    assert _load_hook().is_blocked(tool, tool_input)


@pytest.mark.parametrize("tool,tool_input", ALLOWED)
def test_allows(tool, tool_input):
    assert _load_hook().is_blocked(tool, tool_input) is None


def test_exit_code():
    payload = json.dumps({"tool_name": BLOCKED[0][0], "tool_input": BLOCKED[0][1]})
    result = subprocess.run([sys.executable, str(HOOK)], input=payload, text=True,
                            capture_output=True)
    assert result.returncode == 2
    assert "R1" in result.stderr


def test_exit_code_allowed():
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": "ls"}})
    result = subprocess.run([sys.executable, str(HOOK)], input=payload, text=True,
                            capture_output=True)
    assert result.returncode == 0
