"""Write the possession viewer's data file (open viewer/possession_viewer.html and load it).

    python scripts/export_viewer.py --match metrica1                 # external demo (+ truth)
    python scripts/export_viewer.py --match BAR-ATH --predictor learned   # HUMAN-RUN ONLY (R1)

Output goes to viewer/out/ (git-ignored). Prints one aggregate line only.
"""

import argparse
import json

import numpy as np

from mtah.constants import REPO_ROOT
from mtah.predictors import PREDICTORS
from mtah.viewer import viewer_payload

OUT = REPO_ROOT / "viewer" / "out"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--match", default="metrica1")
    parser.add_argument("--predictor", default="learned", choices=sorted(PREDICTORS))
    parser.add_argument("--step", type=int, default=5)
    args = parser.parse_args()

    if args.match == "BAR-ATH":
        from mtah.io.match import load_match

        track, truth, home, away = load_match(), None, "BAR", "ATH"
        source = "BAR–ATH · local only"
    else:
        from mtah.degrade import degrade, load_config
        from mtah.eval.harness import match_seed
        from mtah.io.external import load_external

        clean, truth = load_external(args.match)
        track = degrade(clean, load_config(), np.random.default_rng(match_seed(0, args.match)))
        home, away = "HOME", "AWAY"
        source = f"{args.match} · external demo, degraded tracking"

    labels = PREDICTORS[args.predictor](track)
    payload = viewer_payload(track, labels, home, away, truth=truth, step=args.step,
                             source=f"{source} · {args.predictor}")
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{args.match}_{args.predictor}.json"
    path.write_text(json.dumps(payload, separators=(",", ":")))
    print(f"written {path.relative_to(REPO_ROOT)} ({len(payload['pred'])} label runs)")


if __name__ == "__main__":
    main()
