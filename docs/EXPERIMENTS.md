# Experiment Log

Scores are on the **public 5 minutes** only (`make eval`) — a sanity check, not the leaderboard.
Public GT: 17 possessions, mean 14.2 s. Watch `poss` and `dur` as much as the F1s.

| # | Date | Who | Submission file | Idea / params | macroF1 | spellF1 | poss | dur (s) | Notes |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 2026-10-31 | setup | baseline_smooth125 | nearest player, ±125 vote | 0.5812 | 0.4242 | 16 | 18.5 | full-match floor 0.2433 |
| 0 | 2026-10-31 | setup | baseline_smooth50 | ±50 vote | 0.6207 | 0.3256 | 26 | 10.8 | |
| 0 | 2026-10-31 | setup | baseline_smooth25 | ±25 vote | 0.6200 | 0.2868 | 36 | 7.6 | |
| 0 | 2026-10-31 | setup | baseline_raw | no smoothing | 0.5972 | 0.0378 | 131 | 2.0 | |
