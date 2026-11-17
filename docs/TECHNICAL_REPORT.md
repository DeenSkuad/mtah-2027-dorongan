# Technical Report — Team Dorongan

More than a Hack 2027, Phase 1: Ball Possession (BAR–ATH, 199,319 frames).
Code: https://github.com/DeenSkuad/mtah-2027-dorongan · Submission file: `Dorongan.csv`.

## 1. Approach

**In one line:** per-frame tracking features → gradient-boosted classifier giving P(H, A, D) →
Viterbi decoding with switch costs → one label per frame. The classifier is trained only on
other matches (7 Bundesliga games), after we degraded their tracking to look like ours.

**Why this design.** The task docs say the ground truth is derived *mechanically* from corrected
tracking: `D` where the tracking marks the ball dead, otherwise the team it names as owner. The
IDSSE / DFL open dataset (Bassek et al. 2025) has exactly that pair of flags, per frame, for 7
professional matches. So we can learn the same labelling function from external data instead of
hand-writing possession rules, and we never need a label from the provided game.

The gap between the two is tracking quality: DFL tracking is clean, while ours is automatic (ball
missing on ~41 % of graded frames, fragmented tracks, no identities). We close that gap by
**degrading** the external tracking before training.

- **Base config, measured on our match:** ball gaps (missing fraction, log-normal gap lengths)
  and identity switches. The numbers come from a human-run script (`make measure`, §7) that
  writes a handful of aggregate statistics to a local, git-ignored file. Nothing else leaves the
  match files.
- **Fixed stress scenarios on top:** 4× more ball loss near the lines and in slow play, the ball
  hidden off the pitch, and 15 % player dropout, alone and combined. The model trains on all five
  mixes (default + four stress), so it does not depend on the simulation being exactly right.

**Why not something else.**
- *Nearest-player + vote window* (the organisers' baseline): it never predicts `D` while the ball
  is visible and gets the possession count badly wrong. On our bench it scores spellF1 0.230.
- *Hand-written rules* (reachability, pass detection): many thresholds to tune, and nothing
  legitimate to tune them on. The public 5 minutes are off limits for tuning.
- *Video models* (detectors, action spotting): too expensive for the timeline. The bigger
  win was handling the missing ball in the tracking we already had.

**Pipeline** (`src/mtah/`):

1. **Load** the tactical ATD into one array (`io/match.py`): 2-D positions in metres, team per
   track from the ATD metadata, ball position. Video frame *i* = ATD frame_id − 1.
2. **Periods** (`schema.infer_periods`): playing periods come from player presence alone (≥ 18
   tracked players; gaps < 2 min joined; runs < 5 min dropped). No frame numbers are hard-coded.
3. **Features** (`features.py`, 34 per frame). Every feature is a team aggregate, so it does
   not depend on track order or identity:
   - **ball:** visible or not, position, speed, distance outside the pitch, frames since / until
     last seen
   - **players:** nearest home / away player distance and their difference, players within
     3 m, team centroids and the gap between them, team speeds, share of slow players, tracked
     count, side of the last nearest team
   - **context:** rolling means of 7 of these over ±1 s and ±5 s

   The x axis is mirrored so home always attacks +x. Direction comes from a ±2.5 min majority
   vote of the centroid gap, so the half-time switch is handled without a frame constant.
4. **Classifier:** scikit-learn `HistGradientBoostingClassifier` (300 iterations, learning
   rate 0.05, 63 leaves, L2 1.0, `random_state=0`, no early stopping) giving P(H, A, D).
5. **Decoding** (`decode.py`): Viterbi over three states per period, emissions log P − log prior.
   An H↔A switch costs 8 and any alive↔dead change costs 8 (natural-log units). Frames
   outside every period are `D`.
6. **Write** (`submit.py`): the file is validated with the official `validate_submission` before
   it replaces the target. A bad run can never overwrite a good file.

## 2. Assets used

| Asset | Used? | How / why dropped |
|---|---|---|
| Tactical ATD (tracking + ball) | **Yes** | The only model input: player and ball positions, plus team per track from the ATD metadata |
| Tactical homography | No | The ATD is already in pitch coordinates |
| Smart Tagging | No | Not tried. Its intervals are phases, not possessions, and it is automatic and noisy. Using its restart tags is the first thing we would add (§6) |
| Tactical video | Not in the pipeline | Watched locally only, to understand the data and debug our viewer. No labels, rules or constants came from it |
| Broadcast video / ATD / homography | No | Separate timeline with no mapping to the tactical frames, so it was not worth the risk |
| Public 5-min ground truth | Parity check only | Used to confirm the file is aligned and well-formed. Never used for training, tuning or choosing a model |

**External assets.**
- **IDSSE / DFL open data** (7 Bundesliga matches, CC-BY): training and model selection.
- **Metrica Sports sample games 1–2** (open): second benchmark only, never trained on.
- **Libraries:** `kloppy` 3.19.1 (loading), `scikit-learn` 1.7.2, `numpy`, `pandas`.
  Exact versions are in `requirements/lock.txt`.

**AI assistance.** Code and docs were written with Claude Code, a cloud LLM. The terms forbid
sharing match material with a cloud LLM, so every step that reads the match is run locally by a
person and prints aggregates only. A hook blocks the assistant from match files (`.claude/hooks/`).
A few slips are logged openly in `docs/CASE_STUDY.md` §4:
- a few aggregate statistics seen before the rule was known
- still frames and viewer screenshots pasted by a person into the chat

None of it was used for the model, its features or its settings.

## 3. Training data

| Dataset | Source | Labelled by | Amount | Used for |
|---|---|---|---|---|
| IDSSE (Bassek et al. 2025, *Scientific Data*) | DFL / Sportec Solutions official match data, CC-BY ([doi:10.1038/s41597-025-04505-y](https://doi.org/10.1038/s41597-025-04505-y)); downloaded through `kloppy` from the `pysport/idsse-data` Hugging Face mirror, checked against the SHA-256 list in `config/idsse_sha256.txt` | DFL's data provider: per-frame `BallStatus` and `BallPossession` flags in the official positional data | 7 matches, 1,002,644 frames at 25 fps (11.1 h); matches J03WMX, J03WN1, J03WOH, J03WOY, J03WPY, J03WQQ, J03WR9 | Training (all 7) and model selection (leave-one-match-out) |
| Metrica Sports sample games 1–2 | github.com/metrica-sports/sample-data | Metrica Sports (their published, hand-tagged event file); our code turns the events into per-frame H/A/D (`src/mtah/io/metrica.py`) | 2 matches | Second benchmark only. Not trained on, because its labels are defined differently |

**Label mapping (IDSSE → ours).** `D` when the ball is not alive. Otherwise the owning team. If
the owner is missing, keep the last owner within the period.

**Training set.** Each IDSSE match is degraded 5 times, once per scenario (default, edge, slow,
players, all), each with its own seed. Every 5th in-period frame is kept, so the set is as big as
one copy of the 7 matches (≈ 1.0 M rows).

**Nothing from the provided game is labelled, by anyone, for any purpose.**

## 4. Possession rules implemented

We did not hand-code possession rules. The labels follow the same definition as the ground truth
(ball-dead flag + owning team from corrected tracking), learned from DFL data. Here is what that
means case by case:

- **Ball in play vs dead.** The target is `D` exactly when the reference tracking flags the ball
  dead. The model approximates it from ball speed, ball outside the pitch, players slowing down
  and the ball going missing. Who will restart is not predicted: the task asks for `D`.
- **Loose balls and challenges.** Possession stays with the last team that had it, as in the task
  definition and the DFL flags. On top of that, the H↔A switch cost (8 nats) means the decoder
  changes team only when the evidence for the other team lasts. A brief flip there and back costs
  16 nats, so a touch, a deflection, or an aerial duel without control is *unlikely* to flip the
  label (not guaranteed). This is our proxy for "controlled" possession.
- **Restarts.** Dead → alive costs 8 too, so a throw-in, free kick or corner *tends to* become
  `H`/`A` when play resumes rather than while the ball sits still. The restart team comes from
  the features (nearest team, team shape), not a rule.
- **Before kick-off, half-time, after the whistle.** Outside the inferred periods we write `D`.
  If the periods cover the graded halves, those frames are either ungraded or graded as `D`
  (the second-half lead-in). `make submission` prints how many graded frames fell outside the
  periods (an aggregate, diagnostic only), so a period cut inside a half would be visible.
- **Abstention.** We never write `X`. Under spellF1 an `X` repeats the previous label, which is
  costly across a hand-over, and our decoder already smooths through ball gaps.
- **Not done:** no frame-specific constants for this game, and no hand corrections.

## 5. Results (external benchmark — how we chose)

Every number below is spellF1 on degraded external matches, leave-one-match-out on IDSSE
(`make bench`; full log in `docs/EXPERIMENTS.md`). Organisers' note: differences below ~0.04 are
noise.

| Model | IDSSE mean (7) | Metrica (2) |
|---|---|---|
| Baseline, nearest player ±50 frames | 0.230 | 0.415 |
| Learned, default degradation only | 0.480 | 0.537 |
| **Learned, scenario-mix training (submitted)** | **0.497** | **0.617** |

**Robustness.** The submitted model scores 0.45–0.51 under every stress scenario (edge, slow,
players, all). The default-only model drops to 0.37–0.38 with player dropout. Removing the
ball-visibility features changes the score by at most 0.015 in any scenario (0.006 on the mean).

**Decoder costs.** We searched a 5×4 grid of switch / dead costs with default-only training
(run 4); the top 9 cells are within 0.02. Under the submitted mix we re-checked 3 decoders, all
within 0.01, so the choice is stable.

**Which degradation config.** The bench runs used the committed default config
(`config/degradation.default.json`, 41 % ball missing). The submitted model trains on the same
recipe, with its base config measured from our match (§1).

**Public 5 minutes.** Run only as a parity check that the frames line up. Never used to choose.

## 6. Limitations and future work

- **Domain shift.** Trained on Bundesliga DFL tracking with simulated noise. Real automatic
  tracking fails in ways the simulation does not cover, such as ghost tracks or a wrong ball
  candidate. Identity switches are simulated, and every feature is a team aggregate, so switches
  within a team barely matter. This is the biggest risk to the score.
- **Possession count.** On the bench we still predict fewer possessions than the truth
  (323 vs 437 on IDSSE for the default-trained model, run 4), i.e. some short possessions get
  merged.
- **Selection bias.** Model and decoder were chosen on the same 7 matches as the
  leave-one-match-out folds. Metrica agrees on the ranking, which reduces but does not remove the
  bias.
- **Period inference** assumes ≥ 18 tracked players. A long tracking drop-out inside a half would
  be labelled `D`.
- **Next with more time:**
  - restart tags from the Smart Tagging as a dead-ball signal
  - a sequence model (bi-LSTM / transformer) in place of features + HMM
  - ball-trajectory inference while the ball is missing (ballradar-style)
  - self-training on the provided game's own tracking with pseudo-labels (allowed: no human
    decides any label)
- **Reproducibility scope.** We trained from scratch twice (1 thread vs all threads, macOS arm64)
  and the full pipeline on a synthetic 199,319-frame track wrote byte-identical files (a manual
  check, not a CI test). Another CPU or OS could in theory change floating-point results in the
  gradient boosting.

## 7. Reproduction

```bash
git clone https://github.com/DeenSkuad/mtah-2027-dorongan && cd mtah-2027-dorongan
make setup        # Python 3.12 venv via uv; installs requirements/lock.txt exactly
# unpack the competition bundle into ./data (see data/README.md)
make submission   # 1) make measure: writes config/degradation.local.json from the match
                  # 2) downloads the 7 IDSSE matches once (~/.cache/mtah, needs internet), trains
                  #    with seeds fixed, labels the match -> evaluation/results/Dorongan.csv
                  # 3) runs the official validator and prints the file's SHA-256
```

- **Prerequisites:** macOS or Linux, [uv](https://docs.astral.sh/uv/) (installs Python 3.12.12),
  `make`, `curl`, `shasum`, and internet access to huggingface.co for the first run (~2.6 GB of
  IDSSE XML, verified by checksum).
- **Running time:** 3–5 minutes on an M1 laptop to train and label (measured on a synthetic
  199,319-frame track). Add the two match loads and, on the first run only, the IDSSE download
  and parse.
- **Exact versions:** pinned in `requirements/lock.txt`.
- **Checks without the match:** `make test` (unit tests), `make bench` (the external benchmark).
