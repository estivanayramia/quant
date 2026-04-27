.PHONY: install format lint test test-cov seed-demo validate-data backtest tournament shadow rebuild report smoke autonomous autonomous-daemon autonomous-status watchdog drift alerts-test clean

install:
	python -m pip install -e ".[dev]"

format:
	python -m ruff format .

lint:
	python -m ruff check .

test:
	python -m pytest

test-cov:
	python -m pytest --cov=quant_os --cov-report=term-missing

seed-demo:
	python -m quant_os.cli seed-demo

validate-data:
	python -m quant_os.cli validate-data

backtest:
	python -m quant_os.cli backtest

tournament:
	python -m quant_os.cli tournament

shadow:
	python -m quant_os.cli shadow

rebuild:
	python -m quant_os.cli rebuild-read-models

report:
	python -m quant_os.cli report

autonomous:
	python -m quant_os.cli autonomous run-once

autonomous-daemon:
	python -m quant_os.cli autonomous daemon --interval-minutes 60 --max-cycles 1

autonomous-status:
	python -m quant_os.cli autonomous status

watchdog:
	python -m quant_os.cli watchdog

drift:
	python -m quant_os.cli drift

alerts-test:
	python -m quant_os.cli alerts-test

smoke:
	python -m quant_os.cli smoke
	python -m pytest tests/test_smoke.py tests/test_risk_firewall.py tests/test_event_replay.py

clean:
	python -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in ['data/demo','data/events','data/read_models','.pytest_cache','.ruff_cache','htmlcov']]; [path.unlink() for path in pathlib.Path('reports').glob('*') if path.name != '.gitkeep']"
