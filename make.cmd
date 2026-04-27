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
