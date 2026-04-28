.PHONY: install format lint test test-cov seed-demo validate-data backtest tournament shadow rebuild report smoke autonomous autonomous-daemon autonomous-status watchdog drift alerts-test freqtrade-config freqtrade-validate freqtrade-export-strategy freqtrade-status freqtrade-command-preview freqtrade-manifest freqtrade-dry-run-check freqtrade-docker-check freqtrade-dry-run-start freqtrade-dry-run-stop freqtrade-dry-run-logs freqtrade-dry-run-status freqtrade-dry-run-report freqtrade-ingest-logs freqtrade-reconcile freqtrade-operational-manifest freqtrade-artifacts-scan freqtrade-trades-ingest freqtrade-trades-normalize freqtrade-trade-reconcile freqtrade-trade-report dryrun-history dryrun-compare dryrun-divergence-check dryrun-monitor-report dryrun-promote-check dryrun-status dryrun-trade-reconcile dryrun-trade-report phase3-smoke phase4-smoke phase5-smoke phase6-smoke clean

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

freqtrade-config:
	python -m quant_os.cli freqtrade generate-config

freqtrade-validate:
	python -m quant_os.cli freqtrade validate

freqtrade-export-strategy:
	python -m quant_os.cli freqtrade export-strategy

freqtrade-status:
	python -m quant_os.cli freqtrade status

freqtrade-command-preview:
	python -m quant_os.cli freqtrade command-preview

freqtrade-manifest:
	python -m quant_os.cli freqtrade manifest

freqtrade-dry-run-check:
	python -m quant_os.cli freqtrade dry-run-check

freqtrade-docker-check:
	python -m quant_os.cli freqtrade docker-check

freqtrade-dry-run-start:
	python -m quant_os.cli freqtrade dry-run-start

freqtrade-dry-run-stop:
	python -m quant_os.cli freqtrade dry-run-stop

freqtrade-dry-run-logs:
	python -m quant_os.cli freqtrade dry-run-logs

freqtrade-dry-run-status:
	python -m quant_os.cli freqtrade dry-run-status

freqtrade-dry-run-report:
	python -m quant_os.cli freqtrade dry-run-report

freqtrade-ingest-logs:
	python -m quant_os.cli freqtrade ingest-logs

freqtrade-reconcile:
	python -m quant_os.cli freqtrade reconcile

freqtrade-operational-manifest:
	python -m quant_os.cli freqtrade operational-manifest

freqtrade-artifacts-scan:
	python -m quant_os.cli freqtrade artifacts-scan

freqtrade-trades-ingest:
	python -m quant_os.cli freqtrade trades-ingest

freqtrade-trades-normalize:
	python -m quant_os.cli freqtrade trades-normalize

freqtrade-trade-reconcile:
	python -m quant_os.cli freqtrade trade-reconcile

freqtrade-trade-report:
	python -m quant_os.cli freqtrade trade-report

dryrun-history:
	python -m quant_os.cli dryrun history

dryrun-compare:
	python -m quant_os.cli dryrun compare

dryrun-divergence-check:
	python -m quant_os.cli dryrun divergence-check

dryrun-monitor-report:
	python -m quant_os.cli dryrun monitor-report

dryrun-promote-check:
	python -m quant_os.cli dryrun promote-check

dryrun-status:
	python -m quant_os.cli dryrun status

dryrun-trade-reconcile:
	python -m quant_os.cli dryrun trade-reconcile

dryrun-trade-report:
	python -m quant_os.cli dryrun trade-report

phase3-smoke:
	python -m quant_os.cli freqtrade generate-config
	python -m quant_os.cli freqtrade export-strategy
	python -m quant_os.cli freqtrade validate
	python -m quant_os.cli freqtrade dry-run-check
	python -m quant_os.cli freqtrade status
	python -m quant_os.cli autonomous run-once
	python -m quant_os.cli smoke
	python -m pytest

phase4-smoke:
	python -m quant_os.cli freqtrade generate-config
	python -m quant_os.cli freqtrade export-strategy
	python -m quant_os.cli freqtrade validate
	python -m quant_os.cli freqtrade dry-run-check
	python -m quant_os.cli freqtrade docker-check
	python -m quant_os.cli freqtrade ingest-logs
	python -m quant_os.cli freqtrade reconcile
	python -m quant_os.cli freqtrade dry-run-status
	python -m quant_os.cli autonomous run-once
	python -m quant_os.cli smoke
	python -m pytest

phase5-smoke:
	$(MAKE) phase4-smoke
	python -m quant_os.cli dryrun history
	python -m quant_os.cli dryrun compare
	python -m quant_os.cli dryrun divergence-check
	python -m quant_os.cli dryrun monitor-report
	python -m quant_os.cli dryrun promote-check
	python -m quant_os.cli autonomous run-once
	python -m quant_os.cli smoke
	python -m pytest

phase6-smoke:
	$(MAKE) phase5-smoke
	python -m quant_os.cli freqtrade artifacts-scan
	python -m quant_os.cli freqtrade trades-ingest
	python -m quant_os.cli freqtrade trades-normalize
	python -m quant_os.cli freqtrade trade-reconcile
	python -m quant_os.cli freqtrade trade-report
	python -m quant_os.cli autonomous run-once
	python -m quant_os.cli smoke
	python -m pytest

smoke:
	python -m quant_os.cli smoke
	python -m pytest tests/test_smoke.py tests/test_risk_firewall.py tests/test_event_replay.py

clean:
	python -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in ['data/demo','data/events','data/read_models','.pytest_cache','.ruff_cache','htmlcov']]; [path.unlink() for path in pathlib.Path('reports').glob('*') if path.name != '.gitkeep']"
