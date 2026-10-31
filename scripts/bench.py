"""Model selection: score predictors on degraded external matches (never on the match, R3).

    python scripts/bench.py --predictors baseline25,baseline125 --matches all
"""

import argparse
from datetime import datetime

from mtah.constants import REPO_ROOT
from mtah.degrade import load_config
from mtah.eval.harness import bench
from mtah.io.external import IDSSE_MATCHES
from mtah.predictors import PREDICTORS


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictors", default=",".join(PREDICTORS))
    parser.add_argument("--matches", default="all")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    names = args.predictors.split(",")
    matches = IDSSE_MATCHES if args.matches == "all" else args.matches.split(",")
    table = bench({n: PREDICTORS[n] for n in names}, matches, load_config(), seed=args.seed)

    print(table.round(4).to_string(index=False))
    out = REPO_ROOT / "docs" / "bench" / f"{datetime.now():%Y%m%d-%H%M%S}.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(out, index=False)
    print(f"\nsaved {out.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
