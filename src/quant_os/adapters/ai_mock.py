from __future__ import annotations

import json


class MockAIProvider:
    def critique_strategy(self, strategy_id: str, metrics: dict[str, object]) -> str:
        payload = json.dumps(metrics, sort_keys=True)
        return f"MOCK_CRITIQUE[{strategy_id}]: deterministic review of metrics {payload}"

    def daily_report_summary(self, context: dict[str, object]) -> str:
        keys = ",".join(sorted(context.keys()))
        return f"MOCK_DAILY_SUMMARY: simulation-only summary with context keys {keys}"

    def risk_notes(self, risk_context: dict[str, object]) -> str:
        keys = ",".join(sorted(risk_context.keys()))
        return f"MOCK_RISK_NOTES: deterministic risk note for keys {keys}"
