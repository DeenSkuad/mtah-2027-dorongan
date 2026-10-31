# Plan & Task Board

Status: ☐ todo · ◐ in progress · ✅ done · ✖ dropped. Put an owner on every in-progress task.

## Phase 0 — Setup (Oct 31) ✅

| Task | Owner | Status |
|---|---|---|
| Download all 9 assets incl. tactical video | | ✅ |
| Foundation: guardrails, package, harness, bench (plan 2026-10-31-foundation) | | ✅ |
| Clone repo, venv, unpack into `data/` | | ✅ |
| Reproduce baselines + scorer locally | | ✅ |
| Register every member with the **same team name** (by Nov 10) | all | ☐ |

## Phase 1 — Understand (Nov 1–3)

| Task | Owner | Status |
|---|---|---|
| Read CHALLENGE / EVALUATION / RULES end to end | all | ☐ |
| Run the 3 starter notebooks | | ☐ |
| Study the public 5-min GT vs video: how are D / loose balls / restarts labelled? | | ☐ |
| Quantify ball-missing frames (41%) — where/when do gaps occur? | | ☐ |
| Write possession rules into `DECISIONS.md` | | ☐ |

## Phase 2 — Core model (Nov 4–10)

| Task | Owner | Status |
|---|---|---|
| Dead-ball detector (Smart Tagging set pieces + ball out of pitch + stillness) | | ☐ |
| Per-frame team control (nearest player, ball velocity, distance thresholds) | | ☐ |
| Ball gap filling (interpolation, player-cluster inference) | | ☐ |
| Segment-level smoothing: HMM / min-duration spells (spellF1 rewards whole possessions) | | ☐ |
| Use Smart Tagging phases (in/out of possession) as a prior | | ☐ |

## Phase 3 — Tune & harden (Nov 11–15)

| Task | Owner | Status |
|---|---|---|
| Parameter sweep, guard against overfitting the 5-min GT | | ☐ |
| Optional: broadcast feed / video CV for ball-missing stretches | | ☐ |
| `scripts/make_submission.py` reproduces the final CSV bit-for-bit | | ☐ |

## Phase 4 — Ship (Nov 16–17)

| Task | Owner | Status |
|---|---|---|
| Public repo created, data/GT confirmed absent | | ☐ |
| `TECHNICAL_REPORT.md` finalised (export PDF if wanted) | | ☐ |
| `make validate` on final CSV | | ☐ |
| Submit form **before Nov 17 23:59 CET** (aim for Nov 16) | | ☐ |
