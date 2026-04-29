from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from quant_os.autonomy.state import AutonomousRunState
from quant_os.core.ids import deterministic_id

PROVING_ROOT = Path("reports/proving")
PROVING_HISTORY_ROOT = PROVING_ROOT / "history"


class ProvingRunRecord(BaseModel):
    run_id: str
    timestamp: str
    run_status: str
    autonomous_status: str
    dryrun_monitoring_status: str = "UNAVAILABLE"
    historical_evidence_status: str = "UNAVAILABLE"
    strategy_research_status: str = "UNAVAILABLE"
    dataset_quality_status: str = "UNAVAILABLE"
    leakage_status: str = "UNAVAILABLE"
    trade_reconciliation_status: str = "UNAVAILABLE"
    proving_blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    incidents_created: list[str] = Field(default_factory=list)
    top_strategy_id: str | None = None
    top_strategy_status: str | None = None
    leaderboard_hash: str | None = None
    evidence_score_status: str = "UNAVAILABLE"
    drift_status: str = "UNAVAILABLE"
    report_paths: dict[str, str] = Field(default_factory=dict)
    live_promotion_status: str = "LIVE_BLOCKED"
    live_ready: bool = False


def build_proving_record(state: AutonomousRunState | dict[str, Any]) -> ProvingRunRecord:
    payload = state.model_dump(mode="json") if isinstance(state, AutonomousRunState) else state
    run_id = str(payload.get("run_id") or deterministic_id("proving-run", _now(), length=20))
    dataset = _nested(payload.get("dataset_evidence_summary", {}), "dataset_evidence")
    historical = _nested(payload.get("historical_data_summary", {}), "historical_data")
    dryrun = _nested(payload.get("dryrun_monitoring_summary", {}), "dryrun_monitoring")
    trades = _nested(payload.get("freqtrade_trade_artifacts_summary", {}), "freqtrade_trade_artifacts")
    strategy = payload.get("strategy_research_summary", {})
    warnings = _collect_warnings(dataset, historical, dryrun, trades, strategy)
    blockers = _collect_blockers(payload, dataset, historical, dryrun, trades)
    return ProvingRunRecord(
        run_id=run_id,
        timestamp=str(payload.get("completed_at") or payload.get("started_at") or _now()),
        run_status=str(payload.get("status", "unknown")),
        autonomous_status=str(payload.get("status", "unknown")),
        dryrun_monitoring_status=str(dryrun.get("latest_divergence_status", "UNAVAILABLE")),
        historical_evidence_status=str(
            historical.get("latest_historical_evidence_status", "UNAVAILABLE")
        ),
        strategy_research_status=str(strategy.get("leaderboard_status", "UNAVAILABLE")),
        dataset_quality_status=str(dataset.get("quality_status", "UNAVAILABLE")),
        leakage_status=str(dataset.get("leakage_status", "UNAVAILABLE")),
        trade_reconciliation_status=str(
            trades.get("trade_reconciliation_status", "UNAVAILABLE")
        ),
        proving_blockers=blockers,
        warnings=warnings,
        top_strategy_id=strategy.get("top_research_strategy"),
        top_strategy_status=_top_strategy_status(),
        leaderboard_hash=_hash_file("reports/strategy/leaderboard/latest_leaderboard.json"),
        evidence_score_status=str(dataset.get("evidence_status", "UNAVAILABLE")),
        drift_status=str(payload.get("drift_summary", {}).get("status", "UNAVAILABLE")),
        report_paths=dict(payload.get("report_paths", {})),
    )


def record_to_dict(record: ProvingRunRecord | dict[str, Any]) -> dict[str, Any]:
    return record.model_dump(mode="json") if isinstance(record, ProvingRunRecord) else record


def _nested(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key, payload)
    return value if isinstance(value, dict) else {}


def _collect_warnings(*sections: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    for section in sections:
        warnings.extend(str(item) for item in section.get("warnings", []) or [])
    return warnings


def _collect_blockers(
    payload: dict[str, Any],
    dataset: dict[str, Any],
    historical: dict[str, Any],
    dryrun: dict[str, Any],
    trades: dict[str, Any],
) -> list[str]:
    blockers: list[str] = []
    if str(payload.get("status")) != "completed":
        blockers.append("AUTONOMOUS_RUN_NOT_COMPLETED")
    for source, section in [
        ("dataset", dataset),
        ("historical", historical),
        ("dryrun", dryrun),
        ("trades", trades),
    ]:
        blockers.extend(
            f"{source.upper()}:{item}"
            for item in section.get("blockers", []) or []
            if str(item) != "LIVE_PROMOTION_DISABLED"
        )
    if dataset.get("quality_status") == "FAIL":
        blockers.append("DATASET_QUALITY_FAILED")
    if dataset.get("leakage_status") == "FAIL":
        blockers.append("DATASET_LEAKAGE_FAILED")
    if historical.get("latest_quality_status") == "FAIL":
        blockers.append("HISTORICAL_QUALITY_FAILED")
    if trades.get("trade_reconciliation_status") == "FAIL":
        blockers.append("TRADE_RECONCILIATION_FAILED")
    if dryrun.get("latest_divergence_status") == "FAIL":
        blockers.append("DRYRUN_DIVERGENCE_FAILED")
    return sorted(set(blockers))


def _top_strategy_status() -> str | None:
    path = Path("reports/strategy/leaderboard/latest_leaderboard.json")
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    top = payload.get("top_strategy")
    for entry in payload.get("entries", []):
        if entry.get("strategy_id") == top:
            return entry.get("status")
    return None


def _hash_file(path: str | Path) -> str | None:
    target = Path(path)
    if not target.exists():
        return None
    digest = hashlib.sha256()
    with target.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _now() -> str:
    return datetime.now(UTC).isoformat()
