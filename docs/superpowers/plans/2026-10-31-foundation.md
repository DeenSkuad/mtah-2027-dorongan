# Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A professional, rule-safe project foundation: Claude guardrails, an installable `mtah` package with a clean architecture, an internal benchmark that scores any predictor on degraded public Bundesliga matches with Metrica's own metric, and a match runner that produces a validated submission while printing only aggregate scores.

**Architecture:** Everything flows through one data contract, `MatchTracking` (players, teams, ball, periods, in metres). Loaders (match / external) produce it; `degrade` perturbs it; predictors map it to a label array; `eval.harness` scores labels with `evaluation/possession_metrics.evaluate`; `submit` writes and validates the CSV. Claude develops only against external data; match code paths print aggregates only.

**Tech Stack:** Python 3.12 (uv-managed venv), numpy, pandas, kloppy 3.18, pytest, ruff. Claude Code: `CLAUDE.md`, `.claude/settings.json` permissions + PreToolUse hook, `.claude/agents/*.md` subagents.

**Spec:** `docs/superpowers/specs/2026-10-31-operating-plan-design.md`

## Global Constraints

- R1: no match data, video or extracts may reach Claude. Claude never reads `data/`, `*.mp4`, `*_atd.*`, `*_homography.csv`, `*_smart_tagging.xml`, or `config/*.local.json`.
- Code that runs on the match prints only aggregate metrics (spell F1, macro F1, spell counts, mean durations, row counts) — never frames, rows, coordinates or segment lists.
- Label alphabet and codes exactly as `evaluation/possession_metrics.py`: `LABELS = ("H","A","D","X")`, `H, A, D, X = 0, 1, 2, 3`.
- Submission: header `frame,label`, exactly 199,319 rows, frames `0..199318`, validated with `possession_metrics.validate_submission`.
- Never edit upstream files (`evaluation/`, `starter/`, `games.py`, upstream `*.md`) — import them.
- Tests touching the match are marked `match`; tests needing internet are marked `network`. Default `pytest` run excludes both. Claude never runs `-m match`.
- Deterministic: every random step takes an explicit `numpy.random.Generator` / seed.
- Pitch for the match: 105.3 × 68 m, ATD coordinates normalised 0–1. FPS = 25.

## Review Focus

1. A period boundary inside an external match must not create or merge spells — expect the harness to score periods as separate runs (test in Task 4).
2. Ball missing for an entire window / whole period — predictors and harness must not crash or emit NaN labels (test in Task 7).
3. Hook bypass via Bash (`cat data/...`, `python -c "open('data/...')"`, `head *_atd.txt`) — expect a block (test in Task 1).
4. Degradation must hit the requested missing-ball fraction within ±2 pp and never un-hide an already-missing ball (test in Task 6).
5. Submission with any non-HADX value or wrong length must fail loudly before being written (test in Task 8).

---

## Target folder structure

```
barcelona/
├─ CLAUDE.md                     project rules for Claude (R1 first)
├─ PROJECT.md                    team hub (exists)
├─ pyproject.toml                package + tool config (ruff, pytest markers)
├─ Makefile                      setup / test / lint / bench / submission / eval / validate / sync
├─ .claude/
│  ├─ settings.json              permissions.deny + PreToolUse hook (committed, team-wide)
│  ├─ hooks/guard_match_data.py  blocks any tool call touching match data
│  └─ agents/                    researcher, data-engineer, modeler, evaluator, reviewer
├─ config/
│  ├─ degradation.default.json   literature defaults (committed)
│  └─ degradation.local.json     measured on the match locally (git-ignored, Claude never reads)
├─ src/mtah/
│  ├─ constants.py               labels/codes, FPS, pitch, paths
│  ├─ schema.py                  MatchTracking dataclass
│  ├─ io/match.py                BAR-ATH loader → MatchTracking (human-run only)
│  ├─ io/external.py             IDSSE/DFL via kloppy → MatchTracking + gt labels
│  ├─ degrade.py                 ball dropout + ID switches
│  ├─ predictors/baseline.py     nearest-player + vote (port of starter, for parity)
│  ├─ eval/harness.py            score() + bench() using the official metric
│  ├─ submit.py                  write + validate CSV
│  └─ report.py                  aggregate-only printing
├─ scripts/
│  ├─ bench.py                   predictor × external holdouts → table
│  ├─ make_submission.py         match → CSV → validate → aggregate report
│  └─ measure_degradation.py     match stats → config/degradation.local.json (human-run)
├─ tests/                        mirrors src/mtah
├─ notebooks/                    NN_initials_topic.ipynb (external data only when shared with Claude)
└─ docs/  ARCHITECTURE.md, REFERENCES.md, PLAN.md, EXPERIMENTS.md, DECISIONS.md, TECHNICAL_REPORT.md
```

---

### Task 1: Claude guardrails (R1 enforcement)

**Files:**
- Create: `CLAUDE.md`, `.claude/settings.json`, `.claude/hooks/guard_match_data.py`
- Modify: `.gitignore` (append `config/*.local.json`, `!.claude/`)
- Test: `tests/test_guard_hook.py`

**Interfaces:**
- Produces: `guard_match_data.py` reads the hook JSON on stdin (`{"tool_name": str, "tool_input": {...}}`), exits `2` with a reason on stderr to block, `0` to allow. Exposes `is_blocked(tool_name: str, tool_input: dict) -> str | None` for tests.

- [ ] **Step 1: Write the failing tests** — parametrised `test_blocks` over:
  `("Read", {"file_path": "/x/barcelona/data/tactical/BAR-ATH_tactical_atd.txt"})`,
  `("Grep", {"path": "data/"})`, `("Bash", {"command": "head -5 data/tactical/BAR-ATH_tactical_atd.txt"})`,
  `("Bash", {"command": "python -c \"open('data/x')\""})`, `("Bash", {"command": "ffmpeg -i BAR-ATH_tactical.mp4 f.png"})`,
  `("Read", {"file_path": "config/degradation.local.json"})` → each `is_blocked(...)` is a non-empty str.
  `test_allows` over `("Read", {"file_path": "evaluation/gt/BAR-ATH_possession_gt_public.csv"})`,
  `("Read", {"file_path": "data/README.md"})`, `("Bash", {"command": "make bench"})`, `("Bash", {"command": "pytest -q"})` → `None`.
  `test_exit_code`: run the script via `subprocess` with a blocked payload on stdin → returncode 2.
- [ ] **Step 2: Run** `pytest tests/test_guard_hook.py -v` → FAIL (module missing).
- [ ] **Step 3: Implement** — scan every string value in `tool_input` for regex
  `(^|[\s/'"=])data/(?!README\.md)|\.mp4\b|_atd\.(txt|xml)|_homography\.csv|_smart_tagging\.xml|\.local\.json`;
  message: `"Blocked by R1: match data must not reach a cloud LLM. Ask a human to run it locally."`.
  `settings.json`: `permissions.deny` = `["Read(./data/**)", "Edit(./data/**)", "Read(./config/*.local.json)", "Read(**/*.mp4)"]`; `hooks.PreToolUse` matcher `"Read|Edit|Write|Grep|Glob|Bash|NotebookEdit"` running `python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/guard_match_data.py"`.
  `CLAUDE.md` (≤60 lines): R1–R7 verbatim from spec §2; how Claude works (§3); commands (`make test|lint|bench`); never run `make submission`, `make eval`, `pytest -m match`; experiment logging rule; architecture pointer to `docs/ARCHITECTURE.md`.
- [ ] **Step 4: Run** `pytest tests/test_guard_hook.py -v` → PASS. Then in Claude Code ask it to `Read data/tactical/BAR-ATH_tactical_atd.xml` → blocked message shown.
- [ ] **Step 5: Commit** `feat(guard): enforce R1 with CLAUDE.md, permissions and PreToolUse hook`

### Task 2: Package, tooling and constants

**Files:**
- Create: `pyproject.toml`, `src/mtah/__init__.py`, `src/mtah/constants.py`, `tests/conftest.py`, `tests/test_constants.py`
- Modify: `Makefile`, `requirements-lock.txt` (regenerate), delete `src/possession/`
- Test: `tests/test_constants.py`

**Interfaces:**
- Produces: `mtah.constants`: `LABELS`, `H, A, D, X`, `FPS = 25`, `MATCH_PITCH = (105.3, 68.0)`, `N_MATCH_FRAMES = 199_319`, `REPO_ROOT: Path`, `DATA_DIR: Path` (honours `MTAH_DATA_DIR`), `RESULTS_DIR = REPO_ROOT/"evaluation/results"`. `mtah.constants.official_metrics()` → the imported `possession_metrics` module (adds `REPO_ROOT/"evaluation"` to `sys.path` once).

- [ ] **Step 1: Write the failing test** — `test_codes_match_official`: `official_metrics().LABELS == LABELS` and `(H,A,D,X) == (0,1,2,3)`; `test_data_dir_env(monkeypatch, tmp_path)`: setting `MTAH_DATA_DIR` changes `DATA_DIR` after `importlib.reload`.
- [ ] **Step 2: Run** `pytest tests/test_constants.py -v` → FAIL.
- [ ] **Step 3: Implement.** Recreate venv: `uv venv --python 3.12 .venv && uv pip install -e ".[dev]"`. `pyproject.toml`: project `mtah`, `requires-python = ">=3.12"`, deps `numpy`, `pandas`, `kloppy==3.18.*`; extra `dev` = `pytest`, `ruff`, `jupyterlab`, `matplotlib`, `mplsoccer`; `[tool.pytest.ini_options] addopts = "-m 'not match and not network'"`, markers `match`, `network`; ruff line-length 100. Makefile adds `test`, `lint`, `bench`, `measure` and switches `setup` to uv; regenerate lock with `uv pip freeze > requirements-lock.txt`.
- [ ] **Step 4: Run** `make test` → PASS; `make lint` → clean; `make baseline && make eval` still reproduce spellF1 0.4242 for `baseline_smooth125`.
- [ ] **Step 5: Commit** `build: mtah package on Python 3.12 with uv, pytest markers, ruff`

### Task 3: `MatchTracking` data contract

**Files:**
- Create: `src/mtah/schema.py`, `tests/test_schema.py`

**Interfaces:**
- Produces:
```python
@dataclass(frozen=True)
class MatchTracking:
    players: np.ndarray      # (T, N, 2) float32 metres, NaN when slot absent
    team_of_slot: np.ndarray # (N,) int8: 0 home, 1 away, -1 other (referee/unknown)
    ball: np.ndarray         # (T, 2) float32 metres, NaN when missing
    periods: tuple[tuple[int, int], ...]  # half-open frame spans, sorted, non-overlapping
    pitch: tuple[float, float]            # (length, width) metres, origin at a corner
    fps: int = 25
    def n_frames(self) -> int
    def validate(self) -> None  # raises ValueError on shape/dtype/period problems
```
- [ ] **Step 1: Failing tests** — `test_validate_ok` on a 100×4 synthetic; `test_validate_rejects` for players/ball length mismatch, `team_of_slot` length ≠ N, overlapping periods, period beyond T.
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement.** **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat(schema): MatchTracking contract`

### Task 4: Evaluation harness on the official metric

**Files:**
- Create: `src/mtah/eval/__init__.py`, `src/mtah/eval/harness.py`, `src/mtah/report.py`, `tests/eval/test_harness.py`

**Interfaces:**
- Consumes: `official_metrics().evaluate`, `MatchTracking.periods`.
- Produces:
  - `score(gt: np.ndarray, pred: np.ndarray, periods) -> dict` — `gt`/`pred` are `<U1` arrays over `HADX`; returns `{"spell_f1", "macro_f1", "n_gt_spells", "n_pred_spells", "mean_spell_s", "gt_mean_spell_s"}` copied from `evaluate()` keys `spell_f1_mean, macro_f1, n_gt_spells, n_pred_spells, mean_spell_duration_s, gt_mean_spell_duration_s`. Period separation: build arrays with one `X` frame inserted between consecutive periods (in both gt and pred) so `valid_runs` splits them.
  - `Predictor = Callable[[MatchTracking], np.ndarray]`
  - `report.summary(name: str, scores: dict) -> str` — one line, only the dict's numeric aggregates.

- [ ] **Step 1: Failing tests**
  - `test_perfect`: `score(gt, gt.copy(), ((0,len(gt)),))["spell_f1"] == 1.0`.
  - `test_period_boundary_not_merged`: gt = `H`×50 in period 0 and `H`×50 in period 1, pred identical → `n_gt_spells == 2`, `spell_f1 == 1.0`.
  - `test_matches_official_on_public_gt`: score `evaluation/results/baseline_smooth125.csv` against the public GT with `periods=((0, 199319),)` → `spell_f1 == pytest.approx(0.4242, abs=1e-4)`.
  - `test_summary_has_no_arrays`: `summary` output contains no `[` and is under 200 chars.
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement.** **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat(eval): harness wrapping the official possession metric`

### Task 5: External data loader (IDSSE / DFL via kloppy)

**Files:**
- Create: `src/mtah/io/__init__.py`, `src/mtah/io/external.py`, `scripts/fetch_external.py`, `tests/io/test_external.py`

**Interfaces:**
- Produces:
  - `IDSSE_MATCHES = ("J03WMX", "J03WN1", "J03WOH", "J03WOY", "J03WPY", "J03WQQ", "J03WR9")` (verify against kloppy docs in Step 3; fix list if different).
  - `load_idsse(match_id: str, cache_dir: Path) -> tuple[MatchTracking, np.ndarray]` — labels `<U1`: `D` when `frame.ball_state` is dead, else `H`/`A` from `frame.ball_owning_team` vs `metadata.teams[0]` (home). Coordinates in metres, origin at a corner, from `metadata.pitch_dimensions`. Cached to `cache_dir/<id>.npz` after first load. `cache_dir` default `~/.cache/mtah/idsse` (outside repo).
- [ ] **Step 1: Failing tests** — `@pytest.mark.network test_load_one`: first match → `track.validate()` passes; `labels` only in `{"H","A","D"}`; `0.3 < (labels=="H").mean() < 0.7`; `(labels=="D").mean() > 0.05`; `len(track.periods) == 2`. Non-network `test_label_mapping` on a tiny fake frame list via a private `_labels_from_frames(frames, home_team)`.
- [ ] **Step 2: Run** `pytest tests/io -m network -v` → FAIL.
- [ ] **Step 3: Implement**; `scripts/fetch_external.py` downloads + caches all 7 and prints per-match frame count and label shares (external data — fine to show Claude). **Spec C5 check:** if possession/ball-state are absent, stop and report to the team (fallback: SkillCorner + Metrica).
- [ ] **Step 4: Run** network test → PASS; `python scripts/fetch_external.py` → 7 rows.
- [ ] **Step 5: Commit** `feat(io): IDSSE/DFL loader with possession + ball-state labels`

### Task 6: Degradation to match our tracking quality

**Files:**
- Create: `src/mtah/degrade.py`, `config/degradation.default.json`, `scripts/measure_degradation.py`, `tests/test_degrade.py`

**Interfaces:**
- Produces:
  - `@dataclass DegradeConfig(ball_missing_frac: float = 0.41, gap_len_median_frames: int = 25, gap_len_sigma: float = 1.0, id_switch_per_min: float = 2.0)`; `load_config() -> DegradeConfig` reads `config/degradation.local.json` if present else the default file.
  - `degrade(track: MatchTracking, cfg: DegradeConfig, rng: np.random.Generator) -> MatchTracking` — ball gaps with log-normal lengths placed until the missing fraction is reached; ID switches = swapping the trajectories of two same-team slots from a random frame onward.
  - `measure_degradation.py` (human-run on the match): computes the same four stats and writes the local JSON; prints only "written".
- [ ] **Step 1: Failing tests** on a synthetic 30 000-frame track: `test_missing_fraction` within ±0.02; `test_never_unhides` (already-NaN ball stays NaN); `test_deterministic` (same seed → identical arrays); `test_team_preserved` (per-frame set of home positions unchanged by ID switches).
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement.** **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat(degrade): ball dropout and ID-switch simulation`

### Task 7: Baseline predictor + benchmark

**Files:**
- Create: `src/mtah/predictors/__init__.py`, `src/mtah/predictors/baseline.py`, `scripts/bench.py`, `tests/predictors/test_baseline.py`, `tests/eval/test_bench.py`
- Modify: `src/mtah/eval/harness.py`

**Interfaces:**
- Consumes: `MatchTracking`, `degrade`, `load_idsse`, `score`.
- Produces:
  - `nearest_player(track, window: int = 125) -> np.ndarray` — same semantics as `starter/baseline.py` (`nearest_player_labels` + `smooth`), vectorised over `(T, N)`, `D` where no ball in window.
  - `bench(predictors: dict[str, Predictor], match_ids, cfg: DegradeConfig, seed: int = 0) -> pd.DataFrame` — rows per (predictor, match) plus a `MEAN` row per predictor; columns = `score()` keys.
  - `scripts/bench.py [--predictors baseline25,baseline125] [--matches all]` prints the table and appends a dated CSV to `docs/bench/` (external data only).
- [ ] **Step 1: Failing tests** — `test_all_ball_missing`: track with NaN ball → output all `D`, no exception; `test_parity_shape` on synthetic; `@network test_bench_runs`: 2 predictors × 1 match → 4 rows, `0 <= spell_f1 <= 1`.
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement.** **Step 4: Run** → PASS; `make bench` prints the table.
- [ ] **Step 5: Commit** `feat(bench): baseline predictor and external benchmark`; log the bench means in `docs/EXPERIMENTS.md` as experiment #1.

### Task 8: Match loader + submission runner (human-run)

**Files:**
- Create: `src/mtah/io/match.py`, `src/mtah/submit.py`, `tests/test_submit.py`, `tests/io/test_match.py`
- Modify: `scripts/make_submission.py` (replace placeholder)

**Interfaces:**
- Consumes: `starter/baseline.team_of_each_track`, `games.asset_paths`, constants.
- Produces:
  - `load_match(data_dir: Path = DATA_DIR) -> MatchTracking` — parses the tactical ATD (format as in `starter/baseline.nearest_player_labels`), metres via `MATCH_PITCH`, `periods = ((0, N_MATCH_FRAMES),)`.
  - `write_submission(labels: np.ndarray, path: Path) -> Path` — raises `ValueError` before writing if length ≠ 199 319 or any label ∉ HADX; after writing, re-reads and runs `validate_submission`; raises on any reason.
  - `make_submission.py --predictor baseline125 --name <team>` → writes `evaluation/results/<team>.csv`, prints `report.summary` of the public-GT score and `"valid, 199319 rows"`. Nothing else.
- [ ] **Step 1: Failing tests** — `test_rejects_bad_length`, `test_rejects_bad_label`, `test_roundtrip_valid(tmp_path)`; `@pytest.mark.match test_load_match_shape` asserting only `n_frames()==199319` and `team_of_slot.size==46` with messages that print no data.
- [ ] **Step 2: Run** non-match tests → FAIL. **Step 3: Implement.** **Step 4: Run** → PASS. *Human* runs `pytest -m match` and `make submission` → spellF1 for baseline125 equals 0.4242 (parity with upstream).
- [ ] **Step 5: Commit** `feat(submit): match loader and validated submission runner`

### Task 9: Agents, architecture and references docs

**Files:**
- Create: `.claude/agents/{researcher,data-engineer,modeler,evaluator,reviewer}.md`, `docs/ARCHITECTURE.md`, `docs/REFERENCES.md`
- Modify: `PROJECT.md` (folder map, commands), `docs/PLAN.md` (Phase 0 done, Phase 1 = this plan)

- [ ] **Step 1:** Each agent file has frontmatter `name`, `description`, `tools` (reviewer/researcher read-only: `Read, Grep, Glob, WebSearch, WebFetch`), and a body restating R1 plus its role from spec §6. Reviewer checklist = R1–R6 + "no frame-specific constants" + "seeds explicit".
- [ ] **Step 2:** `ARCHITECTURE.md` — the data-flow diagram (loader → MatchTracking → degrade → predictor → harness / submit), the module table, the match/external boundary, and how to add a predictor (one function + one `bench` line).
- [ ] **Step 3:** `REFERENCES.md` — grouped links with one-line relevance: Vidal-Codina 2022 (arXiv 2202.00804), Link & Hoernig 2017 (PMC5503225), PathCRF (arXiv 2602.12080), ballradar (arXiv 2306.08206), TranSPORTmer (arXiv 2410.17785), Lang et al. 2022 (PMC9522646), IDSSE dataset (huggingface pysport/idsse-data), kloppy, floodlight, databallpy, roboflow/sports, sn-teamspotting; plus Claude Code docs: memory/CLAUDE.md, settings & permissions, hooks, subagents, and obra/superpowers.
- [ ] **Step 4: Verify** `make test && make lint` pass; `claude` lists the 5 agents under `/agents`.
- [ ] **Step 5: Commit** `docs: architecture, references, Claude subagents`
