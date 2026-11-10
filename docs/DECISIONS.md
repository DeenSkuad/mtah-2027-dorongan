# Decisions Log

One entry per choice that changes labels. These feed the "possession rules" section of the tech doc.

## Template

### D-NNN — <title> (YYYY-MM-DD, owner)
- **Context:** what situation / ambiguity
- **Decision:** the rule we implement
- **Evidence:** GT frames / experiment # that support it
- **Alternatives rejected:** and why

---

### D-001 — Learned possession model trained on external matches only (2026-11-10, Claude)
- **Context:** the baselines (nearest player + vote) never predict D while the ball is visible, and miscount possessions.
- **Decision:** per-frame features (`mtah.features`) → `HistGradientBoostingClassifier` (random_state 0) trained on the 7 IDSSE matches after degradation (seed 1). Never trained on this match (R2) or the public 5 min (R3). Metrica is not used for training, because its labels are rebuilt from events and defined differently.
- **Evidence:** EXPERIMENTS run 4: MEAN idsse 0.4804 vs 0.2299 (leave-one-match-out), Metrica 0.5366 vs 0.4154.
- **Alternatives rejected:** hand rules for dead ball (the classifier learns them jointly); training on Metrica (label definitions differ).

### D-002 — Viterbi decoding with switch cost 8 and dead cost 8 (2026-11-10, Claude)
- **Context:** per-frame argmax flickers and inflates the spell count, which spellF1 punishes.
- **Decision:** `mtah.decode.viterbi` with prior-corrected emissions, H↔A switch cost 8 and alive↔D cost 8, decoded per period.
- **Evidence:** a 5×4 grid on MEAN idsse in run 4. s8_d8 is best on both IDSSE and Metrica. Its neighbours are within 0.01, so the choice is stable. d = 8 is the grid edge, but the gains toward it are below the noise band.
- **Alternatives rejected:** a fixed vote window (the baselines); per-match tuning (R4).

### D-003 — Train the submission model on a mix of degradation scenarios (2026-11-10, Claude)
- **Context:** the final review warned that the uniform ball-dropout simulation may not match the match's tracking (non-random ball loss, off-pitch ball, players out of view).
- **Decision:** `train_on_external` degrades every IDSSE match under all five `SCENARIOS` (default, edge, slow, players, all), on top of `load_config()`, keeping every 5th frame so the training size stays unchanged. The human-run measurement script now also writes the four realism knobs measured on the match, so "default" becomes the measured tracking.
- **Evidence:** EXPERIMENTS run 5. Mean over scenarios 0.485 vs 0.435 for default-only training, better in every scenario including default (0.497 vs 0.480). Metrica 0.617 vs 0.537.
- **Alternatives rejected:** default-only training (fragile under player dropout); dropping the ball-visibility features (no gain, run C).

## Open questions

- Loose ball after a tackle: keep previous team, switch, or `D`?
- When does a restart (throw-in, free kick, corner) flip from `D` to alive?
- Aerial duels / clearances with no clear controller.
- Ball invisible for long stretches: carry last label vs infer from player shape?
