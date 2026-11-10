# Learned HMM Possession Predictor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A predictor that beats baseline50 clearly on `MEAN idsse` (0.2299) by learning per-frame
H/A/D probabilities from tracking geometry and decoding them with an HMM, aiming for top 20.

**Architecture:** `features.frame_features(track)` turns a `MatchTracking` into a (T, F) float
matrix (NaN allowed). A scikit-learn `HistGradientBoostingClassifier` trained on *degraded* IDSSE
matches maps it to P(H, A, D). `decode.viterbi` picks the label path per period with a cost for
every H↔A switch and every alive↔dead change. The bench scores it leave-one-match-out on IDSSE,
and on Metrica with a model trained on all 7 IDSSE matches.

**Tech Stack:** Python 3.12, numpy, scikit-learn (new, pinned), existing `mtah` harness.

**Spec:** none written. The user skipped design questions ("top 20, go"). Design calls are in this
header and in the session of 2026-11-10. Baselines: `docs/EXPERIMENTS.md` runs 2–3.

## Why this design (Claude's calls)

- spellF1 counts H/A runs, and **D runs split them**. IDSSE GT is 41–52 % D, but baseline50 almost
  never predicts D while the ball is visible. Dead-ball detection is the largest lever. Cues:
  ball outside the pitch, a stationary ball, slow players, ball missing.
- All baselines get the possession *count* wrong (582 predicted vs 437 GT). An explicit switch
  cost controls the count directly.
- The training data is external only (IDSSE). That's allowed: R2 forbids hand labels on *this*
  game, not learning from other games. Metrica is not used for training because its labels are
  defined differently (run 3).

## Global Constraints

- R1: never load the match in tests or scripts Claude runs. `pytest -m match` and `make submission` are human-only.
- R3: choose features, hyper-parameters and decoder costs on `MEAN idsse` from `make bench` only. Never use the public 5 min.
- R4: no frame-specific constants. R5: `random_state=0` everywhere, and two identical runs give identical labels.
- Dependency: add `scikit-learn==1.7.*` to `pyproject.toml` dependencies, then `make lock`.
- Training degradation seed = bench seed + 1, so training tracks never equal the scored tracks.
- Features must not depend on slot order or slot count (the match has 46 slots, IDSSE about 30, and `team_of_slot == -1` slots are ignored).
- Labels returned are `<U1` arrays over `H/A/D` only. Never `X`.
- Match-side code prints aggregates only (`mtah.report`).

## Review Focus

1. Ball missing for a whole period → features stay NaN-safe, no warnings or crash, and decoding falls back to the classifier's D/H/A from player features (test in Task 1 and Task 2).
2. A period shorter than the longest rolling window (125) → no index errors (Task 1).
3. Frames with no tracked players (pre-match or half-time in the match) → features NaN and the prediction is a valid label (Task 1, Task 3).
4. Determinism → two `fit` + predict runs give byte-identical labels (Task 3).
5. Extra slots with team -1 and slot permutations → features unchanged (Task 1).

---

### Task 1: Frame features

**Files:**
- Create: `src/mtah/features.py`
- Test: `tests/test_features.py`

**Interfaces:**
- Produces: `FEATURE_NAMES: tuple[str, ...]` and `frame_features(track: MatchTracking) -> np.ndarray` of shape `(T, len(FEATURE_NAMES))`, dtype float32, NaN where undefined.

Feature set (names exact). x is mirrored per period so home always attacks +x. A period's direction is `sign(median away x − median home x)` over that period's frames.

| name | definition |
|---|---|
| `ball_seen` | 1 if the ball is finite, else 0 |
| `ball_x`, `ball_y` | ball position (mirrored x), NaN if missing |
| `ball_speed` | m/s between consecutive visible frames, clipped to 40, NaN otherwise |
| `ball_out` | distance outside the pitch rectangle (0 inside), NaN if missing |
| `since_seen`, `until_seen` | frames since / until the ball was last / next visible within the period, capped at 250 |
| `d_home`, `d_away`, `d_diff` | nearest home / away player distance to the ball, and home − away |
| `n_home3`, `n_away3` | players of each team within 3 m of the ball |
| `cx_home`, `cx_away`, `cx_gap` | team centroid x (mirrored), and away − home |
| `v_home`, `v_away` | mean player speed per team, m/s, per-player speed clipped to 12 |
| `slow_frac` | share of tracked players under 1 m/s |
| `n_tracked` | tracked outfield players (team ≥ 0) |
| `last_side` | sign of `d_diff` at the last frame the ball was visible in this period (forward fill), NaN before the first visible frame |
| `<f>_m25`, `<f>_m125` | centred NaN-aware rolling mean over ±25 and ±125 frames, within the period, for f in `ball_seen, ball_speed, d_diff, v_home, v_away, slow_frac, ball_out` |

- [ ] **Step 1: Write failing tests** in `tests/test_features.py`, using a synthetic two-period `MatchTracking` built in a fixture (2 home, 2 away, 1 referee slot, 300 frames per period, the ball next to home player 0):
  - `test_shape_and_names`: `frame_features(t).shape == (600, len(FEATURE_NAMES))` and the names are unique.
  - `test_ball_owner_side`: in frames where the ball is next to a home player, `d_diff < 0` and `n_home3 >= 1`.
  - `test_direction_mirrored`: swapping which team sits on the left in period 2 leaves `cx_gap > 0` in both periods.
  - `test_ball_out_positive_outside`: a ball at x = −2 gives `ball_out == pytest.approx(2)`.
  - `test_missing_ball_period_is_nan_safe`: ball all-NaN in period 2 gives no warnings (`warnings.simplefilter("error")`), `ball_seen == 0` there, and `d_diff` NaN there.
  - `test_short_period`: a period of 10 frames works and gives finite `v_home_m125`.
  - `test_slot_permutation_and_referee_invariant`: permuting slots (with `team_of_slot` permuted the same way) and adding an all-NaN team −1 slot gives `np.testing.assert_array_equal` on the features (NaN equal).
  - `test_empty_frames`: frames with every player NaN give NaN team features and `n_tracked == 0`.
- [ ] **Step 2: Run** `.venv/bin/python -m pytest tests/test_features.py -q` → FAIL (module missing).
- [ ] **Step 3: Implement** `frame_features` in `src/mtah/features.py`, vectorised with numpy. Rolling means use cumulative sums of value and count per period. Use `np.errstate` / `nanmean` guards so nothing warns.
- [ ] **Step 4: Run** the tests again → PASS. Run `make lint`.
- [ ] **Step 5: Commit** `feat(features): per-frame tracking features for the learned predictor`.

### Task 2: Viterbi decoder

**Files:**
- Create: `src/mtah/decode.py`
- Test: `tests/test_decode.py`

**Interfaces:**
- Produces: `viterbi(proba: np.ndarray, periods, switch_cost: float, dead_cost: float, prior: np.ndarray | None = None) -> np.ndarray` (`<U1` H/A/D, length T). `proba` is (T, 3) in column order H, A, D. Emission score = `log(proba + 1e-6) − log(prior)` (prior defaults to uniform). Transition cost: 0 to stay, `switch_cost` for H↔A, `dead_cost` for any alive↔D change. Decoded independently per period, with frames outside periods = `D`.

- [ ] **Step 1: Write failing tests**:
  - `test_zero_costs_equal_argmax`: random proba with costs 0 → labels equal argmax.
  - `test_switch_cost_removes_short_flicker`: H for 100 frames with a 3-frame A blip at p = 0.6 and switch_cost 5 → all H.
  - `test_long_switch_survives`: a 200-frame A block at p = 0.9 inside H, switch_cost 5 → exactly 2 transitions.
  - `test_dead_run_kept`: a 100-frame D block at p = 0.9 inside H, dead_cost 5 → that block decodes D.
  - `test_periods_independent`: the path does not carry across a period boundary (period 2 opening with strong A is A from its first frame, even with a huge switch cost).
  - `test_all_equal_proba`: uniform proba gives a valid constant label per period, no NaN.
- [ ] **Step 2: Run** `pytest tests/test_decode.py -q` → FAIL.
- [ ] **Step 3: Implement** a numpy forward pass over T with a 3×3 cost matrix and int8 back-pointers. That's O(T·9), fine for 200k frames.
- [ ] **Step 4: Run** → PASS. Then lint.
- [ ] **Step 5: Commit** `feat(decode): Viterbi decoder with switch and dead-ball costs`.

### Task 3: Learned predictor

**Files:**
- Create: `src/mtah/predictors/learned.py`
- Modify: `pyproject.toml` (add `scikit-learn==1.7.*`), `requirements/lock.txt` (`make lock`)
- Test: `tests/predictors/test_learned.py`

**Interfaces:**
- Consumes: `frame_features`, `viterbi`.
- Produces: `class LearnedPredictor` with
  - `__init__(self, switch_cost: float = 8.0, dead_cost: float = 4.0, max_iter: int = 300)`
  - `fit(self, tracks: list[MatchTracking], labels: list[np.ndarray]) -> "LearnedPredictor"`: train on all frames inside periods with label in H/A/D. `HistGradientBoostingClassifier(max_iter=max_iter, learning_rate=0.05, max_leaf_nodes=63, l2_regularization=1.0, random_state=0)`. Stores the class prior from the training labels.
  - `proba(self, track) -> np.ndarray` (T, 3) with columns H, A, D.
  - `decode(self, proba, periods, switch_cost=None, dead_cost=None) -> np.ndarray`: `viterbi` with the stored prior and the instance costs unless overridden.
  - `__call__(self, track) -> np.ndarray`: `decode(proba(track), track.periods)`.
  - `train_on_external(seed: int = 1) -> LearnedPredictor` (module function): loads the 7 IDSSE matches, degrades each with `load_config()` and `np.random.default_rng(match_seed(seed, id))`, then fits.

- [ ] **Step 1: Write failing tests** with two synthetic matches whose labels follow the ball's nearest team, and D where the ball is outside the pitch:
  - `test_fit_predict_learns_simple_rule`: frame accuracy > 0.9 on a third synthetic match.
  - `test_deterministic`: two fresh fit + call runs are `np.array_equal`.
  - `test_labels_alphabet_and_length`: output length T and alphabet a subset of {H, A, D}, including frames where every player is NaN.
  - `test_decode_override_costs`: `decode(p, periods, switch_cost=0, dead_cost=0)` equals the argmax of `p / prior`.
- [ ] **Step 2: Run** → FAIL. Add the dependency, `uv pip install -e ".[dev]"`, `make lock`.
- [ ] **Step 3: Implement** `learned.py`. Don't register in `PREDICTORS` yet (Task 4).
- [ ] **Step 4: Run** the whole suite with `make test` and `make lint` → PASS.
- [ ] **Step 5: Commit** `feat(predictors): learned per-frame classifier + HMM decoding`, including the lock file.

### Task 4: Bench and submission wiring

**Files:**
- Modify: `src/mtah/eval/harness.py`, `scripts/bench.py`, `src/mtah/predictors/__init__.py`
- Test: `tests/eval/test_bench.py`

**Interfaces:**
- Produces:
  - `bench_learned(make_model: Callable[[], LearnedPredictor], decoders: dict[str, tuple[float, float]], match_ids, cfg, seed=0) -> DataFrame`. For each IDSSE match, fit on the other IDSSE matches (degraded with `seed + 1`) and score the held-out match degraded with `seed`. For Metrica, fit once on all 7 IDSSE matches. Each fold calls `proba` once and scores every `(switch_cost, dead_cost)` decoder variant as predictor `learned_s{switch}_d{dead}`. Returns rows in the same schema as `bench`, then `summarise`.
  - `PREDICTORS["learned"]`: a callable that runs `train_on_external()` once (lazy, cached in the module) and then predicts. That way `make submission --predictor learned` works on the human's machine (needs the IDSSE cache: `python scripts/fetch_external.py`).
  - `scripts/bench.py --learned`: runs `bench_learned` with the grid switch ∈ {2, 4, 8, 16, 32} × dead ∈ {1, 2, 4, 8}, concatenated with the baseline rows.
- [ ] **Step 1: Write a failing test** `test_bench_learned_folds_exclude_heldout` that monkeypatches `load_external` to synthetic matches `["J1","J2","J3","metrica1"]` and records the training ids per fit. Assert each IDSSE fold never trains on its own id, Metrica trains on all three IDSSE ids, and one row comes back per (decoder, match) plus per-source MEAN rows.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement**. `IDSSE_MATCHES` stays the training pool. Metrica is never trained on.
- [ ] **Step 4: Run** `make test`, `make lint` → PASS.
- [ ] **Step 5: Commit** `feat(bench): leave-one-match-out bench for the learned predictor; register 'learned'`.

### Task 5: Select on the bench, log, hand over

- [ ] **Step 1:** Run `.venv/bin/python -W ignore scripts/bench.py --learned`. Record the best `MEAN idsse` decoder and check that Metrica ranks it above baseline50.
- [ ] **Step 2:** Set the `LearnedPredictor` default costs to the winning pair. Add a test that the defaults match the chosen pair, so it can't drift silently.
- [ ] **Step 3:** If `MEAN idsse` doesn't beat 0.2299 by more than 0.04 (the noise band), stop and report. Look at the per-class D F1 and the spell counts before touching anything else.
- [ ] **Step 4:** Log run 4 in `docs/EXPERIMENTS.md` (best variant plus the 2 neighbours). Add `D-001` (decoder costs, how they were chosen) and `D-002` (training only on external IDSSE) to `docs/DECISIONS.md`, with a timeline row in `docs/CASE_STUDY.md`.
- [ ] **Step 5:** Commit, then hand the human the exact commands: `python scripts/fetch_external.py` (if not cached), `make submission` with `--predictor learned`, `make eval`. They paste back aggregates only.
