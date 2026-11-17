PY := .venv/bin/python -W ignore
TEAM ?= Dorongan
PREDICTOR ?= learned

.PHONY: help setup lock test e2e lint bench baseline eval validate submission measure sync notebook

help:            ## list targets
	@grep -E '^[a-z]+:.*##' $(MAKEFILE_LIST) | sed 's/:.*##/\t/'

setup:           ## create .venv (Python 3.12, uv), install the pinned lock + mtah (R5)
	uv venv --python 3.12.12 .venv
	uv pip install --python .venv/bin/python -r requirements/lock.txt
	uv pip install --python .venv/bin/python --no-deps -e .

lock:            ## pin the exact environment (R5)
	uv pip freeze --exclude-editable > requirements/lock.txt

test:            ## unit tests (no match data, no network)
	$(PY) -m pytest -q

e2e:             ## Playwright tests of the viewer page (installed Chrome, synthetic tracking)
	$(PY) -m pytest -q -m e2e tests/e2e

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

submission: measure  ## build evaluation/results/$(TEAM).csv (HUMAN: reads match data)
	$(PY) scripts/make_submission.py --predictor $(PREDICTOR) --name $(TEAM)
	$(PY) evaluation/validate_submission.py evaluation/results/$(TEAM).csv
	shasum -a 256 evaluation/results/$(TEAM).csv

measure:         ## measure tracking-quality stats into config/degradation.local.json (HUMAN)
	$(PY) scripts/measure_degradation.py

sync:            ## merge upstream fixes from Metrica
	git fetch upstream && git merge upstream/main

notebook:        ## jupyter lab
	.venv/bin/jupyter lab
