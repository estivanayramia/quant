.PHONY: install format lint test test-cov seed-demo validate-data backtest tournament shadow rebuild report smoke autonomous autonomous-daemon autonomous-status watchdog drift alerts-test freqtrade-config freqtrade-validate freqtrade-export-strategy freqtrade-status freqtrade-command-preview freqtrade-manifest freqtrade-dry-run-check freqtrade-docker-check freqtrade-dry-run-start freqtrade-dry-run-stop freqtrade-dry-run-logs freqtrade-dry-run-status freqtrade-dry-run-report freqtrade-ingest-logs freqtrade-reconcile freqtrade-operational-manifest freqtrade-artifacts-scan freqtrade-trades-ingest freqtrade-trades-normalize freqtrade-trade-reconcile freqtrade-trade-report dryrun-history dryrun-compare dryrun-divergence-check dryrun-monitor-report dryrun-promote-check dryrun-status dryrun-trade-reconcile dryrun-trade-report features-build strategy-research strategy-ablation strategy-walk-forward strategy-regime-tests strategy-overfit-check strategy-leaderboard strategy-research-report dataset-seed-expanded dataset-manifest dataset-quality dataset-splits dataset-leakage-check dataset-evidence-score research-evidence-report historical-import-csv historical-normalize historical-manifest historical-quality historical-splits historical-evidence-score historical-research-report historical-provider-check historical-status proving-run-once proving-status proving-history proving-incidents proving-readiness proving-report canary-policy canary-checklist canary-preflight canary-incident-drill canary-capital-ladder canary-readiness canary-report phase3-smoke phase4-smoke phase5-smoke phase6-smoke phase7-smoke phase8-smoke phase9-smoke phase10-smoke phase11-smoke clean

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

features-build:
	python -m quant_os.cli features build

strategy-research:
	python -m quant_os.cli strategy research

strategy-ablation:
	python -m quant_os.cli strategy ablation

strategy-walk-forward:
	python -m quant_os.cli strategy walk-forward

strategy-regime-tests:
	python -m quant_os.cli strategy regime-tests

strategy-overfit-check:
	python -m quant_os.cli strategy overfit-check

strategy-leaderboard:
	python -m quant_os.cli strategy leaderboard

strategy-research-report:
	python -m quant_os.cli strategy research-report

dataset-seed-expanded:
	python -m quant_os.cli dataset seed-expanded

dataset-manifest:
	python -m quant_os.cli dataset manifest

dataset-quality:
	python -m quant_os.cli dataset quality

dataset-splits:
	python -m quant_os.cli dataset splits

dataset-leakage-check:
	python -m quant_os.cli dataset leakage-check

dataset-evidence-score:
	python -m quant_os.cli dataset evidence-score

research-evidence-report:
	python -m quant_os.cli evidence research-report

historical-import-csv:
	python -m quant_os.cli historical import-csv

historical-normalize:
	python -m quant_os.cli historical normalize

historical-manifest:
	python -m quant_os.cli historical manifest

historical-quality:
	python -m quant_os.cli historical quality

historical-splits:
	python -m quant_os.cli historical splits

historical-evidence-score:
	python -m quant_os.cli historical evidence-score

historical-research-report:
	python -m quant_os.cli historical research-report

historical-provider-check:
	python -m quant_os.cli historical provider-check

historical-status:
	python -m quant_os.cli historical status

proving-run-once:
	python -m quant_os.cli proving run-once

proving-status:
	python -m quant_os.cli proving status

proving-history:
	python -m quant_os.cli proving history

proving-incidents:
	python -m quant_os.cli proving incidents

proving-readiness:
	python -m quant_os.cli proving readiness

proving-report:
	python -m quant_os.cli proving report

canary-policy:
	python -m quant_os.cli canary policy

canary-checklist:
	python -m quant_os.cli canary checklist

canary-preflight:
	python -m quant_os.cli canary preflight

canary-incident-drill:
	python -m quant_os.cli canary incident-drill

canary-capital-ladder:
	python -m quant_os.cli canary capital-ladder

canary-readiness:
	python -m quant_os.cli canary readiness

canary-report:
	python -m quant_os.cli canary report

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

phase7-smoke:
	$(MAKE) phase6-smoke
	python -m quant_os.cli features build
	python -m quant_os.cli strategy research
	python -m quant_os.cli strategy ablation
	python -m quant_os.cli strategy walk-forward
	python -m quant_os.cli strategy regime-tests
	python -m quant_os.cli strategy overfit-check
	python -m quant_os.cli strategy leaderboard
	python -m quant_os.cli strategy research-report
	python -m quant_os.cli autonomous run-once
	python -m quant_os.cli smoke
	python -m pytest

phase8-smoke:
	$(MAKE) phase7-smoke
	python -m quant_os.cli dataset seed-expanded
	python -m quant_os.cli dataset manifest
	python -m quant_os.cli dataset quality
	python -m quant_os.cli dataset splits
	python -m quant_os.cli dataset leakage-check
	python -m quant_os.cli dataset evidence-score
	python -m quant_os.cli evidence research-report
	python -m quant_os.cli autonomous run-once
	python -m quant_os.cli smoke
	python -m pytest

phase9-smoke:
	$(MAKE) phase8-smoke
	python -m quant_os.cli historical provider-check
	python -m quant_os.cli historical import-csv
	python -m quant_os.cli historical normalize
	python -m quant_os.cli historical manifest
	python -m quant_os.cli historical quality
	python -m quant_os.cli historical splits
	python -m quant_os.cli historical evidence-score
	python -m quant_os.cli historical research-report
	python -m quant_os.cli autonomous run-once
	python -m quant_os.cli smoke
	python -m pytest

phase10-smoke:
	$(MAKE) phase9-smoke
	python -m quant_os.cli proving run-once
	python -m quant_os.cli proving status
	python -m quant_os.cli proving history
	python -m quant_os.cli proving incidents
	python -m quant_os.cli proving readiness
	python -m quant_os.cli proving report
	python -m quant_os.cli autonomous run-once
	python -m quant_os.cli smoke
	python -m pytest

phase11-smoke:
	$(MAKE) phase10-smoke
	python -m quant_os.cli canary policy
	python -m quant_os.cli canary checklist
	python -m quant_os.cli canary preflight
	python -m quant_os.cli canary incident-drill
	python -m quant_os.cli canary capital-ladder
	python -m quant_os.cli canary readiness
	python -m quant_os.cli canary report
	python -m quant_os.cli autonomous run-once
	python -m quant_os.cli smoke
	python -m pytest

smoke:
	python -m quant_os.cli smoke
	python -m pytest tests/test_smoke.py tests/test_risk_firewall.py tests/test_event_replay.py

clean:
	python -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in ['data/demo','data/events','data/read_models','.pytest_cache','.ruff_cache','htmlcov']]; [path.unlink() for path in pathlib.Path('reports').glob('*') if path.name != '.gitkeep']"
