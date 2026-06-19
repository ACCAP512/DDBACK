# Drawback Engine — developer entrypoints
# Quick start:   make setup && make run     then open http://localhost:8000
PY := .venv/bin/python
PIP := .venv/bin/pip

.PHONY: help setup venv frontend run dev test samples clean

help:
	@echo "make setup     - create venv, install Python deps, build the frontend"
	@echo "make run       - serve API + built SPA at http://localhost:8000 (one process)"
	@echo "make dev       - API on :8000 + Vite dev server on :5173 (two processes)"
	@echo "make test      - run the engine test suite (pytest)"
	@echo "make samples   - regenerate samples/ (CSVs, estimate, claim files)"
	@echo "make clean     - remove venv, node_modules, build output"

venv:
	@test -d .venv || python3 -m venv .venv
	@$(PIP) install -q --upgrade pip
	@$(PIP) install -q -r requirements.txt

frontend:
	@cd web && npm install && npm run build

setup: venv frontend samples
	@echo "Setup complete. Run 'make run' and open http://localhost:8000"

run:
	@$(PY) -m uvicorn api.main:app --host 127.0.0.1 --port 8000

dev:
	@echo "Start the API:   $(PY) -m uvicorn api.main:app --port 8000"
	@echo "In another shell: cd web && npm run dev   (Vite proxies /api -> :8000)"
	@$(PY) -m uvicorn api.main:app --host 127.0.0.1 --port 8000

test:
	@$(PY) -m pytest

samples:
	@PYTHONPATH=engine $(PY) scripts/make_samples.py

clean:
	@rm -rf .venv web/node_modules web/dist filing_out engine/**/__pycache__ .pytest_cache
