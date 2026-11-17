# Team Dorongan — More than a Hack 2027, Phase 1: Ball Possession

Our entry to [More than a Hack 2027](https://github.com/metrica-sports/more-than-a-hack-2027).
Every frame of BAR–ATH (199,319 frames) is labelled **H** (home in possession), **A** (away),
**D** (dead ball) or **X** (abstain). Entries are ranked on `spellF1`.

**Technical report:** [`docs/TECHNICAL_REPORT.md`](docs/TECHNICAL_REPORT.md)
**Submitted state:** tag [`submission-v1`](https://github.com/DeenSkuad/mtah-2027-dorongan/tree/submission-v1)
**Submitted file:** `Dorongan.csv`, SHA-256
`aa679800f3094bcc79356ec51da92fd06551aa51e3aba451b6edc2dc4f786b44`

## Method in brief

**Pipeline:** tracking features → gradient-boosted P(H, A, D) → Viterbi decoding with switch costs.

1. **Features:** 34 team-aggregate features per frame from the provided tactical tracking: ball
   state and position, nearest-player distances, team shape, speeds, and rolling context.
2. **Classifier:** scikit-learn `HistGradientBoostingClassifier`, trained only on 7 external
   Bundesliga matches (IDSSE / DFL open data, CC-BY). Their per-frame ball-status and possession
   flags follow the same definition as this challenge's ground truth.
3. **Domain gap:** the external tracking is degraded to resemble ours (ball gaps, identity
   switches, stress scenarios) before training.
4. **Decoding:** Viterbi with switch and dead-ball costs turns flickering per-frame probabilities
   into whole possessions.

No label from the provided game was used for anything.

## Results (model selection on external data)

spellF1 on degraded external matches, leave-one-match-out (`make bench`; log in
[`docs/EXPERIMENTS.md`](docs/EXPERIMENTS.md)):

| Model | IDSSE (7) | Metrica (2) |
|---|---|---|
| Organisers' baseline (nearest player, ±50 frames) | 0.230 | 0.415 |
| **Submitted model** | **0.497** | **0.617** |

The public 5-minute ground truth was used only as an alignment check: spellF1 0.500, with
19 possessions predicted against 17 true. It was never used to train, tune or choose.

## Reproduce the submission

```bash
git clone https://github.com/DeenSkuad/mtah-2027-dorongan && cd mtah-2027-dorongan
git checkout submission-v1
make setup        # Python 3.12.12 venv via uv; installs requirements/lock.txt exactly
# unpack the competition bundle into ./data (see data/README.md), or set MTAH_DATA_DIR
make submission   # measure tracking stats -> train on IDSSE (downloaded once, checksum-verified)
                  # -> label the match -> evaluation/results/Dorongan.csv
                  # -> official validator -> SHA-256
```

**Requirements:**
- [uv](https://docs.astral.sh/uv/), `make`, `curl`, `shasum`
- internet access to huggingface.co on the first run (~2.6 GB of IDSSE XML)

Seeds are fixed and dependencies pinned, so the same inputs give the same file byte for byte.
Without the match data you can still run `make test` and `make bench`.

## Rules compliance

- **No hand labels and no human-produced data about the provided game.** Training uses external
  matches only. The private ground truth is never referenced.
- **The public 5 minutes are a parity check only.** Model selection happens on `make bench`.
- **No frame-specific constants.** Playing periods and attacking direction are inferred from
  the tracking.
- **The match data is not in this repository**, nor any data derived from it. `.gitignore`
  guards against it.
- **AI-assisted development.** The code was written with Claude Code. Steps that read the match
  run locally and print aggregates only, and a hook (`.claude/hooks/`) keeps match files away
  from the assistant. Details are in the technical report, §2.

## Repository layout

```
src/mtah/        our package: loaders, features, degradation, predictors, decoding, writer
scripts/         make_submission · measure_degradation · bench · fetch_external · export_viewer
tests/           unit tests on synthetic and external data (match tests run locally only)
config/          default degradation config · IDSSE checksum manifest
docs/            TECHNICAL_REPORT · ARCHITECTURE · DECISIONS · EXPERIMENTS · REFERENCES ·
                 CASE_STUDY · bench/ (results) · challenge/ (organisers' docs) · superpowers/ (plans)
viewer/          local HTML viewer for possession timelines (QA tool, not part of the pipeline)
requirements/    lock.txt (exact environment) + upstream requirement files
evaluation/      upstream: official scorer, public 5-min ground truth, baselines   (unchanged)
starter/         upstream: loaders, baseline, notebooks                            (unchanged)
games.py         upstream: asset paths and frame alignment                         (unchanged)
data/            match assets: git-ignored, never committed
```

## Development

```bash
make test && make lint   # unit tests (no match data, no network) and ruff
make bench               # external benchmark: the model-selection number
make help                # every target
```

Upstream code (`evaluation/`, `starter/`, `games.py`) is kept byte-identical to the
organisers' repository. This repository builds on theirs; see [`LICENSE`](LICENSE) and
[`CITATION.cff`](CITATION.cff) for the benchmark.
