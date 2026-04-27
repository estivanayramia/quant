# Risk Policy

Default risk limits live in `configs/risk_limits.yaml`.

The risk firewall rejects candidate orders for live-trading attempts, active kill switch, strategy quarantine, max open positions, max trades per day, max order notional, max position notional, leverage, shorting, options, futures, spread/slippage caps, cooldown placeholders, and no-trade flags.

The Freqtrade dry-run lane is guarded separately by a fail-closed safety validator. It rejects live flags, exchange credentials, futures, margin, shorts, leverage above one, Telegram/API server enablement, and any generated config outside the expected repo-local Freqtrade config directory.

Every approval or rejection produces a risk decision event with reasons and a limits snapshot. The kill switch blocks all new orders. Strategy quarantine blocks all new orders from the quarantined strategy.

Capital unlock is staged and conservative: shadow stability, paper stability, reconciliation tests, slippage tests, kill-switch drills, tiny notional limits, and explicit human approval are required before any future scaling.
