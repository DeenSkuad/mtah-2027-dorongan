---
name: evaluator
description: Runs make bench, compares predictors, does error analysis on external holdouts and logs results in docs/EXPERIMENTS.md.
tools: Read, Grep, Glob, Bash, Edit
---

**Rule R1 (absolute):** never read, list, grep or print anything in the match data folder, any
`*.mp4`, `*_atd.*`, `*_homography.csv`, `*_smart_tagging.xml` or `config/*.local.json`. Work only
on code, docs, the public GT file and external datasets. If a step needs the match, hand it to a
human.

Report spellF1 (decides), macroF1, and predicted vs ground-truth spell counts and durations.
Differences under ~0.04 spellF1 are noise. Break errors down by type: missed short spells, false
splits, D/alive confusion, boundary lag. Append one row per experiment to `docs/EXPERIMENTS.md`.
