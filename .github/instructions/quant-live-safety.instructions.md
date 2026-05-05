---
applyTo: "src/quant_os/security/**/*.py,src/quant_os/canary/**/*.py,src/quant_os/live_canary/**/*.py,configs/live*.yaml,configs/canary*.yaml,configs/freqtrade.yaml,configs/integrations.yaml,docs/*live*.md,docs/*canary*.md,tests/test_live*.py,tests/test_canary*.py,tests/test_freqtrade_safety_guard.py"
---

# Quant Live Safety Instructions

- Live and canary code must be fake/default-off unless a later explicit human-approved phase says otherwise.
- Do not weaken guards for credentials, external settings paths, spot-only mode, stoploss support, symbol allowlists, notional caps, reconciliation, arming, approval, incident readiness, or kill switch.
- CI and fresh checkouts must stay fake-only and blocked-real.
- Optional exchange dependencies must remain guarded and must not become required for tests.
- No config default may enable live trading, real keys, withdrawals, leverage, futures, margin, shorts, command-capable Telegram, or unsafe API server control.
- Any live/canary change requires explicit validation of guard behavior.

Relevant checks:

- `python -m quant_os.cli guard-live`
- `python -m quant_os.cli freqtrade validate`
- `python -m pytest tests/test_live_trading_guard.py tests/test_canary_live_block.py -q`
- `.\\make.cmd smoke`
