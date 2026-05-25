from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from json import JSONDecodeError
from pathlib import Path
from typing import Any

ROOT = Path("reports/thousand_strategy_campaign")
PREREG_TS = "2026-05-18T00:00:00Z"
RESUME_COMMAND = ".\\make.cmd thousand-strategy-next-tranche"

SAFETY_STATE: dict[str, Any] = {
    "live_trading_enabled": False,
    "execution_authority": "NONE",
    "order_transmission_enabled": False,
    "authenticated_requests_enabled": False,
    "request_signing_enabled": False,
    "api_keys_loaded": False,
    "private_keys_loaded": False,
    "actual_order_count": 0,
    "actual_cancel_count": 0,
    "checked_account_balance": False,
    "checked_portfolio": False,
}


def now_utc() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def stable_id(prefix: str, payload: Any, *, length: int = 16) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str)
    return f"{prefix}_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:length]}"


def safe_payload(**fields: Any) -> dict[str, Any]:
    payload = dict(SAFETY_STATE)
    payload.update(fields)
    return payload


def write_json_md(
    payload: dict[str, Any],
    *,
    output_root: str | Path,
    report_dir: str,
    json_name: str,
    md_name: str,
    title: str,
    lines: list[str],
) -> dict[str, Any]:
    root = Path(output_root) / ROOT / report_dir
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / json_name
    md_path = root / md_name
    payload = dict(payload)
    payload["report_paths"] = {"json": str(json_path), "markdown": str(md_path)}
    _atomic_write_text(json_path, json.dumps(payload, indent=2, sort_keys=True))
    _atomic_write_text(md_path, "\n".join([f"# {title}", "", *lines]) + "\n")
    return payload


def load_report(
    *,
    output_root: str | Path,
    report_dir: str,
    json_name: str,
) -> dict[str, Any]:
    path = Path(output_root) / ROOT / report_dir / json_name
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except JSONDecodeError:
        return {}


def write_campaign_state(*, output_root: str | Path, **updates: Any) -> dict[str, Any]:
    state = safe_payload(
        schema_version="thousand_strategy_campaign_state_v1",
        campaign_status="THOUSAND_STRATEGY_CAMPAIGN_CHECKPOINTED_NOT_COMPLETE",
        money_worthy_readiness_status="MONEY_WORTHY_NOT_PROVEN",
        manual_canary_packet_status="FIRST_TINY_MANUAL_CANARY_PACKET_BLOCKED",
        variants_generated=0,
        variants_tested=0,
        variants_rejected=0,
        variants_promoted=0,
        current_best_candidate=None,
        blockers=["CAMPAIGN_NOT_COMPLETE"],
        next_action="Resume public-data tournament loop.",
        exact_resume_command=RESUME_COMMAND,
        safety_state=dict(SAFETY_STATE),
        updated_at=now_utc(),
    )
    existing = load_report(output_root=output_root, report_dir="state", json_name="latest_state.json")
    if existing:
        state.update(existing)
    state.update(updates)
    state["updated_at"] = now_utc()
    state["safety_state"] = dict(SAFETY_STATE)
    root = Path(output_root) / ROOT / "state"
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_state.json"
    md_path = root / "latest_state.md"
    _atomic_write_text(json_path, json.dumps(state, indent=2, sort_keys=True))
    md_lines = [
        "# Thousand Strategy Campaign State",
        "",
        f"Campaign status: {state['campaign_status']}",
        f"Money-worthy readiness: {state['money_worthy_readiness_status']}",
        f"Manual canary packet: {state['manual_canary_packet_status']}",
        f"Variants generated: {state['variants_generated']}",
        f"Variants tested: {state['variants_tested']}",
        f"Variants rejected: {state['variants_rejected']}",
        f"Variants promoted: {state['variants_promoted']}",
        f"Current best candidate: {state.get('current_best_candidate')}",
        f"Blockers: {', '.join(state.get('blockers', []) or ['None'])}",
        f"Next action: {state['next_action']}",
        f"Resume: `{state['exact_resume_command']}`",
        f"Live trading enabled: {state['safety_state']['live_trading_enabled']}",
        f"Execution authority: {state['safety_state']['execution_authority']}",
    ]
    _atomic_write_text(md_path, "\n".join(md_lines) + "\n")
    return state


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp_path.write_text(text, encoding="utf-8")
    tmp_path.replace(path)
