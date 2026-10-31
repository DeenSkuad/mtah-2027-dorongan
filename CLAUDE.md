# CLAUDE.md — MTAH 2027 Phase 1 (ball possession)

Label each of 199,319 frames of BAR–ATH as H / A / D / X. Ranked on spellF1 (private GT).
Team hub: `README.md` · plan: `docs/superpowers/specs/2026-10-31-operating-plan-design.md` ·
architecture: `docs/ARCHITECTURE.md` · challenge docs: `docs/challenge/`.

## Hard rules (never break, never "just this once")

- **R1 — No match data reaches Claude.** Never read, grep, list, print or view anything under
  the match data folder, any `*.mp4`, `*_atd.*`, `*_homography.csv`, `*_smart_tagging.xml`, or
  `config/*.local.json`. A PreToolUse hook enforces this; if it blocks you, do not work around it —
  ask a human to run the step locally. Applies to subagents too.
- **R2 — No hand labels on this game**, any amount, any purpose.
- **R3 — Never tune or select on the public 5-min GT.** Model selection uses `make bench`
  (external Bundesliga data). The public GT is a parity / alignment check only.
- **R4 — No frame-specific constants** for this game.
- **R5 — Reproducible.** The final CSV must regenerate bit-for-bit from `make submission`.
  Seeds are explicit; dependencies pinned in `requirements/lock.txt`.
- **R6 — Public repo hygiene.** Never commit match data, GT beyond the public file, or
  match-derived artefacts.
- Upstream files (`evaluation/`, `starter/`, `games.py`, `docs/challenge/`) are read-only — import them.

## How Claude works here

- Develop, debug and plot freely on **external** data (IDSSE/DFL, Metrica samples).
- On the match, a **human** runs `make submission` / `make eval` / `pytest -m match` and pastes
  back aggregate scores only. Claude never runs those three.
- Match-side code prints only aggregates via `mtah.report` — never rows, frames, coordinates or
  segment lists.

## Commands

```bash
make setup     # uv venv (Python 3.12) + editable install
make test      # unit tests (excludes match + network markers)
make lint      # ruff
make bench     # score predictors on degraded external matches — THE model-selection number
```

## Workflow

superpowers: brainstorming → writing-plans → TDD → verification-before-completion →
requesting-code-review. Branches `feat/<topic>` → PR into `develop`; `main` is always
submittable. Every scored experiment = one commit + one row in `docs/EXPERIMENTS.md`;
every label-affecting rule = one entry in `docs/DECISIONS.md`.
