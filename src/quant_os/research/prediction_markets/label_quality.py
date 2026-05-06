from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from quant_os.data.prediction_markets.activity_capture import build_activity_dataset_from_capture

REPORT_ROOT = Path("reports/sequence26/label_quality")
LABEL_QUALITY_SAFETY = {
    "execution_authority": "NONE",
    "wallet_signing_enabled": False,
    "live_trading_enabled": False,
    "copy_trading_enabled": False,
    "real_orders_enabled": False,
}
MIN_CONFIDENT_LABELS_FOR_OOS = 20


def evaluate_label_quality(dataset: dict[str, Any]) -> dict[str, Any]:
    market_quality = [_market_label_quality(market) for market in dataset["markets"]]
    counts = Counter(item["label_quality_status"] for item in market_quality)
    missing_reference_count = sum(
        1 for item in market_quality if "MISSING_REFERENCE_CONTEXT" in item["exclusion_reasons"]
    )
    incomplete_activity_count = sum(
        1 for item in market_quality if "INCOMPLETE_ACTIVITY_HISTORY" in item["exclusion_reasons"]
    )
    summary = {
        "confidently_resolved_count": counts["CONFIDENTLY_RESOLVED"],
        "weakly_resolved_count": counts["WEAKLY_RESOLVED"],
        "unresolved_count": counts["UNRESOLVED"],
        "ambiguous_count": counts["AMBIGUOUS"],
        "disputed_count": counts["DISPUTED"],
        "excluded_count": sum(
            1 for item in market_quality if not item["included_in_lane_activity_research"]
        ),
        "usable_resolved_label_count": counts["CONFIDENTLY_RESOLVED"] + counts["WEAKLY_RESOLVED"],
        "missing_reference_context_count": missing_reference_count,
        "incomplete_activity_history_count": incomplete_activity_count,
    }
    warnings = _warnings(summary)
    status = (
        "LABELS_USABLE_FOR_OOS_RESEARCH"
        if summary["confidently_resolved_count"] >= MIN_CONFIDENT_LABELS_FOR_OOS
        and summary["usable_resolved_label_count"] >= MIN_CONFIDENT_LABELS_FOR_OOS
        else "INSUFFICIENT_LABEL_QUALITY"
    )
    return {
        "sequence": "26",
        "source": dataset["source"],
        "source_mode": dataset["source_mode"],
        "lane_id": dataset["lane_id"],
        "dataset_id": dataset["dataset_id"],
        "dataset_hash": dataset["dataset_hash"],
        "label_quality_status": status,
        "summary": summary,
        "warnings": warnings,
        "exclusion_reasons": _exclusion_reasons(market_quality),
        "market_label_quality": market_quality,
        "observed_facts": [
            "Label quality is computed from saved resolution fields and reference-context hooks.",
            "Weak labels are retained as diagnostics and clearly separated from confident labels.",
        ],
        "inferred_patterns": [
            "Resolved-history expansion only helps if labels remain trustworthy under OOS evaluation.",
        ],
        "unknowns": [
            "Reference context remains cached/offline and may need later external confirmation.",
        ],
        "ready_for_narrow_replay_design": False,
        **LABEL_QUALITY_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def write_label_quality_report(
    *,
    fixture_path: str | Path,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    dataset = build_activity_dataset_from_capture(fixture_path)
    payload = evaluate_label_quality(dataset)
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _market_label_quality(market: dict[str, Any]) -> dict[str, Any]:
    resolution = market["resolution"]
    status = resolution["status"]
    reasons = []
    if not market.get("reference_context"):
        reasons.append("MISSING_REFERENCE_CONTEXT")
    if market["included_in_lane_activity_research"] and not market["activity"]:
        reasons.append("INCOMPLETE_ACTIVITY_HISTORY")

    if not market["included_in_lane_activity_research"]:
        label_status = "AMBIGUOUS" if status == "AMBIGUOUS" else "EXCLUDED"
        if market["exclusion_reason"]:
            reasons.append(market["exclusion_reason"])
    elif status == "RESOLVED" and resolution.get("winning_outcome") in {"YES", "NO"}:
        label_status = (
            "CONFIDENTLY_RESOLVED"
            if resolution.get("confidence") in {"HIGH", "MEDIUM"}
            and resolution.get("truth_source")
            and market.get("reference_context")
            else "WEAKLY_RESOLVED"
        )
    elif status == "UNRESOLVED":
        label_status = "UNRESOLVED"
    elif status == "AMBIGUOUS":
        label_status = "AMBIGUOUS"
    elif status == "DISPUTED":
        label_status = "DISPUTED"
    else:
        label_status = "EXCLUDED"
        reasons.append(status)

    return {
        "market_id": market["market_id"],
        "condition_id": market["condition_id"],
        "slug": market["slug"],
        "lane_id": market["lane_id"],
        "resolution_status": status,
        "winning_outcome": resolution.get("winning_outcome"),
        "label_confidence": resolution.get("confidence"),
        "truth_source": resolution.get("truth_source"),
        "label_quality_status": label_status,
        "included_in_lane_activity_research": market["included_in_lane_activity_research"],
        "exclusion_reasons": sorted(set(reasons)),
    }


def _warnings(summary: dict[str, int]) -> list[str]:
    warnings = []
    if summary["confidently_resolved_count"] < MIN_CONFIDENT_LABELS_FOR_OOS:
        warnings.append("CONFIDENT_LABEL_COUNT_BELOW_REPLAY_THRESHOLD")
    if summary["weakly_resolved_count"] > 0:
        warnings.append("WEAK_LABEL_CONFIDENCE_PRESENT")
    if summary["unresolved_count"] > 0:
        warnings.append("UNRESOLVED_MARKETS_RETAINED_UNSCORED")
    if summary["ambiguous_count"] > 0:
        warnings.append("AMBIGUOUS_MARKETS_EXCLUDED")
    return warnings


def _exclusion_reasons(market_quality: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(
        reason
        for item in market_quality
        if item["label_quality_status"] in {"AMBIGUOUS", "DISPUTED", "EXCLUDED"}
        for reason in item["exclusion_reasons"]
        if reason not in {"MISSING_REFERENCE_CONTEXT"}
    )
    return dict(sorted(counts.items()))


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_label_quality.json"
    md_path = root / "latest_label_quality.md"
    json_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    lines = [
        "# Sequence 26 Label Quality",
        "",
        "Research-only label-quality report. No execution authority.",
        "",
        f"Lane: {payload['lane_id']}",
        f"Label quality: {payload['label_quality_status']}",
        f"Usable resolved labels: {payload['summary']['usable_resolved_label_count']}",
        f"Live promotion: {payload['live_promotion_status']}",
        "",
        "## Observed facts",
    ]
    lines.extend(f"- {item}" for item in payload["observed_facts"])
    lines.extend(["", "## Inferred patterns"])
    lines.extend(f"- {item}" for item in payload["inferred_patterns"])
    lines.extend(["", "## Unknowns"])
    lines.extend(f"- {item}" for item in payload["unknowns"])
    lines.extend(["", "## Warnings"])
    lines.extend(f"- {item}" for item in (payload["warnings"] or ["None"]))
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
