from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.replay.prediction_market_replay_inputs import write_replay_input_summary

REPORT_ROOT = Path("reports/sequence28/replay_input_readiness")
READINESS_SAFETY = {
    "execution_authority": "NONE",
    "wallet_signing_enabled": False,
    "live_trading_enabled": False,
    "copy_trading_enabled": False,
    "real_orders_enabled": False,
    "prediction_market_execution_authority_added": False,
}


def write_replay_input_readiness_report(
    *,
    output_root: str | Path = ".",
    polymarket_snapshot_path: str | Path | None = None,
    pmxt_manifest_path: str | Path | None = None,
    reference_datasets_manifest_path: str | Path | None = None,
) -> dict[str, Any]:
    summary = write_replay_input_summary(
        output_root=output_root,
        polymarket_snapshot_path=polymarket_snapshot_path,
        pmxt_manifest_path=pmxt_manifest_path,
        reference_datasets_manifest_path=reference_datasets_manifest_path,
    )
    payload = evaluate_replay_input_readiness(summary)
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def evaluate_replay_input_readiness(summary: dict[str, Any]) -> dict[str, Any]:
    blockers = _readiness_blockers(summary)
    status = _status_from_blockers(summary, blockers)
    ready = status == "READY_FOR_NARROW_REPLAY_DESIGN"
    return {
        "sequence": "28",
        "replay_input_readiness_status": status,
        "ready_for_narrow_replay_design": ready,
        "not_live_readiness": True,
        "not_profitability_evidence": True,
        "blockers": blockers,
        "summary": {
            "event_count": summary["event_count"],
            "event_counts": summary["event_counts"],
            "quality_flag_counts": summary["quality_flag_counts"],
            "market_count": summary["market_count"],
            "token_count": summary["token_count"],
        },
        "observed_facts": [
            "Replay inputs can be normalized from fixture-safe public snapshots and manifests.",
            "The normalized events include market state, orderbook snapshots, and trades where present.",
        ],
        "inferred_patterns": [
            "The repo can now inspect replay input shape before designing a replay engine for this lane.",
        ],
        "unknowns": [
            "Queue position, fills, fees, latency, and adverse selection remain unresolved.",
            "Manifest availability does not prove enough historical depth for profitable replay.",
        ],
        **READINESS_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def _readiness_blockers(summary: dict[str, Any]) -> list[str]:
    blockers = []
    event_counts = summary["event_counts"]
    if summary["event_count"] == 0:
        blockers.append("REPLAY_INPUTS_TOO_THIN")
    if event_counts.get("market_state", 0) == 0:
        blockers.append("MISSING_MARKET_STATE")
    if event_counts.get("orderbook_snapshot", 0) == 0:
        blockers.append("MISSING_ORDERBOOK_SNAPSHOTS")
    if event_counts.get("trade", 0) == 0:
        blockers.append("MISSING_TRADES")
    if event_counts.get("orderbook_snapshot", 0) < 10:
        blockers.append("ORDERBOOK_HISTORY_TOO_THIN")
    if event_counts.get("trade", 0) < 10:
        blockers.append("TRADE_HISTORY_TOO_THIN")
    if summary["quality_flag_counts"]:
        blockers.append("QUALITY_FLAGS_PRESENT")
    blockers.append("REPLAY_LIMITATIONS_UNMODELED")
    return _dedupe(blockers)


def _status_from_blockers(summary: dict[str, Any], blockers: list[str]) -> str:
    if "REPLAY_INPUTS_TOO_THIN" in blockers:
        return "REPLAY_INPUTS_TOO_THIN"
    minimum_shape_present = (
        summary["event_counts"].get("market_state", 0) > 0
        and summary["event_counts"].get("orderbook_snapshot", 0) > 0
        and summary["event_counts"].get("trade", 0) > 0
    )
    if minimum_shape_present:
        return "REPLAY_INPUTS_PARTIAL"
    return "REPLAY_INPUTS_TOO_THIN"


def _dedupe(items: list[str]) -> list[str]:
    seen = set()
    deduped = []
    for item in items:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_replay_input_readiness.json"
    md_path = root / "latest_replay_input_readiness.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 28 Replay Input Readiness",
        "",
        "Research-only replay input readiness gate. No execution authority.",
        "",
        f"Status: {payload['replay_input_readiness_status']}",
        f"Ready for narrow replay design: {payload['ready_for_narrow_replay_design']}",
        f"Live promotion: {payload['live_promotion_status']}",
        "",
        "## Blockers",
    ]
    lines.extend(f"- {item}" for item in payload["blockers"])
    lines.extend(["", "## Unknowns"])
    lines.extend(f"- {item}" for item in payload["unknowns"])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
