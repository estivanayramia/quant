# Future Integrations

- Freqtrade is now scaffolded for crypto dry-run containers only; eventual tiny live canary remains a future gated phase.
- Freqtrade operational runner can be used for dry-run inspection and reconciliation only; live canary remains disabled and future-gated.
- Freqtrade trade artifact ingestion can read local dry-run artifacts for evidence, but it does not unlock live trading.
- Strategy research upgrades can feed future dry-run candidate selection, but only after placebo, ablation, walk-forward, regime, overfitting, and human-review gates.
- Dataset evidence hardening can improve offline research confidence, but synthetic datasets remain research plumbing and do not unlock live trading.
- Historical data ingestion can improve research evidence through local/cache-first imports, but public provider downloads remain disabled by default and cannot unlock live trading.
- Lumibot + Alpaca Paper later for equities paper trading.
- QuantConnect/LEAN later as an external validation lane.
- NautilusTrader later if a professional event-driven stack becomes necessary.
- Telegram/Discord alerts later for human visibility only, never order authority.
- AI provider mesh later through LiteLLM or equivalent, research/reporting only.
- Prediction-market, GDELT, FRED, and SEC EDGAR adapters later as research and event features only.

None of these integrations are implemented in Milestone 1.
