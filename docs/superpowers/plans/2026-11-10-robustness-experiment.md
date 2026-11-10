# Robustness Experiment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Find out whether the learned model's bench score (0.48) survives realistic tracking
problems the current simulation ignores, and make it robust before the Nov 14 freeze.

**Architecture:** `DegradeConfig` gets four new knobs: ball loss weighted toward the pitch edge
and slow play, an off-pitch ball that disappears, and players dropping out. Their defaults
reproduce today's output bit for bit. A set of stress scenarios is scored in one matrix: training
regime {default, mix} × eval scenario. `measure_degradation.py` (human-run) measures the same
knobs on the match, so the local config calibrates the simulation without Claude seeing numbers.

**Tech Stack:** numpy, existing `mtah` harness.

**Spec:** final review of `feat/learned-hmm` (finding I3) plus the session of 2026-11-10. No separate spec.

## Global Constraints

- R1: `measure_degradation.py` stays human-run and prints only `written`. Claude never reads `config/*.local.json`.
- R3: select on `MEAN idsse` from the bench. R4: no frame constants.
- New `DegradeConfig` defaults must leave `degrade()` output byte-identical to today's for the same seed (regression test). Run 4 stays comparable.
- Every knob is measurable on the match **without labels** (ball position, player positions only).

## Review Focus

1. Weighted gap sampling when every weight is 1 → identical RNG stream to today (Task 1).
2. A track with no visible ball at all → edge/slow weighting must not divide by zero (Task 1).
3. Player dropout must not remove the referee-only slots' meaning (team −1 untouched) and must keep `validate()` passing (Task 1).
4. Measure helpers on a match with no off-pitch ball → `offpitch_visible = false` without NaN (Task 2).
5. A scenario name typo in the bench → KeyError up front, not after 30 minutes (Task 3).

---

### Task 1: Degradation knobs

**Files:** Modify `src/mtah/degrade.py`. Test `tests/test_degrade.py`.

**Interfaces:**
- Produces: `DegradeConfig` new fields `edge_boost: float = 1.0`, `slow_boost: float = 1.0`, `offpitch_visible: bool = True`, `player_missing_frac: float = 0.0`. `SCENARIOS: dict[str, dict]` of field overrides: `default` {}, `edge` {edge_boost 4, offpitch_visible False}, `slow` {slow_boost 4}, `players` {player_missing_frac 0.15}, `all` (union of the three). `scenario(cfg, name) -> DegradeConfig` = `dataclasses.replace(cfg, **SCENARIOS[name])`.
- Semantics:
  - `offpitch_visible=False` hides the ball wherever it lies outside the pitch rectangle. This happens before gap sampling and counts toward `ball_missing_frac`.
  - Gap starts are sampled with per-frame weight w = 1 × `edge_boost` if the ball is within 3 m of a boundary or outside it, × `slow_boost` if more than 60 % of tracked players move under 1 m/s. When all weights are 1, use the existing `rng.integers` path, so the default output is unchanged.
  - `player_missing_frac`: hide random log-normal gaps (median 50 frames, sigma 1) in team-0/1 slots until that fraction of the visible player-frames is hidden.
- [ ] Tests: `test_defaults_unchanged` (compare `degrade` with the default config against a frozen hash of today's output for a synthetic track and seed 0; compute the hash before editing), `test_offpitch_hidden`, `test_edge_boost_concentrates_gaps` (gap-start share near the edge rises above its frame share), `test_player_missing_frac_reached` (±0.02), `test_referee_slot_untouched`, `test_no_visible_ball_ok`, `test_scenario_unknown_raises`.
- [ ] RED → implement → GREEN → `make test`, `make lint` → commit `feat(degrade): edge/slow-weighted ball loss, off-pitch hiding, player dropout`.

### Task 2: Measure the knobs on the match (human-run script)

**Files:** Modify `scripts/measure_degradation.py`. Create pure helpers in `src/mtah/degrade.py`: `measure_knobs(track) -> dict` returning the four new fields, computed from the match alone. Test `tests/test_degrade.py`.

- `offpitch_visible` = share of visible ball frames outside the pitch > 0.002.
- `edge_boost` = (gap-start rate per frame when the last-seen ball is near the edge) / (rate elsewhere), clipped to [1, 10].
- `slow_boost` = the same ratio for slow-play frames, clipped to [1, 10].
- `player_missing_frac` = 1 − mean(tracked team-0/1 players per in-play frame) / 22, clipped to [0, 0.6].
- [ ] Tests on synthetic tracks: a track whose gaps start only near the edge gives `edge_boost` > 3. A uniform one gives about 1. A track with no off-pitch ball gives `offpitch_visible` False. 18 tracked players gives about 0.18.
- [ ] The script merges `measure_knobs` into the written config. It still prints only `written`.
- [ ] Commit `feat(measure): calibrate the new degradation knobs on the match (human-run)`.

### Task 3: Scenario matrix bench

**Files:** Modify `src/mtah/eval/harness.py` (`bench_learned`), `src/mtah/predictors/learned.py`, `scripts/bench.py`. Test `tests/eval/test_bench.py`, `tests/predictors/test_learned.py`.

- `bench_learned(..., train_scenarios: list[str] = ["default"], eval_scenarios: list[str] = ["default"])`. Validate every name against `SCENARIOS` before any work. Training tracks: each IDSSE match degraded once per training scenario (seed + 1 + scenario index), all copies used. Each fold's model scores the held-out match under every eval scenario. Predictor name = `f"{decoder}@{eval_scenario}"`.
- `LearnedPredictor(drop: tuple[str, ...] = ())`: features named in `drop` are removed before fit/predict (ablation).
- `scripts/bench.py --learned --train default|mix --eval default,edge,slow,players,all --drop ...`, where `mix` = all five scenarios. Decoders: s8_d8 plus neighbours s8_d4 and s16_d8.
- [ ] Tests: unknown scenario raises before any `load_external` call; with 2 train scenarios a fold receives 2 × (n − 1) tracks; `drop` removes the columns (model `n_features_in_` = 34 − len(drop)).
- [ ] Commit `feat(bench): degradation-scenario matrix and feature ablation for the learned model`.

### Task 4: Run, select, log

- [ ] Run A: `--train default`, all five eval scenarios. Run B: `--train mix`, the same. Run C: `--train mix --drop ball_seen,since_seen,until_seen,ball_seen_m25,ball_seen_m125`.
- [ ] Select the regime with the best **mean over eval scenarios** of `MEAN idsse`. It must be within the noise band of the best on `default`. Robust beats peak. Metrica must agree.
- [ ] If the winner differs from today's (train default, no drop), make it the `train_on_external` default, with a pinning test.
- [ ] Log run 5 (matrix) in EXPERIMENTS and D-003 in DECISIONS, with a case-study row. Hand over: human runs `measure_degradation.py`, then `make_submission.py --predictor learned`, then `make eval`.
