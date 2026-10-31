# Technical Report — <Team name>

More than a Hack 2027, Phase 1: Ball Possession. Required sections per SUBMISSION.md.

## 1. Approach
_What we built and why this rather than something else._

## 2. Assets used
| Asset | Used? | How / why dropped |
|---|---|---|
| Tactical ATD (tracking + ball) | | |
| Tactical homography | | |
| Smart Tagging | | |
| Tactical video | | |
| Broadcast video / ATD / homography | | |

## 3. Training data
_Every labelled dataset, source, who labelled it, how much. None may come from the provided game._

## 4. Possession rules implemented
_Loose balls, challenges, restarts — see docs/DECISIONS.md._

## 5. Results
_Public 5-min scores; see docs/EXPERIMENTS.md._

## 6. Limitations & future work

## 7. Reproduction
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-lock.txt
# put data in ./data (see data/README.md)
make submission
make validate F=evaluation/results/<final>.csv
```
