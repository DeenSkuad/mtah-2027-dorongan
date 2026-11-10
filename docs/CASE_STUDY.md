# Case Study: Building a Hackathon Entry with Claude Code

*More than a Hack 2027, Phase 1 (ball possession). Living document, started 2026-11-01.*

How a senior team lead and Claude Code (Opus 5.5) went from "I downloaded some zips" to a
rule-compliant, tested, benchmarked project foundation in about 30 hours of wall-clock time.
The parts that went wrong are included as well.

---

## 1. Starting point (Oct 31, morning)

- Challenge: label each of 199,319 video frames of Barcelona–Athletic as H / A / D / X.
  Ranked on spellF1, a segment-level F1 over whole possessions. Floor 0.2433. Deadline Nov 17.
- What existed: the organisers' public repo, 8 zip parts and a 13 GB broadcast video in `~/Downloads`.
- Ask: "check if I'm missing anything."

## 2. Timeline

| When | What happened | How |
|---|---|---|
| Oct 31 | **Inventory.** The tactical video (the file the whole submission is indexed to) was missing. Two stalled 2.6 GB downloads turned out to be a duplicate and a truncated file. | Cloned the repo, compared it against `data/README.md`, checked the partial files with `ffprobe`. |
| Oct 31 | **Download.** Anonymous Drive download failed (restricted folder). Found the file ID through the Google Drive connector, then downloaded it in the user's signed-in Chrome. Verified 199,319 frames, matching the required row count. | Drive MCP + Claude in Chrome + `ffprobe` |
| Oct 31 | **Project skeleton.** Repo cloned into the project folder, venv, data unpacked, baselines rebuilt, scorer run. Matched the published numbers exactly (spellF1 0.4242 on the public 5 min). | Make targets, a git `develop` branch, Metrica's repo as `upstream` |
| Oct 31 | **Deep research.** Three parallel agents covered rules and metric, data EDA, and literature/tools. | Subagents (general-purpose) |
| Oct 31 | **Compliance discovery (critical).** The rules agent found the terms forbid sending match data or extracts to any cloud LLM, Claude included. The EDA agent was **stopped mid-run**. All later work kept match data out of the model. | `TaskStop`, memory note, later a hook |
| Oct 31 | **Operating plan (spec).** Rules R1–R7, how Claude is used, workflow, agent roles, timeline. A fresh "builder" agent reviewed it; its 6 questions were answered as recorded calls C1–C6. | superpowers: brainstorming → spec → builder check |
| Oct 31 | **Implementation plan.** 9 TDD tasks with exact interfaces, global constraints and a "review focus" list. | superpowers: writing-plans |
| Oct 31 | **Root reorganisation.** The user didn't like the cluttered root. Upstream docs moved to `docs/challenge/`, the team hub became `README.md`, requirements went into `requirements/`. Code that upstream scripts resolve by path stayed at the root (verified first). | `git mv` (history preserved) |
| Oct 31 | **Build (inline execution).** Guard hook, Python 3.12 package via uv, `MatchTracking` data contract, harness wrapping the official metric, IDSSE loader, degradation simulator, baseline port (bit-identical to upstream), validated submission writer, docs, 5 Claude subagent definitions. | superpowers: executing-plans + TDD (failing test first, every task) |
| Oct 31 | **Whole-branch review.** A fresh Opus reviewer found 3 Critical, 3 Important and 8 Minor issues, e.g. the match loader would crash outside pytest, a degradation edge case hung forever, and the hook had many bypasses. All Critical/Important fixed, each with a test that failed first. | superpowers: requesting-code-review |
| Oct 31 | **External benchmark.** 7 open Bundesliga matches (~2.9 GB) downloaded; the kloppy release had dead links, so it was upgraded. Bench result: baseline50 = 0.230 vs the organisers' full-match 0.2433, with the same ranking. **The internal benchmark is a valid stand-in for the hidden leaderboard.** | `make bench` |
| Oct 31–Nov 1 | **Side quest: vision video.** Mockups (visual companion), research on football-TV camera grammar, Blender install, Mixamo characters, a CC0 BlendSwap stadium, Cycles look-dev, an animated broadcast + rewind + 3D replay clip. | Blender 5.2 scripted in Python, Chrome automation, BlendSwap MCP |
| Nov 1 | User: "I think we overdo this task?" Agreed. Saved a feedback memory to time-box optional work and steer back to the scored submission. | memory |
| Nov 10 | **Second bench provider.** Metrica's 2 public sample games (~127 MB) added; per-frame labels rebuilt from the hand-tagged events. Event labels turned out much easier (baseline50 0.415 vs 0.230), so the bench now reports the two sources separately: IDSSE decides, Metrica must agree on the ranking (it does). | TDD, `make bench`, run 3 in `EXPERIMENTS.md` |
| Nov 10 | **Learned model.** The user said "top 20, go". Plan, then 4 TDD tasks inline: tracking features → gradient-boosted P(H/A/D) → Viterbi with switch / dead-ball costs, trained on external IDSSE only. Bench, leave-one-match-out: **0.480 vs 0.230** for baseline50, better on all 9 matches. | superpowers: writing-plans → executing-plans + TDD, `scripts/bench.py --learned` |

## 3. Architecture we ended with

```
external (Claude may see)                        match (humans only, rule R1)
IDSSE/DFL ─► load_idsse ─► MatchTracking         tactical ATD ─► load_match ─► MatchTracking
                 │                                                     │
           degrade (41% ball dropout,                           predictor (same code)
           ID switches)                                                │
                 │                                       write_submission ─► CSV (validated)
           predictor ─► score() ─► make bench                          │
           (official possession_metrics)                 report.summary (aggregates only)
```

- One data contract (`MatchTracking`), one predictor registry, the official metric reused rather than re-implemented.
- 76 tests (unit + network + human-only match markers), ruff-clean, Python 3.12, locked deps.

## 4. Rule compliance as engineering (R1)

The single biggest risk was disqualification for sending match data to a cloud LLM. It was handled in layers:
1. **Process:** Claude develops only on public data that carries the same labels; a human runs anything that touches the match and pastes back aggregate scores only.
2. **Code:** match-side output goes through `mtah.report.summary`; error messages never echo values; match tests fail without printing data.
3. **Enforcement:** a Claude Code PreToolUse hook blocks tool calls that reference the data folder, the video, the tracking/tagging/homography files or locally measured statistics, plus human-only commands. It has 35 tests. It blocked Claude about 15 times during the project, including false positives on harmless text, which was accepted as the cost of safety.
4. **Incidents and disclosure question:**
   - Oct 31: a few aggregate statistics (video length, ball-present %, label counts) were seen before the rule was found.
   - Nov 1: three still frames from the tactical video were pasted into the chat by a team member. Claude did not analyse or use them, and the team was reminded that screenshots must stay local.
   - The hook can't stop content a human pastes in; that part is human discipline. Whether to tell the organisers is left to the team.

## 5. How Claude Code was used

| Capability | Used for |
|---|---|
| Subagents | rules/metric research, literature research, builder check of the spec, whole-branch code review (Opus) |
| superpowers skills | brainstorming → writing-plans → executing-plans → TDD → verification → code review |
| Hooks + settings | R1 guard, deny rules, team-wide `.claude/settings.json` |
| Memory | rules, project state, user profile, hook workarounds, scope feedback |
| MCP connectors | Google Drive (find the file), BlendSwap (assets), Claude in Chrome (signed-in downloads) |
| Visual companion | style frames and camera studies for the video |
| Background tasks | multi-GB downloads, Blender renders, benchmark runs |

## 6. What went wrong, and the fix

| Problem | Fix |
|---|---|
| EDA agent started reading match data before the rule was known | Stopped; R1 memory + hook + process |
| Hook too narrow (reviewer found bypasses) | Hardened: word-level match, case-insensitive, human-only commands; tests for each bypass |
| kloppy's dataset links were dead | Upgraded kloppy; downloaded with resumable curl |
| Parallel downloads spawned duplicate writers | Killed all, restarted one writer per file |
| Homebrew broken on the Mac | Installed Blender from blender.org with checksum verification into `~/Applications` |
| Early video looks were "cartoon" | Studied real broadcast camera rules (12–15°, halfway gantry), moved to Mixamo + modelled stadium + Cycles |
| Scope creep on the video | Feedback memory: time-box optional work |

## 7. Numbers

| Metric | Value |
|---|---|
| Commits on `develop` (ours) | 18 |
| Tests | 76 (73 unit, 2 network, 1 human-only) |
| Internal bench, baseline50 | spellF1 0.2299 (7 matches) vs 0.2433 official |
| Subagent tokens (measured) | rules 112,753 · literature 57,382 · builder check 46,895 · code review 80,768 · **total 297,798** (the stopped EDA agent is not counted) |
| Main session tokens | *fill from `/cost` or `/usage`* |
| Render speed (M1, Cycles, 1280×720) | ~27 s/frame |

## 8. Still to come

- Step 1 (human): match test, `make submission`, `make measure`.
- Step 2: first real model (per-frame probabilities + HMM/Viterbi switch penalty).
- CI, pre-commit, code-standards pass; public repo; technical report; submission on Nov 16.
