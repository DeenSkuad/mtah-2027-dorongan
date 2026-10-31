"""HUMAN-RUN ONLY (rule R1). Build the team submission and print aggregate scores only.

    python scripts/make_submission.py --predictor baseline125 --name <team>
"""

import argparse

from mtah.constants import N_MATCH_FRAMES, REPO_ROOT, RESULTS_DIR, official_metrics
from mtah.eval.harness import score
from mtah.io.match import load_match
from mtah.predictors import PREDICTORS
from mtah.report import summary
from mtah.submit import write_submission


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictor", default="baseline125", choices=sorted(PREDICTORS))
    parser.add_argument("--name", default="team")
    args = parser.parse_args()

    labels = PREDICTORS[args.predictor](load_match())
    path = write_submission(labels, RESULTS_DIR / f"{args.name}.csv")

    metrics = official_metrics()
    gt = metrics.read_label_csv(REPO_ROOT / "evaluation/gt/BAR-ATH_possession_gt_public.csv")
    public = score(gt["label"].to_numpy(dtype="<U1"), labels, ((0, N_MATCH_FRAMES),))
    print(summary(f"{args.predictor} (public 5 min, sanity only)", public))
    print(f"valid, {N_MATCH_FRAMES} rows -> {path.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
