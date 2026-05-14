from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.research.replay_candidates.pm_crypto_updown_schema import CANDIDATE_ID
from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY

REPORT_ROOT = Path("reports/sequence37/shadow_bridge")


def build_pm_crypto_updown_shadow_bridge(
    *,
    evaluation_report: dict[str, Any],
    readiness_report: dict[str, Any],
) -> dict[str, Any]:
    signal_rows = [
        decision
        for decision in evaluation_report["signal_report"]["row_decisions"]
        if decision["side"] == "BUY"
    ]
    rows_by_id = {row["clob_snapshot_id"]: row for row in evaluation_report["primary_rows"]}
    cost_by_id = {
        row["row_id"]: row for row in evaluation_report["cost_adjusted_metrics"]["rows"]
    }
    fill_by_id = {
        row["row_id"]: row for row in evaluation_report["fill_adjusted_metrics"]["rows"]
    }
    intents = [
        _intent(decision, rows_by_id[decision["row_id"]], cost_by_id, fill_by_id, readiness_report)
        for decision in signal_rows
        if decision["row_id"] in rows_by_id
    ]
    return {
        "schema_version": "pm_crypto_updown_shadow_bridge_v1",
        "sequence": "37",
        "candidate_id": CANDIDATE_ID,
        "offline_shadow_intents_only": True,
        "shadow_intent_count": len(intents),
        "blocked_intent_count": sum(1 for item in intents if item["blocked"]),
        "shadow_intents": intents,
        "readiness_status": readiness_report["readiness_status"],
        **SOCIAL_INTAKE_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def write_pm_crypto_updown_shadow_bridge_report(
    *,
    evaluation_report: dict[str, Any],
    readiness_report: dict[str, Any],
    output_root: str | Path = ".",
) -> dict[str, Any]:
    payload = build_pm_crypto_updown_shadow_bridge(
        evaluation_report=evaluation_report,
        readiness_report=readiness_report,
    )
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _intent(
    decision: dict[str, Any],
    row: dict[str, Any],
    cost_by_id: dict[str, dict[str, Any]],
    fill_by_id: dict[str, dict[str, Any]],
    readiness_report: dict[str, Any],
) -> dict[str, Any]:
    cost = cost_by_id[decision["row_id"]]
    fill = fill_by_id[decision["row_id"]]
    blockers = []
    if readiness_report["readiness_status"] != "READY_FOR_EXPANDED_SHADOW_REPLAY":
        blockers.append(readiness_report["readiness_status"])
    blockers.extend(cost.get("cost_blockers", []))
    blockers.extend(fill.get("fill_blockers", []))
    limit_price = min(float(row["market_ask"]), float(row["market_mid"]) + 0.01)
    return {
        "row_id": row["clob_snapshot_id"],
        "market_id": row["market_id"],
        "token_id": row["token_id"],
        "side": decision["side"],
        "hypothetical_price_discipline": {
            "type": "offline_limit_only",
            "max_price": round(limit_price, 4),
            "reference_mid": row["market_mid"],
            "reference_ask": row["market_ask"],
        },
        "blocked": bool(blockers),
        "blocked_status": "BLOCKED" if blockers else "NOT_BLOCKED_FOR_OFFLINE_SHADOW_ONLY",
        "signal_reason": decision["rationale"],
        "cost_fill_blocker": sorted(set(blockers)) or ["None"],
        "risk_caveat": readiness_report["readiness_status"],
        "real_order_submitted": False,
        "execution_authority": "NONE",
    }


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_pm_crypto_updown_shadow_bridge.json"
    md_path = root / "latest_pm_crypto_updown_shadow_bridge.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 37 PM Crypto UP/DOWN Shadow Bridge",
        "",
        "Offline shadow-intent candidates from replay rows only.",
        "",
        f"Readiness status: {payload['readiness_status']}",
        f"Shadow intents: {payload['shadow_intent_count']}",
        f"Blocked intents: {payload['blocked_intent_count']}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
        "",
        "## Intents",
    ]
    lines.extend(
        "- {row_id}: {side} {status} caveat={caveat}".format(
            row_id=item["row_id"],
            side=item["side"],
            status=item["blocked_status"],
            caveat=item["risk_caveat"],
        )
        for item in payload["shadow_intents"]
    )
    if not payload["shadow_intents"]:
        lines.append("- None")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
