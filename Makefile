PY := .venv/bin/python -W ignore

.PHONY: help setup lock test lint bench baseline eval validate submission measure sync notebook

help:            ## list targets
	@grep -E '^[a-z]+:.*##' $(MAKEFILE_LIST) | sed 's/:.*##/\t/'

setup:           ## create .venv (Python 3.12, uv) and install mtah + dev tools
	uv venv --python 3.12 .venv
	uv pip install -e ".[dev]"

lock:            ## pin the exact environment (R5)
	uv pip freeze --exclude-editable > requirements/lock.txt

test:            ## unit tests (no match data, no network)
	$(PY) -m pytest -q

lint:            ## ruff
	.venv/bin/ruff check src tests scripts

bench:           ## score predictors on degraded external matches (model selection)
	$(PY) scripts/bench.py

baseline:        ## rebuild the upstream reference baselines (HUMAN: reads match data)
	$(PY) starter/baseline.py

eval:            ## official scorer on evaluation/results/ (HUMAN)
	$(PY) evaluation/run_evaluation.py

validate:        ## make validate F=evaluation/results/<file>.csv
	@test -n "$(F)" || (echo "usage: make validate F=path/to/submission.csv" && exit 1)
	$(PY) evaluation/validate_submission.py $(F)

submission:      ## build the team submission (HUMAN: reads match data)
	$(PY) scripts/make_submission.py

measure:         ## measure tracking-quality stats into config/degradation.local.json (HUMAN)
	$(PY) scripts/measure_degradation.py

sync:            ## merge upstream fixes from Metrica
	git fetch upstream && git merge upstream/main

notebook:        ## jupyter lab
	.venv/bin/jupyter lab
