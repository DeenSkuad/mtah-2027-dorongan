# Architecture

## Data flow

```
                    ┌──────────────────────── external (Claude may see) ───────────────────────┐
 IDSSE / DFL  ──►  io/external.load_idsse ─┐
 Metrica ×2   ──►  io/metrica.load_metrica ┴► load_external ──► MatchTracking + true labels
                                                   │
                                          degrade.degrade(cfg)   ◄── config/degradation.*.json
                                                   │
                                          predictor(track)  ──►  labels (H/A/D/X)
                                                   │
                                          eval/harness.score  ──►  scripts/bench.py  ──►  docs/bench/*.csv
                    └──────────────────────────────────────────────────────────────────────────┘

                    ┌──────────────────────── match (humans only, R1) ─────────────────────────┐
 tactical ATD  ──►  io/match.load_match ──► MatchTracking ──► predictor ──► submit.write_submission
                                                                             │
                                                    report.summary (aggregates only) ◄─┘
                    └──────────────────────────────────────────────────────────────────────────┘
```

The same predictor code runs on both sides. Only `MatchTracking` crosses the boundary — never
match values.

## Modules

| Module | Responsibility |
|---|---|
| `mtah.constants` | label codes (identical to the official scorer), FPS, pitch, paths, `official_metrics()` |
| `mtah.schema` | `MatchTracking`: players `(T,N,2)`, `team_of_slot (N,)`, ball `(T,2)`, periods, pitch — metres, corner origin, NaN = missing; `infer_periods` (halves from player presence) |
| `mtah.io.external` | IDSSE/DFL download + parse + `.npz` cache in `~/.cache/mtah/idsse`; `load_external` / `EXTERNAL_MATCHES` registry |
| `mtah.io.metrica` | Metrica sample games 1-2; labels rebuilt from events; cache in `~/.cache/mtah/metrica` |
| `mtah.io.match` | BAR-ATH tactical ATD → `MatchTracking`, periods via `infer_periods` (human-run) |
| `mtah.degrade` | ball dropout (log-normal gaps to a target fraction) + same-team ID switches |
| `mtah.features` | `frame_features(track)` → `(T, 34)` team-aggregate features; direction from a ±2.5 min centroid vote |
| `mtah.decode` | `viterbi(proba, periods, switch_cost, dead_cost, prior)` → H/A/D path, per period |
| `mtah.predictors` | `PREDICTORS` registry; `baseline.nearest_player` = upstream parity; `learned.LearnedPredictor` (HistGB + Viterbi) and `predict_learned` (trains on IDSSE on first use) |
| `mtah.eval.harness` | `score()` via the official `evaluate()`; `bench()` over degraded external matches; `bench_learned()` leave-one-match-out for trainable predictors; per-source `summarise()` |
| `mtah.submit` | contract checks before writing, official validation after |
| `mtah.report` | the only way match-side code prints: one line of aggregates |

## Adding a predictor

1. `src/mtah/predictors/<name>.py`: `def my_predictor(track: MatchTracking) -> np.ndarray`.
2. Register it in `PREDICTORS` (with `functools.partial` for parameters).
3. Unit tests in `tests/predictors/` on synthetic tracks (incl. ball fully missing).
4. `make bench` → compare against `baseline*`; log the MEAN row in `docs/EXPERIMENTS.md`.
5. A human runs `make submission PREDICTOR=<name>` (default: `learned`, file `Dorongan.csv`).

## Test markers

`make test` runs everything except `network` (external downloads) and `match` (humans only).
Run network tests with `.venv/bin/python -m pytest -m network`.
