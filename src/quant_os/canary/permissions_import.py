from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from quant_os.canary.permissions import evaluate_permission_manifest
from quant_os.canary.policy import CANARY_ROOT, write_canary_report
from quant_os.data.loaders import load_yaml

DEFAULT_PERMISSION_MANIFEST = Path("tests/fixtures/canary/permission_manifest_safe.yaml")
PERMISSION_JSON = CANARY_ROOT / "latest_permission_manifest.json"
PERMISSION_MD = CANARY_ROOT / "latest_permission_manifest.md"

FORBIDDEN_BOOLEAN_FIELDS = {
    "withdrawal_enabled": "WITHDRAWAL_ENABLED_TRUE",
    "transfer_enabled": "TRANSFER_ENABLED_TRUE",
    "futures_enabled": "FUTURES_ENABLED_TRUE",
    "margin_enabled": "MARGIN_ENABLED_TRUE",
    "leverage_enabled": "LEVERAGE_ENABLED_TRUE",
    "shorting_enabled": "SHORTING_ENABLED_TRUE",
    "admin_scope": "ADMIN_SCOPE_TRUE",
    "universal_scope": "UNIVERSAL_SCOPE_TRUE",
}


def import_permission_manifest(
    path: str | Path = DEFAULT_PERMISSION_MANIFEST,
    write: bool = True,
) -> dict[str, Any]:
    manifest_path = Path(path)
    blockers: list[str] = []
    warnings: list[str] = []
    raw: dict[str, Any] = {}
    if _is_secret_like_path(manifest_path):
        blockers.append("PERMISSION_MANIFEST_SECRET_LIKE_PATH")
    elif not manifest_path.exists():
        blockers.append("PERMISSION_MANIFEST_MISSING")
    else:
        try:
            raw = _read_manifest(manifest_path)
        except (json.JSONDecodeError, yaml.YAMLError, OSError) as exc:
            blockers.append("PERMISSION_MANIFEST_PARSE_FAILED")
            warnings.append(str(exc))
    normalized_scopes = _normalized_scopes(raw)
    if not normalized_scopes:
        blockers.append("PERMISSION_MANIFEST_SCOPES_MISSING")
    for field, reason in FORBIDDEN_BOOLEAN_FIELDS.items():
        if raw.get(field) is True:
            blockers.append(reason)
    config = load_yaml("configs/canary_rehearsal.yaml") if Path("configs/canary_rehearsal.yaml").exists() else {}
    allowed = set(
        config.get("permission_manifest", {}).get(
            "allowed_scopes_future",
            ["trade_spot_only", "read_balances_optional"],
        )
    )
    unknown_scopes = sorted(scope for scope in normalized_scopes if scope not in allowed)
    if unknown_scopes:
        blockers.append("UNKNOWN_PERMISSION_SCOPES_PRESENT")
    permission_check = evaluate_permission_manifest({"scopes": sorted(normalized_scopes), **raw} if raw else None)
    blockers.extend(permission_check.get("blockers", []))
    status = "FAIL" if blockers else "PASS"
    payload = {
        "status": status,
        "generated_at": datetime.now(UTC).isoformat(),
        "source_path": str(manifest_path),
        "exchange_name": raw.get("exchange_name"),
        "manifest_present": bool(raw),
        "normalized_scope_list": sorted(normalized_scopes),
        "unknown_scopes": unknown_scopes,
        "forbidden_scopes": permission_check.get("forbidden_scopes", []),
        "credential_fields_present": permission_check.get("credential_fields_present", []),
        "blockers": sorted(set(blockers)),
        "warnings": warnings,
        "raw_manifest_metadata": _safe_metadata(raw),
        "connects_to_exchange": False,
        "credentials_required": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "next_commands": [
            "make.cmd canary-arm-token",
            "make.cmd canary-preflight-rehearsal",
        ],
    }
    if write:
        write_canary_report(PERMISSION_JSON, PERMISSION_MD, "Canary Permission Manifest", payload)
    return payload


def validate_latest_permission_manifest(path: str | Path = PERMISSION_JSON) -> dict[str, Any]:
    report_path = Path(path)
    if not report_path.exists():
        return import_permission_manifest(path=Path("__missing_permission_manifest__.yaml"), write=False)
    try:
        payload = json.loads(report_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {
            "status": "FAIL",
            "blockers": ["PERMISSION_MANIFEST_REPORT_UNREADABLE"],
            "warnings": [],
            "live_promotion_status": "LIVE_BLOCKED",
        }
    return payload


def _read_manifest(path: Path) -> dict[str, Any]:
    if path.suffix.lower() == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _normalized_scopes(raw: dict[str, Any]) -> set[str]:
    scopes = raw.get("scope_list", raw.get("scopes", raw.get("permissions", [])))
    if isinstance(scopes, str):
        scopes = [scopes]
    if not isinstance(scopes, list):
        return set()
    return {str(scope).strip().lower().replace("-", "_") for scope in scopes if str(scope).strip()}


def _safe_metadata(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in raw.items()
        if key
        in {
            "exchange_name",
            "notes",
            "withdrawal_enabled",
            "transfer_enabled",
            "futures_enabled",
            "margin_enabled",
            "leverage_enabled",
            "shorting_enabled",
            "admin_scope",
            "universal_scope",
        }
    }


def _is_secret_like_path(path: Path) -> bool:
    lowered = path.name.lower()
    return any(token in lowered for token in [".env", "secret", "credential"])
