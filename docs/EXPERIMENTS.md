# Experiment Log

## Internal benchmark (`make bench`) — decides

Degraded IDSSE matches (ball hidden 41%, ID switches). spellF1 differences < 0.04 are noise.
Since run 3 the bench also scores 2 Metrica sample games and reports `MEAN idsse` and
`MEAN metrica` separately. **`MEAN idsse` decides**; Metrica must agree on the ranking.

| # | Date | Who | Predictor | Matches | spellF1 | macroF1 | spells pred/gt | dur pred/gt (s) | Notes |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 2026-10-31 | setup | baseline25 | J03WMX | 0.1882 | 0.4718 | 928/511 | 5.1/6.7 | over-fragmented |
| 1 | 2026-10-31 | setup | **baseline50** | J03WMX | **0.2469** | 0.4594 | 597/511 | 8.7/6.7 | best — same order as organisers' full-match board |
| 1 | 2026-10-31 | setup | baseline125 | J03WMX | 0.1932 | 0.4142 | 313/511 | 18.2/6.7 | over-merged |
| 2 | 2026-10-31 | setup | baseline25 | all 7 | 0.1710 | 0.4336 | 894/437 | 5.2/7.3 | |
| 2 | 2026-10-31 | setup | **baseline50** | all 7 | **0.2299** | 0.4199 | 582/437 | 8.8/7.3 | organisers' full-match floor for this method: 0.2433 — bench tracks the real board closely |
| 2 | 2026-10-31 | setup | baseline125 | all 7 | 0.2052 | 0.3884 | 305/437 | 18.4/7.3 | |
| 3 | 2026-11-10 | setup | baseline25 | metrica ×2 | 0.3620 | 0.8037 | 629/368 | 5.8/10.3 | second provider; labels rebuilt from events (smoother → scores far higher, never pool with IDSSE) |
| 3 | 2026-11-10 | setup | **baseline50** | metrica ×2 | **0.4154** | 0.7955 | 469/368 | 8.1/10.3 | same ranking as IDSSE → bench generalises across providers; IDSSE mean unchanged 0.2299 |
| 3 | 2026-11-10 | setup | baseline125 | metrica ×2 | 0.2902 | 0.7265 | 374/368 | 11.5/10.3 | |
| 4 | 2026-11-10 | claude | **learned_s8_d8** | IDSSE LOMO | **0.4804** | 0.8762 | 323/437 | 9.9/7.3 | features + HistGB + Viterbi (switch 8, dead 8); beats baseline50 on all 7 matches (+0.17 to +0.30) |
| 4 | 2026-11-10 | claude | learned_s16_d8 | IDSSE LOMO | 0.4756 | 0.8758 | 284/437 | 11.2/7.3 | neighbour |
| 4 | 2026-11-10 | claude | learned_s8_d4 | IDSSE LOMO | 0.4742 | 0.8757 | 333/437 | 9.6/7.3 | neighbour; the top 9 of 20 grid cells sit within 0.02 (inside the noise band) |
| 4 | 2026-11-10 | claude | **learned_s8_d8** | metrica ×2 | **0.5366** | 0.8080 | 306/368 | 12.7/10.3 | trained on all 7 IDSSE; also best on Metrica → ranking agrees (baseline50 0.4154) |

**Run 5: robustness matrix** (learned_s8_d8, `MEAN idsse` spellF1 per eval scenario; `scripts/bench.py --learned --train … --eval default,edge,slow,players,all`). Scenarios are in `mtah.degrade.SCENARIOS`: edge = ball lost near the lines and off the pitch, slow = ball lost in slow play, players = 15 % player dropout, all = the three together.

| Train regime | default | edge | slow | players | all | **mean** | Metrica default | Notes |
|---|---|---|---|---|---|---|---|---|
| A: default only | 0.4804 | 0.4513 | 0.4850 | 0.3844 | 0.3713 | 0.4345 | 0.5366 | player dropout costs ~0.10 |
| **B: mix of all 5** | **0.4969** | **0.5106** | **0.5118** | **0.4454** | **0.4602** | **0.4850** | **0.6168** | best in every column; chosen (D-003) |
| C: mix, no ball-visibility features | 0.4947 | 0.4959 | 0.5089 | 0.4436 | 0.4506 | 0.4787 | 0.6068 | ≈ B → the model does not lean on *when* the ball is missing |

Decoders s8_d4 / s16_d8 under B were within 0.01 of s8_d8 in every scenario; s8_d8 kept. Same-folds selection caveat as run 4.

## Public 5 minutes — sanity only, never for selection (R3)

Scores are on the **public 5 minutes** only (`make eval`) — a sanity check, not the leaderboard.
Public GT: 17 possessions, mean 14.2 s. Watch `poss` and `dur` as much as the F1s.

| # | Date | Who | Submission file | Idea / params | macroF1 | spellF1 | poss | dur (s) | Notes |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 2026-10-31 | setup | baseline_smooth125 | nearest player, ±125 vote | 0.5812 | 0.4242 | 16 | 18.5 | full-match floor 0.2433 |
| 0 | 2026-10-31 | setup | baseline_smooth50 | ±50 vote | 0.6207 | 0.3256 | 26 | 10.8 | |
| 0 | 2026-10-31 | setup | baseline_smooth25 | ±25 vote | 0.6200 | 0.2868 | 36 | 7.6 | |
| 0 | 2026-10-31 | setup | baseline_raw | no smoothing | 0.5972 | 0.0378 | 131 | 2.0 | |
| 6 | 2026-11-17 | human | **Dorongan** (submitted) | learned, scenario mix, measured config `7062534d` (chosen on the bench, run 5) | 0.7274 | 0.5000 | 19 | 14.7 | parity only, not used to choose; full match 443 spells, mean 9.9 s; 1,708 of 158,857 graded frames outside inferred periods (written D); SHA-256 `aa679800…4f786b44` |
