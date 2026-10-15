PY := PYTHONPATH=src .venv/bin/python

.PHONY: setup test lint all data verify-data allstars audit features
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
data:   ## Stage 2: download raw data (cached; re-runs make no new requests)
	$(PY) -m hothand.acquire
verify-data:  ## Stage 2 gate: manifest, volumes, cross-check report
	$(PY) -m hothand.verify_raw
allstars:  ## rebuild data/reference/allstars.csv from Wikipedia
	$(PY) -m hothand.allstars
audit:  ## Stage 3: audit raw data, clean, write data-quality report
	$(PY) run_all.py --stage 3
features:  ## Stage 4: build the feature table and its report notebook
	$(PY) run_all.py --stage 4
