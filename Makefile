PY := PYTHONPATH=src .venv/bin/python

help:  ## list every command
	@grep -E '^[a-zA-Z_-]+:.*## ' Makefile | awk 'BEGIN {FS = ":.*## "}; {printf "  %-16s %s\n", $$1, $$2}'

.PHONY: help setup test lint all data verify-data allstars audit features core segments robustness dashboard-data dashboard-check dashboard
setup:  ## create the environment from the lock file
	python3 -m venv .venv
	$(PY) -m pip install -r requirements-lock.txt
	$(PY) -m pip install -e .
test:   ## run unit tests
	$(PY) -m pytest -q
lint:   ## run the linter (ruff)
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
core:  ## Stage 5: core test on the analysis half
	$(PY) run_all.py --stage 5
segments:  ## Stage 6: H1-H4 on the analysis half
	$(PY) run_all.py --stage 6
robustness:  ## Stage 7: variations, specification curve, placebos (analysis half)
	$(PY) run_all.py --stage 7
dashboard-data:  ## Stage 8: pre-aggregate the tables the dashboard reads
	$(PY) -m hothand.dashboard_data
dashboard-check:  ## Stage 8: displayed-vs-CSV check (run before every deploy)
	$(PY) dashboard/check_numbers.py
dashboard:  ## Stage 8: run the dashboard locally
	.venv/bin/streamlit run dashboard/app.py
