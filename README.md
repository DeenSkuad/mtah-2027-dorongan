# MTAH 2027 — Team Project Hub

Start here. Upstream challenge docs (README, CHALLENGE, DATA, EVALUATION, SUBMISSION, RULES, FAQ)
are untouched so `git pull upstream main` stays clean. Everything the team adds lives in the places below.

## Key dates (CET)

| Date | Milestone | Status |
|---|---|---|
| Oct 20 | Data released | ✅ downloaded |
| **Nov 10** | **All members registered with the same team name** | ☐ |
| Nov 14 | Submission instructions published | ☐ |
| **Nov 17, 23:59** | **Submission deadline** (CSV + public repo + tech doc) | ☐ |
| < Nov 26 | Results — top 20 go to Innovation Challenge | |

## Target

Ranked on `spellF1` (full match, private GT). Baseline floor: **0.2433**. First tie-break: `macroF1`.

## Where things live

```
PROJECT.md              <- you are here
docs/
  PLAN.md               milestones + task board (who does what)
  EXPERIMENTS.md        every scored run: idea, params, public-5min scores
  DECISIONS.md          possession rules & design choices (feeds the tech doc)
  TECHNICAL_REPORT.md   deliverable #3, filled in as we go
src/possession/         our pipeline (importable package)
scripts/                CLI entry points (make_submission.py, ...)
notebooks/              exploration; name as NN_initials_topic.ipynb
starter/, evaluation/   upstream — read, don't edit
data/                   match assets (git-ignored, never commit)
evaluation/results/     candidate submissions (git-ignored except baselines)
```

## Daily commands

```bash
source .venv/bin/activate
make baseline        # rebuild the 4 reference baselines
make eval            # score everything in evaluation/results/
make validate F=evaluation/results/<file>.csv   # ALWAYS before submitting
make sync            # pull upstream fixes from Metrica
```

## Git workflow

- `upstream` = metrica-sports/more-than-a-hack-2027 (read-only).
- `develop` = team integration branch; feature branches `feat/<topic>` → PR into `develop`.
- Add our own public repo as `origin` when created (deliverable #2 must be public — **never push data/ or GT**).
- Log every scored run in `docs/EXPERIMENTS.md` in the same commit as the code that produced it.
