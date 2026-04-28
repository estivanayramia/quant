@echo off
setlocal EnableDelayedExpansion
set TARGET=%1
if "%TARGET%"=="" set TARGET=help

if "%TARGET%"=="install" (
  python -m pip install -e ".[dev]"
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="format" (
  python -m ruff format .
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="lint" (
  python -m ruff check .
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="test" (
  python -m pytest
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="test-cov" (
  python -m pytest --cov=quant_os --cov-report=term-missing
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="seed-demo" (
  python -m quant_os.cli seed-demo
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="validate-data" (
  python -m quant_os.cli validate-data
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="backtest" (
  python -m quant_os.cli backtest
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="tournament" (
  python -m quant_os.cli tournament
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="shadow" (
  python -m quant_os.cli shadow
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="rebuild" (
  python -m quant_os.cli rebuild-read-models
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="report" (
  python -m quant_os.cli report
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="autonomous" (
  python -m quant_os.cli autonomous run-once
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="autonomous-daemon" (
  python -m quant_os.cli autonomous daemon --interval-minutes 60 --max-cycles 1
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="autonomous-status" (
  python -m quant_os.cli autonomous status
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="watchdog" (
  python -m quant_os.cli watchdog
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="drift" (
  python -m quant_os.cli drift
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="alerts-test" (
  python -m quant_os.cli alerts-test
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="freqtrade-config" (
  python -m quant_os.cli freqtrade generate-config
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="freqtrade-validate" (
  python -m quant_os.cli freqtrade validate
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="freqtrade-export-strategy" (
  python -m quant_os.cli freqtrade export-strategy
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="freqtrade-status" (
  python -m quant_os.cli freqtrade status
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="freqtrade-command-preview" (
  python -m quant_os.cli freqtrade command-preview
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="freqtrade-manifest" (
  python -m quant_os.cli freqtrade manifest
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="freqtrade-dry-run-check" (
  python -m quant_os.cli freqtrade dry-run-check
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="freqtrade-docker-check" (
  python -m quant_os.cli freqtrade docker-check
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="freqtrade-dry-run-start" (
  python -m quant_os.cli freqtrade dry-run-start
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="freqtrade-dry-run-stop" (
  python -m quant_os.cli freqtrade dry-run-stop
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="freqtrade-dry-run-logs" (
  python -m quant_os.cli freqtrade dry-run-logs
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="freqtrade-dry-run-status" (
  python -m quant_os.cli freqtrade dry-run-status
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="freqtrade-dry-run-report" (
  python -m quant_os.cli freqtrade dry-run-report
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="freqtrade-ingest-logs" (
  python -m quant_os.cli freqtrade ingest-logs
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="freqtrade-reconcile" (
  python -m quant_os.cli freqtrade reconcile
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="freqtrade-operational-manifest" (
  python -m quant_os.cli freqtrade operational-manifest
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="freqtrade-artifacts-scan" (
  python -m quant_os.cli freqtrade artifacts-scan
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="freqtrade-trades-ingest" (
  python -m quant_os.cli freqtrade trades-ingest
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="freqtrade-trades-normalize" (
  python -m quant_os.cli freqtrade trades-normalize
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="freqtrade-trade-reconcile" (
  python -m quant_os.cli freqtrade trade-reconcile
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="freqtrade-trade-report" (
  python -m quant_os.cli freqtrade trade-report
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="dryrun-history" (
  python -m quant_os.cli dryrun history
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="dryrun-compare" (
  python -m quant_os.cli dryrun compare
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="dryrun-divergence-check" (
  python -m quant_os.cli dryrun divergence-check
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="dryrun-monitor-report" (
  python -m quant_os.cli dryrun monitor-report
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="dryrun-promote-check" (
  python -m quant_os.cli dryrun promote-check
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="dryrun-status" (
  python -m quant_os.cli dryrun status
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="dryrun-trade-reconcile" (
  python -m quant_os.cli dryrun trade-reconcile
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="dryrun-trade-report" (
  python -m quant_os.cli dryrun trade-report
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="features-build" (
  python -m quant_os.cli features build
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="strategy-research" (
  python -m quant_os.cli strategy research
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="strategy-ablation" (
  python -m quant_os.cli strategy ablation
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="strategy-walk-forward" (
  python -m quant_os.cli strategy walk-forward
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="strategy-regime-tests" (
  python -m quant_os.cli strategy regime-tests
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="strategy-overfit-check" (
  python -m quant_os.cli strategy overfit-check
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="strategy-leaderboard" (
  python -m quant_os.cli strategy leaderboard
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="strategy-research-report" (
  python -m quant_os.cli strategy research-report
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="dataset-seed-expanded" (
  python -m quant_os.cli dataset seed-expanded
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="dataset-manifest" (
  python -m quant_os.cli dataset manifest
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="dataset-quality" (
  python -m quant_os.cli dataset quality
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="dataset-splits" (
  python -m quant_os.cli dataset splits
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="dataset-leakage-check" (
  python -m quant_os.cli dataset leakage-check
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="dataset-evidence-score" (
  python -m quant_os.cli dataset evidence-score
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="research-evidence-report" (
  python -m quant_os.cli evidence research-report
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="historical-import-csv" (
  python -m quant_os.cli historical import-csv
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="historical-normalize" (
  python -m quant_os.cli historical normalize
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="historical-manifest" (
  python -m quant_os.cli historical manifest
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="historical-quality" (
  python -m quant_os.cli historical quality
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="historical-splits" (
  python -m quant_os.cli historical splits
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="historical-evidence-score" (
  python -m quant_os.cli historical evidence-score
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="historical-research-report" (
  python -m quant_os.cli historical research-report
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="historical-provider-check" (
  python -m quant_os.cli historical provider-check
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="historical-status" (
  python -m quant_os.cli historical status
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="phase3-smoke" (
  python -m quant_os.cli freqtrade generate-config
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli freqtrade export-strategy
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli freqtrade validate
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli freqtrade dry-run-check
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli freqtrade status
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli autonomous run-once
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m pytest
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="phase4-smoke" (
  python -m quant_os.cli freqtrade generate-config
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli freqtrade export-strategy
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli freqtrade validate
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli freqtrade dry-run-check
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli freqtrade docker-check
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli freqtrade ingest-logs
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli freqtrade reconcile
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli freqtrade dry-run-status
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli autonomous run-once
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m pytest
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="phase5-smoke" (
  call "%~f0" phase4-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli dryrun history
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli dryrun compare
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli dryrun divergence-check
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli dryrun monitor-report
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli dryrun promote-check
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli autonomous run-once
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m pytest
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="phase6-smoke" (
  call "%~f0" phase5-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli freqtrade artifacts-scan
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli freqtrade trades-ingest
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli freqtrade trades-normalize
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli freqtrade trade-reconcile
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli freqtrade trade-report
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli autonomous run-once
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m pytest
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="phase7-smoke" (
  call "%~f0" phase6-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli features build
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli strategy research
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli strategy ablation
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli strategy walk-forward
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli strategy regime-tests
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli strategy overfit-check
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli strategy leaderboard
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli strategy research-report
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli autonomous run-once
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m pytest
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="phase8-smoke" (
  call "%~f0" phase7-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli dataset seed-expanded
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli dataset manifest
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli dataset quality
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli dataset splits
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli dataset leakage-check
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli dataset evidence-score
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli evidence research-report
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli autonomous run-once
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m pytest
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="phase9-smoke" (
  call "%~f0" phase8-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli historical provider-check
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli historical import-csv
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli historical normalize
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli historical manifest
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli historical quality
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli historical splits
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli historical evidence-score
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli historical research-report
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli autonomous run-once
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m pytest
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="smoke" (
  python -m quant_os.cli smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m pytest tests/test_smoke.py tests/test_risk_firewall.py tests/test_event_replay.py
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="clean" (
  python -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in ['data/demo','data/events','data/read_models','.pytest_cache','.ruff_cache','htmlcov']]; [path.unlink() for path in pathlib.Path('reports').glob('*') if path.name != '.gitkeep']"
  exit /b !ERRORLEVEL!
)

echo Unknown target: %TARGET%
exit /b 2
