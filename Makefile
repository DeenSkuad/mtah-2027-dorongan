PY := .venv/bin/python -W ignore

.PHONY: setup baseline eval validate submission sync notebook

setup:
	python3 -m venv .venv
	.venv/bin/pip install -r requirements/upstream.txt -r requirements/upstream-starter.txt jupyter

baseline:
	$(PY) starter/baseline.py

eval:
	$(PY) evaluation/run_evaluation.py

validate:
	@test -n "$(F)" || (echo "usage: make validate F=path/to/submission.csv" && exit 1)
	$(PY) evaluation/validate_submission.py $(F)

submission:
	$(PY) scripts/make_submission.py

sync:
	git fetch upstream && git merge upstream/main

notebook:
	.venv/bin/jupyter lab
