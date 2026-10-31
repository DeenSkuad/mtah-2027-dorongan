"""Build the team submission. Placeholder: promotes the best baseline until src/possession lands."""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
src = ROOT / "evaluation/results/baseline_smooth125.csv"
dst = ROOT / "evaluation/results/team_v0.csv"
shutil.copyfile(src, dst)
print(f"wrote {dst.relative_to(ROOT)}")
