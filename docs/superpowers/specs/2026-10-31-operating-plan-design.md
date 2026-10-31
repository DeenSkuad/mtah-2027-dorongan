# MTAH 2027 Phase 1 — Operating Plan

Status: **DRAFT, awaiting team approval** · 2026-10-31

## 1. Intent

Label every frame of BAR–ATH as H / A / D / X and finish in the **top 20 on spellF1** (private full-match
GT) to reach the Innovation Challenge. Floor to beat: spellF1 **0.2433** (full match).
Success = a reproducible, rule-clean submission that clearly beats every baseline on our own
held-out validation, submitted by **Nov 16** (one day of slack before the Nov 17 23:59 CET deadline).

**Anti-goals** (failure even if the score is good): any rules breach (data to cloud LLM, hand labels,
tuning on the public 5 min), a file the repo cannot regenerate bit-for-bit, data or GT pushed to the
public repo, missing the deadline.

## 2. Hard rules (non-negotiable, enforced)

| # | Rule | Source | Enforcement |
|---|---|---|---|
| R1 | No match video / data / extracts to any cloud LLM (Claude, ChatGPT, Gemini…) | FAQ.md:109, OVERVIEW.md:154 | `CLAUDE.md` + PreToolUse hook blocking Claude from `data/`, `*.mp4`, ATD/homography/tagging files |
| R2 | No hand labels on this game, any amount, any purpose | RULES.md, FAQ.md | team discipline; documented in tech report |
| R3 | Never tune / select models on the public 5-min GT — sanity check only | RULES.md, EVALUATION.md | model selection only on external validation (§5) |
| R4 | No constants tied to specific frames of this game | RULES.md | code review checklist |
| R5 | Final CSV regenerates exactly from `make submission` | SUBMISSION.md | pinned `requirements-lock.txt`, fixed seeds, CI-style check before submit |
| R6 | Public repo never contains `data/`, GT, or match-derived artefacts | data/README.md | existing `.gitignore` + pre-push check |
| R7 | Every member registered under the same team name by **Nov 10** (team of 3–5) | email, RULES.md | PLAN.md checkbox per member |

## 3. How we use Claude (the "Claude plan")

The key insight: **R1 forbids match data, not football data.** Public external datasets (IDSSE/DFL
Bundesliga, Metrica sample games, SkillCorner open data) carry the same kind of tracking *and* real
possession/ball-status labels. So:

- **Claude works fully on external data** — writes loaders, features, models, smoothing, and debugs by
  looking at DFL/Metrica outputs, plots and errors.
- **The match is a black box to Claude.** A human runs `make submission` / `make eval` locally. Only
  these may be pasted back: scorer summary metrics (spellF1, macroF1, spell counts/durations), stack
  traces with no data values, and runtime. Never rows, frames, coordinates, segment lists or video.
- Code that touches the match prints **only aggregate metrics** by design (a `report()` helper), so
  nothing restricted is ever on screen to paste by accident.
- If an LLM is ever needed *on* match data: local only (Ollama / MLX), documented.

## 4. Workflow

**Process (superpowers skills, in order, per feature):**
brainstorming → `writing-plans` → `using-git-worktrees` → `test-driven-development` (via
`subagent-driven-development` for multi-task plans) → `verification-before-completion` →
`requesting-code-review` → `finishing-a-development-branch`. `systematic-debugging` whenever
something breaks.

**Git:** `upstream` = Metrica (read-only) · `main` = always submission-ready · `develop` =
integration · `feat/<topic>` branches → PR into `develop`. Our public repo becomes `origin` once created.

**Every experiment** = one commit that changes code + one row in `docs/EXPERIMENTS.md` with internal
validation score (decides) and public-5-min score (sanity only). Every rule-affecting choice gets a
`docs/DECISIONS.md` entry — these become the tech report's "possession rules" section.

**Cadence:** daily 15-min sync (yesterday / today / blocked + current best internal score);
model freeze **Nov 14**; tech doc complete **Nov 15**; submit **Nov 16**.

## 5. Technical approach (to be detailed in writing-plans)

1. **Internal evaluation harness first.** Convert DFL (7 matches) + Metrica samples into our label
   format (H/A/D per frame), hold out matches, and score with Metrica's *own*
   `possession_metrics.py`. Degrade inputs to match ours: drop ball on ~41% of frames, inject ID
   switches, strip ball-alive flags. This replaces the forbidden public-GT tuning (R3).
2. **Rule baseline v1:** team-level ball control (Vidal-Codina-style zones), last-owner carry-through
   for loose balls, **X (not D) when ball is missing**.
3. **Temporal decoding:** HMM/Viterbi over {H, A, D} with switch penalties tuned on the harness for
   spellF1 — expected largest single gain.
4. **Learned per-frame model:** LightGBM on windowed team-shape + ball features (works with ball
   missing), trained on degraded DFL/Metrica; probabilities feed the Viterbi.
5. **Dead-ball detector:** player stillness, ball near boundaries, restart geometry; Smart Tagging set
   pieces as a feature.
6. **Smart Tagging prior** (attacking/defending phase per team) as an HMM emission feature.
7. *Optional, if time:* local YOLO ball detection on the tactical video for ball-missing frames,
   projected through the provided homography.
8. *Stretch:* PathCRF / ballradar-style possessor model.

## 6. Agentic team (Claude subagents)

| Role | Does | Touches match data? |
|---|---|---|
| Researcher | papers, libraries, external datasets | no |
| Data engineer | loaders for DFL / Metrica / our format, degradation | no (external only) |
| Modeler | features, LightGBM, Viterbi | no (external only) |
| Evaluator | harness, sweeps, error analysis on external holdouts | no |
| Reviewer | code review vs R1–R6 checklist, reproducibility | no |

Parallel tasks run in separate git worktrees. Large multi-agent fan-outs (e.g., hyperparameter
sweeps) only when the team explicitly asks for a workflow. Humans are the only "agents" who run
anything on the match.

## 7. Skills & tools

- **Use:** superpowers (process above), `dataviz` (plots / error analysis), `code-review`,
  `schedule` (deadline reminders: Nov 10, 14, 16), `claude-api` only if we build LLM tooling.
- **Not relevant:** Vercel, Figma, motion/animation skills.
- **Python libs to add:** floodlight, databallpy, hmmlearn, lightgbm, mplsoccer, pytest
  (+ ultralytics, supervision only if step 7 is taken).

## 8. Timeline

| Dates | Milestone |
|---|---|
| Oct 31 | ✅ data, repo, venv, baselines reproduced; this plan |
| Nov 1–2 | plan approved; R1 guardrails in place; external datasets downloaded; harness built |
| Nov 3–5 | rule baseline v1 + Viterbi; first internal scores |
| Nov 6–9 | learned per-frame model + dead-ball detector |
| **Nov 10** | **all members registered**; mid-point review: pick direction for week 2 |
| Nov 11–13 | Smart Tagging prior, optional video, ablations |
| Nov 14 | **model freeze**; submission instructions published |
| Nov 15 | tech doc complete; public repo cleaned + reproducibility check from fresh clone |
| **Nov 16** | **submit** (deadline Nov 17 23:59 CET) |

## 9. Calls made by Claude (team: check these)

- **C1 — Degradation stats stay local.** Ball-gap length distribution, ID-switch rate and track
  fragment lengths are measured on the match by a local script that writes a git-ignored
  `config/degradation.local.json`. The degradation code reads it; Claude never sees its values.
  Default values from literature are used until it exists.
- **C2 — Label definitions come from CHALLENGE.md text**, not from fitting the public 5 min. External
  labels are converted to that written definition (dead = D with no owner; loose ball keeps last
  owner). If ambiguity remains, ask the organisers via a GitHub issue rather than reverse-engineering
  the public GT.
- **C3 — Priorities:** §5 steps 1–6 are fixed in that order; 7 then 8 are cut first if time runs short.
- **C4 — Nov 1–2 includes the guardrails** (CLAUDE.md, R1 hook, pre-push data check) as plan tasks,
  not just the harness.
- **C5 — Dataset check is task #1 of the harness:** confirm IDSSE/DFL per-frame BallPossession +
  BallStatus and CC-BY licence; fallback = Metrica samples + SkillCorner open data.
- **C6 — Experiment loop speed:** match-side runs are batched — the human runs `make eval` at most
  twice a day; everything else iterates on external data.

## 10. Open questions (team must answer)

1. Team members (3–5), skills, hours/week → owners in PLAN.md.
2. Public GitHub repo name/owner for deliverable #2.
3. Whether to disclose to organisers that aggregate stats (ball-present %, label counts, video
   metadata) were seen by Claude on Oct 31 before R1 was noticed.
