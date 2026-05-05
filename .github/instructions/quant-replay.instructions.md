---
applyTo: "src/quant_os/replay/**/*.py,src/quant_os/research/backtest.py,src/quant_os/research/slippage.py,tests/test_sequence1_replay.py,tests/test_backtest_metrics.py,tests/test_slippage_stress.py"
---

# Quant Replay Instructions

- Replay exists to kill fake edges early. Prefer conservative assumptions over optimistic fills.
- Fees, slippage, latency, partial fills, passive/aggressive behavior, timeouts, rejections, inventory, and equity curves must remain visible in outputs.
- Do not let replay reuse live adapters or broker authority.
- Metrics should report after-cost expectancy, drawdown, trade count, turnover, time in market, capacity approximation, and sensitivity where relevant.
- If a replay result looks profitable, look for stale data, leakage, cost omission, placebo weakness, or capacity fantasy before trusting it.

Relevant checks:

- `python -m pytest tests/test_sequence1_replay.py -q`
- `.\\make.cmd replay-smoke`
