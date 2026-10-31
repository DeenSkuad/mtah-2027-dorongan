# References

Curated for this challenge; one line on why each matters. Researched 2026-10-31.

## Possession from tracking data
- **Vidal-Codina et al. 2022**, *Automatic event detection in football using tracking data*, Sports Engineering — rule-based possession/duel zones, >90% P/R on passes and set pieces; the best rule baseline to reimplement. https://arxiv.org/abs/2202.00804
- **Link & Hoernig 2017**, *Individual ball possession in soccer*, PLOS ONE — possession start/end by reachability; human raters only κ=0.72, a realistic ceiling. https://pmc.ncbi.nlm.nih.gov/articles/PMC5503225
- **Kim et al. 2026, PathCRF** (KDD) — possession without the ball: one "possession edge" per frame plus CRF/Viterbi; closest to our problem. https://www.arxiv.org/abs/2602.12080 · code https://github.com/hyunsungkim-ds/pathcrf
- Graph recurrent networks for player–ball interaction (Frontiers 2021). https://pmc.ncbi.nlm.nih.gov/articles/PMC8319236

## Missing ball
- **Kim et al. 2023, ballradar** (KDD) — Set Transformer + Bi-LSTM possessor classifier and ball-trajectory inference. https://arxiv.org/abs/2306.08206 · https://github.com/pientist/ballradar
- **Capellera et al. 2024, TranSPORTmer** (ACCV) — masked transformer; per-frame pass / possession / uncontrolled / out-of-play. https://arxiv.org/abs/2410.17785

## Dead ball / ball in play
- **Lang et al. 2022**, Scientific Reports — in/out of play from player positions only, 92% frame accuracy on unseen matches. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9522646/

## Video (optional)
- roboflow/sports — YOLO ball/player detection, team clustering, pitch keypoints. https://github.com/roboflow/sports
- SoccerNet Team Ball Action Spotting 2025 — team-labelled ball actions incl. Out / Throw-in. https://github.com/SoccerNet/sn-teamspotting

## External labelled data
- **IDSSE / Bassek et al. 2025**, Scientific Data (CC-BY) — 7 Bundesliga matches, 25 fps, per-frame BallPossession + BallStatus. Our internal validation set. https://huggingface.co/datasets/pysport/idsse-data · https://doi.org/10.1038/s41597-025-04505-y
- Metrica Sports sample data — 3 games, tracking + events. https://github.com/metrica-sports/sample-data
- SkillCorner open data — broadcast tracking with realistic gaps. https://github.com/skillcorner/opendata

## Libraries
- kloppy — unified loaders (`ball_owning_team`, `ball_state`). https://github.com/PySport/kloppy
- floodlight — DFL parser with possession / ball-status codes, kinematics. https://pypi.org/project/floodlight/
- databallpy — event–tracking sync, possession features. https://github.com/alek050/databallpy
- mplsoccer — pitch plots for QA. https://mplsoccer.readthedocs.io
- hmmlearn — HMM decoding (or ~30 lines of numpy Viterbi). https://hmmlearn.readthedocs.io

## Claude Code & workflow
- CLAUDE.md / memory. https://docs.claude.com/en/docs/claude-code/memory
- Settings & permissions. https://docs.claude.com/en/docs/claude-code/settings
- Hooks (our R1 guard). https://docs.claude.com/en/docs/claude-code/hooks
- Subagents (`.claude/agents/`). https://docs.claude.com/en/docs/claude-code/sub-agents
- Claude Code best practices. https://www.anthropic.com/engineering/claude-code-best-practices
- superpowers (process skills). https://github.com/obra/superpowers
