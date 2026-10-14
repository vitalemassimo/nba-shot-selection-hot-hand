PY := .venv/bin/python

.PHONY: setup test lint all
setup:  ## create the environment from the lock file
	python3 -m venv .venv
	$(PY) -m pip install -r requirements-lock.txt
	$(PY) -m pip install -e .
test:   ## run unit tests
	$(PY) -m pytest -q
lint:
	$(PY) -m ruff check src tests run_all.py
all:    ## regenerate every result from raw data
	$(PY) run_all.py
