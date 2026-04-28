# Evidence Policy

QuantOS evidence is deliberately conservative.

Phase 8 scores evidence using:

- data quality status;
- symbol coverage;
- timeframe coverage;
- regime coverage;
- trade count sufficiency;
- walk-forward split coverage;
- ablation availability;
- placebo margin;
- slippage stress;
- overfitting penalties.

Statuses can be `INSUFFICIENT`, `RESEARCH_WEAK`, `RESEARCH_ACCEPTABLE`, `SHADOW_CANDIDATE`, or `DRY_RUN_CANDIDATE`.

Live remains blocked. Evidence scoring always reports `LIVE_BLOCKED` for live promotion because no live canary policy, exchange permission verification, multi-week dry-run proof, or human approval gate exists in this phase.

Phase 9 adds historical local-cache evidence. Historical imports must include manifests, hashes, quality reports, split/leakage checks, and license notes. Passing historical evidence is still research evidence only; it is not live readiness.
