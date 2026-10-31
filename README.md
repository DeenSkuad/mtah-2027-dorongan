# MTAH 2027 — Ball Possession (Phase 1)

Our entry to [More than a Hack 2027](https://github.com/metrica-sports/more-than-a-hack-2027):
label every frame of BAR–ATH as **H** (home), **A** (away), **D** (dead ball) or **X** (abstain).
Ranked on `spellF1` (whole possessions recovered); floor to beat **0.2433**.

## Key dates (CET)

| Date | Milestone | Status |
|---|---|---|
| Oct 20 | Data released | ✅ downloaded |
| **Nov 10** | **All members registered under the same team name** | ☐ |
| Nov 14 | Submission instructions published · **model freeze** | ☐ |
| **Nov 16** | **Our submission target** (deadline Nov 17, 23:59) | ☐ |
| < Nov 26 | Results — top 20 go to the Innovation Challenge | |

## Quick start

```bash
make setup                 # Python 3.12 venv via uv + editable install
make test && make lint     # must be green before every commit
make bench                 # score predictors on degraded Bundesliga matches (model selection)
make submission            # HUMAN ONLY: builds evaluation/results/<team>.csv from the match
make validate F=evaluation/results/<team>.csv
make help                  # every target
```

Put the match bundle in `data/` (see `data/README.md`) or point `MTAH_DATA_DIR` at it.

## Project layout

```
.
├── README.md            this page
├── CLAUDE.md            rules Claude follows here (R1: match data never reaches a cloud LLM)
├── Makefile             every command the team needs
├── pyproject.toml       mtah package, deps, pytest + ruff config
├── .claude/             team-wide Claude Code setup: R1 guard hook, permissions, 5 subagents
├── config/              degradation defaults (match-measured values stay local, git-ignored)
├── src/mtah/            our code — see docs/ARCHITECTURE.md
├── scripts/             bench · make_submission · fetch_external · measure_degradation
├── tests/               mirrors src/mtah; markers: network, match (humans only)
├── notebooks/           exploration on external data — NN_initials_topic.ipynb
├── docs/
│   ├── ARCHITECTURE.md  data flow, modules, how to add a predictor
│   ├── PLAN.md          task board with owners
│   ├── EXPERIMENTS.md   every scored run
│   ├── DECISIONS.md     possession rules we chose (feeds the tech report)
│   ├── REFERENCES.md    papers, datasets, libraries, Claude Code docs
│   ├── TECHNICAL_REPORT.md  deliverable #3
│   ├── bench/           benchmark result CSVs
│   ├── challenge/       the organisers' docs (CHALLENGE, DATA, EVALUATION, RULES, FAQ…)
│   └── superpowers/     design spec + implementation plans
├── requirements/        lock.txt (exact env) + upstream requirement files
├── evaluation/          UPSTREAM — official scorer, public GT, results/   (read-only)
├── starter/             UPSTREAM — loaders, baseline, notebooks           (read-only)
├── games.py             UPSTREAM — paths and frame alignment               (read-only)
└── data/                match assets — git-ignored, never committed, never shown to Claude
```

`evaluation/`, `starter/` and `games.py` stay at the root because the official scorer and starter
scripts resolve paths relative to it.

## How we work

- **Rules:** `CLAUDE.md` (R1–R7). The one that can disqualify us: no match data, video or
  extracts go to any cloud LLM. A Claude Code hook enforces it.
- **Model selection** happens on `make bench` (7 public Bundesliga matches, degraded to look like
  our tracking), never on the public 5 minutes.
- **Process:** superpowers — brainstorm → plan → TDD → verify → review.
- **Git:** `upstream` = Metrica (read-only) · `develop` = integration · `feat/<topic>` → PR ·
  `main` always submittable. Our public repo will be `origin` (deliverable #2).
- Every experiment: one commit + one row in `docs/EXPERIMENTS.md`.
