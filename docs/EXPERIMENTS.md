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

## Public 5 minutes — sanity only, never for selection (R3)

Scores are on the **public 5 minutes** only (`make eval`) — a sanity check, not the leaderboard.
Public GT: 17 possessions, mean 14.2 s. Watch `poss` and `dur` as much as the F1s.

| # | Date | Who | Submission file | Idea / params | macroF1 | spellF1 | poss | dur (s) | Notes |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 2026-10-31 | setup | baseline_smooth125 | nearest player, ±125 vote | 0.5812 | 0.4242 | 16 | 18.5 | full-match floor 0.2433 |
| 0 | 2026-10-31 | setup | baseline_smooth50 | ±50 vote | 0.6207 | 0.3256 | 26 | 10.8 | |
| 0 | 2026-10-31 | setup | baseline_smooth25 | ±25 vote | 0.6200 | 0.2868 | 36 | 7.6 | |
| 0 | 2026-10-31 | setup | baseline_raw | no smoothing | 0.5972 | 0.0378 | 131 | 2.0 | |
