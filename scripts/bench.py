"""Model selection: score predictors on degraded external matches (never on the match, R3).

    python scripts/bench.py --predictors baseline25,baseline125 --matches all
    python scripts/bench.py --learned            # + learned model, leave-one-match-out, cost grid
"""

import argparse
from datetime import datetime

import pandas as pd

from mtah.constants import REPO_ROOT
from mtah.degrade import load_config
from mtah.eval.harness import bench, bench_learned
from mtah.io.external import EXTERNAL_MATCHES
from mtah.predictors import PREDICTORS
from mtah.predictors.learned import LearnedPredictor

SWITCH_GRID = (2, 4, 8, 16, 32)
DEAD_GRID = (1, 2, 4, 8)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictors", default="baseline50")
    parser.add_argument("--matches", default="all")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--learned", action="store_true")
    args = parser.parse_args()

    names = [n for n in args.predictors.split(",") if n != "learned"]
    matches = EXTERNAL_MATCHES if args.matches == "all" else args.matches.split(",")
    cfg = load_config()
    tables = [bench({n: PREDICTORS[n] for n in names}, matches, cfg, seed=args.seed)]
    if args.learned:
        decoders = {f"learned_s{s}_d{d}": (s, d) for s in SWITCH_GRID for d in DEAD_GRID}
        tables.append(bench_learned(LearnedPredictor, decoders, matches, cfg, seed=args.seed))
    table = pd.concat(tables, ignore_index=True)

    means = table[table["match"].str.startswith("MEAN")]
    print(means.sort_values(["match", "spell_f1"], ascending=[True, False])
          .round(4).to_string(index=False))
    out = REPO_ROOT / "docs" / "bench" / f"{datetime.now():%Y%m%d-%H%M%S}.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(out, index=False)
    print(f"\nsaved {out.relative_to(REPO_ROOT)} (per-match rows inside)")


if __name__ == "__main__":
    main()
