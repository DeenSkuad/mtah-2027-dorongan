"""HUMAN-RUN ONLY (rule R1). Build the team submission and print aggregate scores only.

    python scripts/make_submission.py --predictor baseline50 --name <team>

The default is baseline50, not baseline125: the upstream docs note that 125 only looks better on
the public five minutes and is worse on the full match, and R3 forbids choosing on that window.
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
    parser.add_argument("--predictor", default="baseline50", choices=sorted(PREDICTORS))
    parser.add_argument("--name", default="team")
    args = parser.parse_args()

    track = load_match()
    covered = sum(stop - start for start, stop in track.periods) / track.n_frames()
    print(f"inferred periods: {len(track.periods)}, covering {100 * covered:.0f}% of frames")
    labels = PREDICTORS[args.predictor](track)
    if args.predictor == "learned":
        from mtah.predictors import learned

        print(f"learned model trained with degradation config {learned._FITTED.trained_with}")
    path = write_submission(labels, RESULTS_DIR / f"{args.name}.csv")

    metrics = official_metrics()
    gt = metrics.read_label_csv(REPO_ROOT / "evaluation/gt/BAR-ATH_possession_gt_public.csv")
    public = score(gt["label"].astype(str).str.strip().str.upper().to_numpy(), labels,
                   ((0, N_MATCH_FRAMES),))
    print(summary(f"{args.predictor} (public 5 min, sanity only)", public))
    print(f"valid, {N_MATCH_FRAMES} rows -> {path.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
