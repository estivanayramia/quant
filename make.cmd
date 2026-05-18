@echo off
setlocal EnableDelayedExpansion
set TARGET=%1
if "%TARGET%"=="" set TARGET=help
set "REPO_ROOT=%~dp0"
set "PYTHONPATH=%REPO_ROOT%src;%PYTHONPATH%"

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
if "%TARGET%"=="proving-run-once" (
  python -m quant_os.cli proving run-once
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="proving-status" (
  python -m quant_os.cli proving status
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="proving-history" (
  python -m quant_os.cli proving history
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="proving-incidents" (
  python -m quant_os.cli proving incidents
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="proving-readiness" (
  python -m quant_os.cli proving readiness
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="proving-report" (
  python -m quant_os.cli proving report
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="canary-policy" (
  python -m quant_os.cli canary policy
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="canary-checklist" (
  python -m quant_os.cli canary checklist
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="canary-preflight" (
  python -m quant_os.cli canary preflight
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="canary-incident-drill" (
  python -m quant_os.cli canary incident-drill
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="canary-capital-ladder" (
  python -m quant_os.cli canary capital-ladder
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="canary-readiness" (
  python -m quant_os.cli canary readiness
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="canary-report" (
  python -m quant_os.cli canary report
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="canary-permission-import" (
  python -m quant_os.cli canary permission-import
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="canary-arm-token" (
  python -m quant_os.cli canary arm-token
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="canary-preflight-rehearsal" (
  python -m quant_os.cli canary preflight-rehearsal
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="canary-stoploss-proof" (
  python -m quant_os.cli canary stoploss-proof
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="canary-rehearsal" (
  python -m quant_os.cli canary rehearsal
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="canary-final-gate" (
  python -m quant_os.cli canary final-gate
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="canary-rehearsal-report" (
  python -m quant_os.cli canary rehearsal-report
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="canary-exchange-capabilities" (
  python -m quant_os.cli canary exchange-capabilities
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="canary-live-prepare" (
  python -m quant_os.cli canary live-prepare
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="canary-live-preflight" (
  python -m quant_os.cli canary live-preflight
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="canary-live-fire" (
  python -m quant_os.cli canary live-fire
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="canary-live-status" (
  python -m quant_os.cli canary live-status
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="canary-live-reconcile" (
  python -m quant_os.cli canary live-reconcile
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="canary-live-stop" (
  python -m quant_os.cli canary live-stop
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="canary-live-report" (
  python -m quant_os.cli canary live-report
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
if "%TARGET%"=="phase10-smoke" (
  call "%~f0" phase9-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli proving run-once
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli proving status
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli proving history
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli proving incidents
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli proving readiness
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli proving report
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli autonomous run-once
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m pytest
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="phase11-smoke" (
  call "%~f0" phase10-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli canary policy
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli canary checklist
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli canary preflight
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli canary incident-drill
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli canary capital-ladder
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli canary readiness
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli canary report
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli autonomous run-once
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m pytest
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="phase12-smoke" (
  call "%~f0" phase11-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli canary permission-import
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli canary arm-token
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli canary preflight-rehearsal
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli canary stoploss-proof
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli canary rehearsal
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli canary final-gate
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli canary rehearsal-report
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli autonomous run-once
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m pytest
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="phase13-smoke" (
  call "%~f0" phase12-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli canary live-prepare
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli canary live-preflight
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli canary live-status
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli canary live-reconcile
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli canary live-stop
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli canary live-report
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli autonomous run-once
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m pytest
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="phase14-smoke" (
  python -m quant_os.cli canary exchange-capabilities
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli canary live-prepare
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli canary live-preflight
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli canary live-status
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli canary live-reconcile
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli canary live-stop
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli canary live-report
  if errorlevel 1 exit /b !ERRORLEVEL!
  del /f /q reports\autonomy\run.lock 2>nul
  python -m quant_os.cli autonomous run-once --runbook phase14_live_canary_cycle
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
if "%TARGET%"=="crypto-research" (
  python -m quant_os.cli data validate
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli research crypto-build
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="replay-smoke" (
  python -m quant_os.cli replay run
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="calibration-smoke" (
  python -m quant_os.cli calibration run
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="validation-smoke" (
  python -m quant_os.cli validation list-scenarios
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli validation run-all
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="replay-realism-smoke" (
  python -m quant_os.cli replay realism-report
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="walk-forward-smoke" (
  python -m quant_os.cli validation walk-forward
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="dry-run-proving-smoke" (
  python -m quant_os.cli proving dry-run-proving
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="venue-calibration-smoke" (
  python -m quant_os.cli calibration venue-report
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="calibrated-edge-smoke" (
  python -m quant_os.cli research calibrated-edge-report
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="prediction-market-capture-smoke" (
  python -m quant_os.cli data capture-prediction-markets
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="prediction-market-quality-smoke" (
  python -m quant_os.cli research prediction-market-quality
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="prediction-market-wallet-smoke" (
  python -m quant_os.cli research prediction-market-wallet-report
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="sequence20-smoke" (
  call "%~f0" prediction-market-capture-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  call "%~f0" prediction-market-quality-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  call "%~f0" prediction-market-wallet-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli research prediction-market-priority
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m pytest tests/test_sequence20_prediction_market_research.py
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="prediction-history-smoke" (
  python -m quant_os.cli research prediction-history-build
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="prediction-candidate-smoke" (
  python -m quant_os.cli research prediction-feature-report
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli research prediction-candidate-report
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="sequence21-smoke" (
  call "%~f0" prediction-history-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  call "%~f0" prediction-candidate-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m pytest tests/test_sequence21_prediction_candidate_research.py
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="prediction-history-expand-smoke" (
  python -m quant_os.cli research prediction-history-expand
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="prediction-candidate-eval-smoke" (
  python -m quant_os.cli research prediction-candidate-eval
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="replay-feasibility-smoke" (
  python -m quant_os.cli research replay-feasibility
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="sequence22-smoke" (
  call "%~f0" prediction-history-expand-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  call "%~f0" prediction-candidate-eval-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  call "%~f0" replay-feasibility-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m pytest tests/test_sequence22_replay_feasibility.py
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="prediction-lane-selection-smoke" (
  python -m quant_os.cli research prediction-lane-selection
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="prediction-signal-smoke" (
  python -m quant_os.cli research prediction-signal-report
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="prediction-lane-eval-smoke" (
  python -m quant_os.cli research prediction-lane-eval
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="sequence23-smoke" (
  call "%~f0" prediction-lane-selection-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  call "%~f0" prediction-signal-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  call "%~f0" prediction-lane-eval-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli research replay-feasibility --lane-aware
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m pytest tests/test_sequence23_signal_discovery.py
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="lane-activity-smoke" (
  python -m quant_os.cli research lane-activity-build
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="dynamic-signal-smoke" (
  python -m quant_os.cli research dynamic-signal-report
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="wallet-flow-smoke" (
  python -m quant_os.cli research wallet-flow-report
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="lane-replay-readiness-smoke" (
  python -m quant_os.cli research lane-replay-readiness
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="sequence24-smoke" (
  call "%~f0" lane-activity-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  call "%~f0" dynamic-signal-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  call "%~f0" wallet-flow-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  call "%~f0" lane-replay-readiness-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m pytest tests/test_sequence24_lane_activity_readiness.py
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="polymarket-activity-capture-smoke" (
  python -m quant_os.cli data capture-polymarket-activity
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="lane-activity-dataset-smoke" (
  python -m quant_os.cli research lane-activity-dataset
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="lane-activity-quality-smoke" (
  python -m quant_os.cli research lane-activity-quality
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="activity-signal-eval-smoke" (
  python -m quant_os.cli research activity-signal-evaluation
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="sequence25-smoke" (
  call "%~f0" polymarket-activity-capture-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  call "%~f0" lane-activity-dataset-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  call "%~f0" lane-activity-quality-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  call "%~f0" activity-signal-eval-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli research real-activity-replay-readiness
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m pytest tests/test_sequence25_polymarket_activity_ingestion.py
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="resolved-history-growth-smoke" (
  python -m quant_os.cli research resolved-history-growth
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="label-quality-smoke" (
  python -m quant_os.cli research label-quality
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="lane-oos-validation-smoke" (
  python -m quant_os.cli research lane-oos-validation
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="lane-robustness-smoke" (
  python -m quant_os.cli research lane-robustness
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="oos-replay-readiness-smoke" (
  python -m quant_os.cli research oos-replay-readiness
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="sequence26-smoke" (
  call "%~f0" resolved-history-growth-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  call "%~f0" label-quality-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  call "%~f0" lane-oos-validation-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  call "%~f0" lane-robustness-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  call "%~f0" oos-replay-readiness-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m pytest tests/test_sequence26_resolved_history_oos_validation.py
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="sequence-benchmark-smoke" (
  python -m quant_os.cli data source-registry-report
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli research external-benchmark-report
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m pytest tests/test_external_benchmark_sources.py
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="reference-context-smoke" (
  python -m quant_os.cli research reference-context-report
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="reference-quality-smoke" (
  python -m quant_os.cli research reference-quality-report
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="venue-market-quality-smoke" (
  python -m quant_os.cli research market-quality-report
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli research manipulation-flags-report
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="venue-signal-smoke" (
  python -m quant_os.cli research venue-signal-report
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli research venue-ablation-report
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="lane-decision-smoke" (
  python -m quant_os.cli research lane-decision
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli research venue-replay-readiness
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="sequence27-smoke" (
  call "%~f0" reference-context-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  call "%~f0" reference-quality-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  call "%~f0" venue-market-quality-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  call "%~f0" venue-signal-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  call "%~f0" lane-decision-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m pytest tests/test_sequence27_venue_specific_signal_discovery.py
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="sequence28-smoke" (
  python -m quant_os.cli research lane-retirement
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli research next-lane-selection-v2
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli research replay-input-summary
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli research replay-input-readiness
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m pytest tests/test_sequence28_lane_retirement_replay_inputs.py
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="replay-design-smoke" (
  python -m quant_os.cli replay design-report
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="shadow-execution-smoke" (
  python -m quant_os.cli replay shadow-execution-report
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="shadow-autonomy-smoke" (
  python -m quant_os.cli readiness shadow-autonomy
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="sequence31-smoke" (
  call "%~f0" replay-design-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  call "%~f0" shadow-execution-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  call "%~f0" shadow-autonomy-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m pytest tests/test_sequence31_shadow_replay_autonomy.py
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="shadow-proving-smoke" (
  python -m quant_os.cli proving shadow-proving-report
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="canary-preconditions-smoke" (
  python -m quant_os.cli readiness canary-preconditions
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="canary-blockers-smoke" (
  python -m quant_os.cli readiness canary-blockers
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="sequence32-smoke" (
  call "%~f0" shadow-proving-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  call "%~f0" canary-preconditions-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  call "%~f0" canary-blockers-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m pytest tests/test_sequence32_shadow_proving_canary_preconditions.py
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="shadow-sample-windows-smoke" (
  python -m quant_os.cli proving shadow-sample-windows
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="shadow-blocker-attribution-smoke" (
  python -m quant_os.cli proving shadow-blocker-attribution
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="shadow-sensitivity-smoke" (
  python -m quant_os.cli proving shadow-sensitivity
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="shadow-unblockability-smoke" (
  python -m quant_os.cli proving unblockability
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="shadow-rehearsal-smoke" (
  python -m quant_os.cli readiness shadow-rehearsal
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="sequence33-smoke" (
  call "%~f0" shadow-sample-windows-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  call "%~f0" shadow-blocker-attribution-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  call "%~f0" shadow-sensitivity-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  call "%~f0" shadow-unblockability-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  call "%~f0" shadow-rehearsal-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m pytest tests/test_sequence33_shadow_sample_unblockability.py
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="social-intake-smoke" (
  python -m quant_os.cli research social-capture-inventory
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli research social-post-classification
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="hypothesis-queue-smoke" (
  python -m quant_os.cli research social-hypothesis-queue
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli research social-task-queue
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="evidence-acquisition-smoke" (
  python -m quant_os.cli research evidence-acquisition-plan
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="sequence34-smoke" (
  call "%~f0" social-intake-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  call "%~f0" hypothesis-queue-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  call "%~f0" evidence-acquisition-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m pytest tests/test_sequence34_social_research_intake.py
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="research-intake-smoke" (
  python -m quant_os.cli research intake-source-policy
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli research intake-run
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli research knowledge-ledger-summary
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="autonomy-milestones-smoke" (
  python -m quant_os.cli research evidence-to-shadow-bridge
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli readiness autonomy-milestones
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="sequence35-smoke" (
  call "%~f0" research-intake-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  call "%~f0" autonomy-milestones-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m pytest tests/test_sequence35_governed_intake_runner.py
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="pm-crypto-updown-dataset-smoke" (
  python -m quant_os.cli research pm-crypto-updown-dataset
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli research pm-crypto-updown-quality
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="replay-dataset-readiness-smoke" (
  python -m quant_os.cli readiness replay-dataset-readiness
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="sequence36-smoke" (
  call "%~f0" pm-crypto-updown-dataset-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  call "%~f0" replay-dataset-readiness-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m pytest tests/test_sequence36_pm_crypto_updown_replay_dataset.py
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="pm-crypto-updown-replay-eval-smoke" (
  python -m quant_os.cli research pm-crypto-updown-replay-eval
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli research pm-crypto-updown-placebo
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="pm-crypto-updown-shadow-bridge-smoke" (
  python -m quant_os.cli research pm-crypto-updown-shadow-bridge
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="candidate-replay-readiness-smoke" (
  python -m quant_os.cli readiness candidate-replay-readiness
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="sequence37-smoke" (
  call "%~f0" pm-crypto-updown-replay-eval-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  call "%~f0" candidate-replay-readiness-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  call "%~f0" pm-crypto-updown-shadow-bridge-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m pytest tests/test_sequence37_pm_crypto_updown_replay_eval.py
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="pm-crypto-updown-evidence-expansion-smoke" (
  python -m quant_os.cli research pm-crypto-updown-expansion-plan
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli research pm-crypto-updown-manual-capture-plan
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli research pm-crypto-updown-expanded-dataset
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli research pm-crypto-updown-evidence-quality
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli research pm-crypto-updown-expanded-replay-eval
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="expanded-shadow-replay-readiness-smoke" (
  python -m quant_os.cli readiness expanded-shadow-replay
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="sequence38-smoke" (
  call "%~f0" pm-crypto-updown-evidence-expansion-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  call "%~f0" expanded-shadow-replay-readiness-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m pytest tests/test_sequence38_pm_crypto_updown_evidence_expansion.py
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="pm-crypto-updown-real-cached-import-smoke" (
  python -m quant_os.cli data pm-crypto-updown-capture-plan
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli data pm-crypto-updown-real-cached-import --import-root tests\fixtures\replay_candidates\pm_crypto_updown\real_cached_sample
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli research pm-crypto-updown-threshold-progress --real-cached-root tests\fixtures\replay_candidates\pm_crypto_updown\real_cached_sample
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="real-cached-replay-readiness-smoke" (
  python -m quant_os.cli research pm-crypto-updown-real-cached-replay-eval --real-cached-root tests\fixtures\replay_candidates\pm_crypto_updown\real_cached_sample
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli readiness real-cached-replay-readiness --real-cached-root tests\fixtures\replay_candidates\pm_crypto_updown\real_cached_sample
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="sequence39-smoke" (
  call "%~f0" pm-crypto-updown-real-cached-import-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  call "%~f0" real-cached-replay-readiness-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m pytest tests/test_sequence39_real_cached_replay_capture.py
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="sequence40-smoke" (
  python -m quant_os.cli data pm-crypto-updown-capture-plan --manual-network-ok --run-id pm_crypto_updown_manual_001
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli data pm-crypto-updown-real-cached-import --import-root data\external\manual_captures\pm_crypto_updown\pm_crypto_updown_manual_001
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli research pm-crypto-updown-threshold-progress --real-cached-root tests\fixtures\replay_candidates\pm_crypto_updown\real_cached_sample --real-cached-root data\external\manual_captures\pm_crypto_updown\pm_crypto_updown_manual_001
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli research pm-crypto-updown-real-cached-replay-eval --real-cached-root tests\fixtures\replay_candidates\pm_crypto_updown\real_cached_sample --real-cached-root data\external\manual_captures\pm_crypto_updown\pm_crypto_updown_manual_001
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli readiness real-cached-replay-readiness --real-cached-root tests\fixtures\replay_candidates\pm_crypto_updown\real_cached_sample --real-cached-root data\external\manual_captures\pm_crypto_updown\pm_crypto_updown_manual_001
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m pytest tests/test_sequence40_real_cached_replay_threshold.py
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="pm-crypto-updown-window-acquisition-smoke" (
  python -m quant_os.cli data pm-crypto-updown-capture-plan --manual-network-ok --run-id pm_crypto_updown_manual_041
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli research pm-crypto-updown-window-acquisition --real-cached-root tests\fixtures\replay_candidates\pm_crypto_updown\real_cached_sample --real-cached-root data\external\manual_captures\pm_crypto_updown\pm_crypto_updown_manual_041
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="sequence41-smoke" (
  python -m quant_os.cli data pm-crypto-updown-capture-plan --manual-network-ok --run-id pm_crypto_updown_manual_041
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli data pm-crypto-updown-real-cached-import --real-cached-root tests\fixtures\replay_candidates\pm_crypto_updown\real_cached_sample --real-cached-root data\external\manual_captures\pm_crypto_updown\pm_crypto_updown_manual_041
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli research pm-crypto-updown-window-acquisition --real-cached-root tests\fixtures\replay_candidates\pm_crypto_updown\real_cached_sample --real-cached-root data\external\manual_captures\pm_crypto_updown\pm_crypto_updown_manual_041
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli research pm-crypto-updown-threshold-progress --sequence41 --real-cached-root tests\fixtures\replay_candidates\pm_crypto_updown\real_cached_sample --real-cached-root data\external\manual_captures\pm_crypto_updown\pm_crypto_updown_manual_041
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli research pm-crypto-updown-real-cached-replay-eval --sequence41 --real-cached-root tests\fixtures\replay_candidates\pm_crypto_updown\real_cached_sample --real-cached-root data\external\manual_captures\pm_crypto_updown\pm_crypto_updown_manual_041
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli readiness expanded-shadow-replay-readiness --real-cached-root tests\fixtures\replay_candidates\pm_crypto_updown\real_cached_sample --real-cached-root data\external\manual_captures\pm_crypto_updown\pm_crypto_updown_manual_041
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m pytest tests/test_sequence41_real_cached_window_acquisition.py
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="sequence42-smoke" (
  python -m pytest tests/test_sequence42_real_cached_window_import.py
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="pm-crypto-updown-fill-policy-smoke" (
  python -m quant_os.cli research pm-crypto-updown-fill-blockers --real-cached-root tests\fixtures\replay_candidates\pm_crypto_updown\real_cached_sample
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli research pm-crypto-updown-shadow-policy --real-cached-root tests\fixtures\replay_candidates\pm_crypto_updown\real_cached_sample
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli research pm-crypto-updown-policy-replay-eval --real-cached-root tests\fixtures\replay_candidates\pm_crypto_updown\real_cached_sample
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="bounded-shadow-rehearsal-readiness-smoke" (
  python -m quant_os.cli readiness bounded-shadow-rehearsal --real-cached-root tests\fixtures\replay_candidates\pm_crypto_updown\real_cached_sample
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="sequence43-smoke" (
  call "%~f0" pm-crypto-updown-fill-policy-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  call "%~f0" bounded-shadow-rehearsal-readiness-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m pytest tests/test_sequence43_fill_realism_shadow_policy.py
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="allowed-intent-diagnostics-smoke" (
  python -m quant_os.cli research pm-crypto-updown-allowed-intent-diagnostics --real-cached-root tests\fixtures\replay_candidates\pm_crypto_updown\real_cached_sample
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli research pm-crypto-updown-discriminators --real-cached-root tests\fixtures\replay_candidates\pm_crypto_updown\real_cached_sample
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli research pm-crypto-updown-baseline-placebo-attribution --real-cached-root tests\fixtures\replay_candidates\pm_crypto_updown\real_cached_sample
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="candidate-decision-smoke" (
  python -m quant_os.cli readiness pm-crypto-updown-candidate-decision --real-cached-root tests\fixtures\replay_candidates\pm_crypto_updown\real_cached_sample
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="sequence44-smoke" (
  call "%~f0" allowed-intent-diagnostics-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  call "%~f0" candidate-decision-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m pytest tests/test_sequence44_allowed_intent_signal_discrimination.py
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="allowed-intent-acquisition-smoke" (
  python -m quant_os.cli data pm-crypto-updown-capture-plan --manual-network-ok --run-id pm_crypto_updown_manual_045
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli research pm-crypto-updown-allowed-intent-acquisition --real-cached-root tests\fixtures\replay_candidates\pm_crypto_updown\real_cached_sample
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli research pm-crypto-updown-allowed-intent-progress --real-cached-root tests\fixtures\replay_candidates\pm_crypto_updown\real_cached_sample
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="allowed-intent-decision-smoke" (
  python -m quant_os.cli research pm-crypto-updown-discriminator-update --real-cached-root tests\fixtures\replay_candidates\pm_crypto_updown\real_cached_sample
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli research pm-crypto-updown-overfit-guard-update --real-cached-root tests\fixtures\replay_candidates\pm_crypto_updown\real_cached_sample
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli research pm-crypto-updown-baseline-placebo-update --real-cached-root tests\fixtures\replay_candidates\pm_crypto_updown\real_cached_sample
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli readiness pm-crypto-updown-allowed-intent-decision --real-cached-root tests\fixtures\replay_candidates\pm_crypto_updown\real_cached_sample
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli proving pm-crypto-updown-bounded-shadow-rehearsal-spec --real-cached-root tests\fixtures\replay_candidates\pm_crypto_updown\real_cached_sample
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli research pm-crypto-updown-phase45-reference-notes
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="sequence45-smoke" (
  call "%~f0" allowed-intent-acquisition-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  call "%~f0" allowed-intent-decision-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m pytest tests/test_sequence45_allowed_intent_evidence_expansion.py
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="sequence46-smoke" (
  python -m quant_os.cli data pm-crypto-updown-capture-plan --manual-network-ok --run-id pm_crypto_updown_manual_046
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli data pm-crypto-updown-real-cached-import --real-cached-root tests\fixtures\replay_candidates\pm_crypto_updown\real_cached_sample --real-cached-root data\external\manual_captures\pm_crypto_updown\pm_crypto_updown_manual_046
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli research pm-crypto-updown-phase46-capture-pass --run-id pm_crypto_updown_manual_046 --real-cached-root tests\fixtures\replay_candidates\pm_crypto_updown\real_cached_sample
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli readiness pm-crypto-updown-phase46-candidate-path --run-id pm_crypto_updown_manual_046 --real-cached-root tests\fixtures\replay_candidates\pm_crypto_updown\real_cached_sample
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m pytest tests/test_sequence46_allowed_intent_capture_path.py
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="sequence47-smoke" (
  python -m quant_os.cli research pm-lp-refresh-lag-candidate-pack
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli research pm-lp-refresh-lag-replay-schema
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli research pm-lp-refresh-lag-source-policy
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli readiness pm-lp-refresh-lag-candidate-readiness --fixture-path tests\fixtures\replay_candidates\pm_lp_refresh_lag\refresh_lag_windows.json
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m pytest tests/test_sequence47_pm_lp_refresh_lag_candidate_pack.py
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="sequence48-smoke" (
  python -m quant_os.cli research pm-lp-refresh-lag-source-feasibility
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli data pm-lp-refresh-lag-capture-plan
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli readiness pm-lp-refresh-lag-source-readiness --fixture-path tests\fixtures\replay_candidates\pm_lp_refresh_lag\public_source_sample\blocked_missing_public_fill_attribution.json
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m pytest tests/test_sequence48_lp_refresh_lag_public_sources.py
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="profit-lane-tournament-smoke" (
  python -m quant_os.cli research profit-lane-tournament
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli research selected-profit-lane
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="paper-proving-smoke" (
  python -m quant_os.cli proving paper-proving-report
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli proving profit-claim-guard
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="sequence49-smoke" (
  call "%~f0" profit-lane-tournament-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  call "%~f0" paper-proving-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m pytest tests/test_sequence49_profit_lane_tournament_paper_proving.py
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="weather-market-candidate-smoke" (
  python -m quant_os.cli research weather-market-candidate
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli research weather-source-policy
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli research weather-market-replay-schema
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="weather-market-capture-plan-smoke" (
  python -m quant_os.cli data weather-market-capture-plan
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="weather-market-paper-proving-smoke" (
  python -m quant_os.cli proving weather-market-paper-proving
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli readiness weather-market-data-readiness
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="sequence50-smoke" (
  call "%~f0" weather-market-candidate-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  call "%~f0" weather-market-capture-plan-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  call "%~f0" weather-market-paper-proving-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m pytest tests/test_sequence50_weather_market_data_paper_proving.py
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="sequence51-smoke" (
  python -m quant_os.cli data weather-market-discover
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli data weather-source-match
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli data weather-market-public-capture
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli research weather-market-dataset
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli proving weather-market-real-paper-proving
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli readiness weather-market-paper-profit-readiness
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m pytest tests/test_sequence51_real_weather_market_capture_paper_proving.py
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="sequence52-smoke" (
  python -m quant_os.cli data weather-resolved-market-discovery
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli data weather-resolution-labels
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli data weather-market-batch-capture
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli research weather-resolved-dataset
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli proving weather-batch-paper-proving
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli readiness weather-batch-paper-readiness
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli data weather-pending-resolution-monitor
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m pytest tests/test_sequence52_weather_resolved_batch_paper_proving.py
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="relentless-profit-campaign-smoke" (
  python -m quant_os.cli research relentless-profit-campaign
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli proving relentless-profit-campaign-run
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli proving relentless-profit-campaign-state
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli autonomy forward-capture-plan
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli readiness profit-candidate-autonomy-path
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="sequence53-smoke" (
  call "%~f0" relentless-profit-campaign-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m pytest tests/test_sequence53_relentless_profit_campaign.py
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="crypto-spot-public-paper-proving-smoke" (
  python -m quant_os.cli proving crypto-spot-public-paper-proving
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="sequence54-smoke" (
  call "%~f0" crypto-spot-public-paper-proving-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m pytest tests/test_sequence54_crypto_spot_public_paper_proving.py
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="canary-readiness-smoke" (
  python -m quant_os.cli readiness paper-candidate-audit
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli readiness weather-lineage-audit
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli proving weather-replay-recompute
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli proving weather-robustness
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli proving weather-cost-fill-stress
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli proving weather-bounded-shadow-rehearsal
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli execution weather-dry-run-parity
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli risk weather-tiny-canary-risk
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli risk weather-canary-kill-switch
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli execution weather-canary-reconciliation
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli readiness weather-manual-canary-packet
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli readiness tiny-canary-readiness
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="sequence55-smoke" (
  call "%~f0" canary-readiness-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m pytest tests/test_sequence55_tiny_canary_readiness.py
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="profit-candidate-artifacts-smoke" (
  python -m quant_os.cli proving regenerate-profit-candidate-artifacts
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="first-dollar-preflight-smoke" (
  call "%~f0" profit-candidate-artifacts-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli readiness first-dollar-provenance-audit
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli readiness first-dollar-provenance-repair
  if errorlevel 1 exit /b !ERRORLEVEL!
  call "%~f0" canary-readiness-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli readiness first-dollar-security-scan
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli readiness current-market-eligibility
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli readiness first-dollar-order-preview
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli readiness first-dollar-human-review
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli readiness first-dollar-preflight
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="sequence56-smoke" (
  call "%~f0" first-dollar-preflight-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m pytest tests/test_sequence56_first_dollar_preflight.py
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="current-market-preflight-smoke" (
  python -m quant_os.cli data current-weather-market-discovery
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli data current-weather-forecast-match
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli readiness current-market-eligibility
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli readiness first-dollar-order-preview
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli readiness first-dollar-human-review
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli readiness first-dollar-preflight
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli autonomy current-market-watch-plan
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="sequence57-smoke" (
  call "%~f0" sequence56-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  call "%~f0" current-market-preflight-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m pytest tests/test_sequence57_current_market_preflight.py
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="live-market-paper-rehearsal-smoke" (
  python -m quant_os.cli autonomy live-market-paper-observer
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli autonomy live-market-paper-intents
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli autonomy live-market-fake-fill
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli autonomy live-market-paper-ledger
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli autonomy live-market-paper-reconciliation
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli readiness live-market-paper-rehearsal
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli autonomy live-market-paper-rehearsal-schedule
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="sequence58-smoke" (
  call "%~f0" live-market-paper-rehearsal-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m pytest tests/test_sequence58_live_market_paper_rehearsal.py
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="autonomous-live-fire-drill-smoke" (
  python -m quant_os.cli autonomy autonomous-market-watcher
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli autonomy autonomous-decision-engine
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli autonomy autonomous-no-transmit-intent
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli execution mock-order-lifecycle
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli execution autonomous-fake-execution
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli risk autonomous-fire-drill-risk
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli execution autonomous-fake-reconciliation
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli validation autonomous-fire-drill-scenarios
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli readiness autonomous-live-fire-drill
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli readiness human-live-boundary-packet
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m pytest tests/test_sequence59_autonomous_live_fire_drill.py
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="sequence59-smoke" (
  call "%~f0" sequence58-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  call "%~f0" autonomous-live-fire-drill-smoke
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="live-market-sim-profitability-smoke" (
  python -m quant_os.cli autonomy live-market-profit-observer
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli autonomy live-market-sim-intents
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli autonomy live-market-sim-fill
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli autonomy live-market-sim-ledger
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli autonomy live-market-sim-outcomes
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli autonomy live-market-sim-pnl
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli proving live-market-sim-comparison
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli autonomy live-market-sim-reconciliation
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli readiness live-market-sim-profitability
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli autonomy live-market-sim-profitability-schedule
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="sequence60-smoke" (
  call "%~f0" sequence59-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  call "%~f0" live-market-sim-profitability-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m pytest tests/test_sequence60_live_market_sim_profitability.py
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="venue-capture" (
  python -m quant_os.cli data venue-capture --venue kraken
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="sequence18-smoke" (
  call "%~f0" venue-capture
  if errorlevel 1 exit /b !ERRORLEVEL!
  call "%~f0" venue-calibration-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  call "%~f0" calibrated-edge-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="sequence3a-smoke" (
  call "%~f0" venue-calibration-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  call "%~f0" calibrated-edge-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m pytest tests/test_sequence3_venue_calibration.py tests/test_sequence3_calibrated_edge.py
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="sequence2-smoke" (
  call "%~f0" replay-realism-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  call "%~f0" walk-forward-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  call "%~f0" dry-run-proving-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli validation run-all
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m quant_os.cli readiness report
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m pytest tests/test_sequence2_replay_realism.py tests/test_sequence2_walk_forward.py tests/test_sequence2_dry_run_proving.py tests/test_sequence2_validation_readiness.py
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="sequence1-smoke" (
  call "%~f0" crypto-research
  if errorlevel 1 exit /b !ERRORLEVEL!
  call "%~f0" replay-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  call "%~f0" calibration-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  call "%~f0" validation-smoke
  if errorlevel 1 exit /b !ERRORLEVEL!
  python -m pytest tests/test_sequence1_data_spine.py tests/test_sequence1_crypto_research.py tests/test_sequence1_replay.py tests/test_sequence1_calibration.py tests/test_sequence1_validation_engine.py
  exit /b !ERRORLEVEL!
)
if "%TARGET%"=="clean" (
  python -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in ['data/demo','data/events','data/read_models','.pytest_cache','.ruff_cache','htmlcov']]; [path.unlink() for path in pathlib.Path('reports').glob('*') if path.name != '.gitkeep']"
  exit /b !ERRORLEVEL!
)

echo Unknown target: %TARGET%
exit /b 2
