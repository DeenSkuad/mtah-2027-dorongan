import subprocess
import sys


def test_match_module_finds_upstream_games_from_any_cwd(tmp_path):
    code = "from mtah.io.match import _import_games; print(_import_games().__name__)"
    out = subprocess.run([sys.executable, "-c", code], cwd=tmp_path, capture_output=True,
                         text=True)
    assert out.returncode == 0, out.stderr[-300:]
    assert out.stdout.strip() == "games"
