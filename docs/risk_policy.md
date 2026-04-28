# Risk Policy

Default risk limits live in `configs/risk_limits.yaml`.

The risk firewall rejects candidate orders for live-trading attempts, active kill switch, strategy quarantine, max open positions, max trades per day, max order notional, max position notional, leverage, shorting, options, futures, spread/slippage caps, cooldown placeholders, and no-trade flags.

The Freqtrade dry-run lane is guarded separately by a fail-closed safety validator. It rejects live flags, exchange credentials, futures, margin, shorts, leverage above one, Telegram/API server enablement, and any generated config outside the expected repo-local Freqtrade config directory.

Phase 4 reconciliation compares generated Freqtrade artifacts with QuantOS risk limits and marks unsafe drift as `FAIL`. Warnings such as Docker unavailable or no logs are non-live operational warnings, not permission to trade.

Phase 5 dry-run divergence checks fail closed on unsafe Freqtrade artifacts: `dry_run` false, live flags, keys, futures, margin, leverage, shorting, missing config or strategy, strategy hash mismatch, or live-mode danger words.

Phase 6 trade artifact parsers also fail closed on live-mode evidence, credentials, futures, margin, leverage, shorting, or `dry_run: false`. Unknown trade schemas are preserved as raw payloads and do not become source of truth.

Every approval or rejection produces a risk decision event with reasons and a limits snapshot. The kill switch blocks all new orders. Strategy quarantine blocks all new orders from the quarantined strategy.

Capital unlock is staged and conservative: shadow stability, paper stability, reconciliation tests, slippage tests, kill-switch drills, tiny notional limits, and explicit human approval are required before any future scaling.
