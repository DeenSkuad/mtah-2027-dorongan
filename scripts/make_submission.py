"""HUMAN-RUN ONLY (rule R1). Build the team submission and print aggregate scores only.

    make submission     # = make measure, then this script with --predictor learned --name Dorongan

The default predictor is the learned model chosen on the external bench (DECISIONS D-001..D-003),
never on the public five minutes (R3). It reads config/degradation.local.json, which `make
measure` writes from the match, so run that first or the file will not reproduce.
"""

import argparse

from mtah.constants import N_MATCH_FRAMES, REPO_ROOT, RESULTS_DIR, official_metrics
from mtah.eval.harness import score
from mtah.io.match import _import_games as _games
from mtah.io.match import load_match
from mtah.predictors import PREDICTORS
from mtah.report import coverage, summary
from mtah.submit import write_submission


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictor", default="learned", choices=sorted(PREDICTORS))
    parser.add_argument("--name", default="Dorongan")
    args = parser.parse_args()

    track = load_match()
    # Diagnostic only: the graded halves come from the upstream alignment table and never
    # change a label (R4); the count says whether period inference cut into a half.
    graded = [(first, last) for _, first, last in _games().half_video_blocks("BAR-ATH")]
    print(coverage(track.periods, track.n_frames(), graded))
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
