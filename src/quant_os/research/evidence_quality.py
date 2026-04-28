from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def latest_evidence_adjustment(
    path: str | Path = "reports/evidence/latest_evidence_score.json",
) -> dict[str, Any]:
    report_path = Path(path)
    if not report_path.exists():
        return {
            "evidence_status": "UNAVAILABLE",
            "evidence_penalty": 0.10,
            "live_promotion_status": "LIVE_BLOCKED",
        }
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    status = payload.get("final_evidence_status", "INSUFFICIENT")
    penalties = {
        "DRY_RUN_CANDIDATE": 0.0,
        "SHADOW_CANDIDATE": 0.03,
        "RESEARCH_ACCEPTABLE": 0.06,
        "RESEARCH_WEAK": 0.12,
        "INSUFFICIENT": 0.20,
    }
    return {
        "evidence_status": status,
        "evidence_penalty": penalties.get(status, 0.15),
        "live_promotion_status": payload.get("live_promotion_status", "LIVE_BLOCKED"),
    }
