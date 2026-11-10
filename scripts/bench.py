"""Model selection: score predictors on degraded external matches (never on the match, R3).

    python scripts/bench.py --predictors baseline25,baseline125 --matches all
    python scripts/bench.py --learned --grid     # + learned model, leave-one-match-out, cost grid
    python scripts/bench.py --learned --train mix --eval default,edge,slow,players,all \
        --drop ball_seen,since_seen               # robustness matrix / feature ablation
"""

import argparse
from datetime import datetime

import pandas as pd

from mtah.constants import REPO_ROOT
from mtah.degrade import SCENARIOS, load_config
from mtah.eval.harness import bench, bench_learned
from mtah.io.external import EXTERNAL_MATCHES
from mtah.predictors import PREDICTORS
from mtah.predictors.learned import LearnedPredictor

SWITCH_GRID = (2, 4, 8, 16, 32)
DEAD_GRID = (1, 2, 4, 8)
NEAR_WINNER = {"learned_s8_d8": (8, 8), "learned_s8_d4": (8, 4), "learned_s16_d8": (16, 8)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictors", default="baseline50")
    parser.add_argument("--matches", default="all")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--learned", action="store_true")
    parser.add_argument("--grid", action="store_true", help="full decoder-cost grid")
    parser.add_argument("--train", default="default", help="scenario list, or 'mix' for all")
    parser.add_argument("--eval", default="default", help="comma-separated scenarios")
    parser.add_argument("--drop", default="", help="comma-separated feature names")
    args = parser.parse_args()

    names = [n for n in args.predictors.split(",") if n != "learned"]
    matches = EXTERNAL_MATCHES if args.matches == "all" else args.matches.split(",")
    cfg = load_config()
    tables = [bench({n: PREDICTORS[n] for n in names}, matches, cfg, seed=args.seed)]
    if args.learned:
        decoders = ({f"learned_s{s}_d{d}": (s, d) for s in SWITCH_GRID for d in DEAD_GRID}
                    if args.grid else NEAR_WINNER)
        train = list(SCENARIOS) if args.train == "mix" else args.train.split(",")
        drop = tuple(f for f in args.drop.split(",") if f)

        def make_model():
            return LearnedPredictor(drop=drop, stride=len(train))  # same rows as one regime

        tables.append(bench_learned(make_model, decoders, matches, cfg, seed=args.seed,
                                    train_scenarios=train,
                                    eval_scenarios=args.eval.split(",")))
        print(f"train={args.train} eval={args.eval} drop={args.drop or '-'}")
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
