from __future__ import annotations

import json
from pathlib import Path
from typing import Any

FORBIDDEN_SCOPE_TERMS = {
    "withdraw",
    "withdrawal",
    "transfer",
    "futures",
    "future",
    "margin",
    "leverage",
    "short",
    "options",
    "admin",
    "universal",
}
SECRET_FIELD_TERMS = {"api_key", "secret", "password", "token", "private_key"}
ALLOWED_FUTURE_SCOPES = {"read", "read_balances", "spot_trade_future"}


def evaluate_permission_manifest(manifest: dict[str, Any] | str | Path | None = None) -> dict[str, Any]:
    payload = _load_manifest(manifest)
    if payload is None:
        return {
            "status": "WARN",
            "manifest_present": False,
            "allowed_future_permissions": sorted(ALLOWED_FUTURE_SCOPES),
            "forbidden_scopes": [],
            "credential_fields_present": [],
            "blockers": ["API_KEY_PERMISSION_MANIFEST_MISSING"],
            "warnings": ["No permission manifest was provided; future live canary cannot be considered."],
            "live_promotion_status": "LIVE_BLOCKED",
        }
    scopes = _collect_scopes(payload)
    forbidden = sorted({scope for scope in scopes if _is_forbidden(scope)})
    credential_fields = sorted(_find_credential_fields(payload))
    blockers = []
    if forbidden:
        blockers.append("FORBIDDEN_PERMISSION_SCOPES_PRESENT")
    if credential_fields:
        blockers.append("CREDENTIAL_FIELDS_PRESENT_IN_PERMISSION_MANIFEST")
    return {
        "status": "FAIL" if blockers else "PASS",
        "manifest_present": True,
        "allowed_future_permissions": sorted(ALLOWED_FUTURE_SCOPES),
        "scopes": sorted(scopes),
        "forbidden_scopes": forbidden,
        "credential_fields_present": credential_fields,
        "blockers": blockers,
        "warnings": [],
        "live_promotion_status": "LIVE_BLOCKED",
    }


def _load_manifest(manifest: dict[str, Any] | str | Path | None) -> dict[str, Any] | None:
    if manifest is None:
        return None
    if isinstance(manifest, dict):
        return manifest
    path = Path(manifest)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _collect_scopes(value: Any) -> set[str]:
    scopes: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            key_text = str(key).lower()
            if key_text in {"scope", "scopes", "permissions", "permission"}:
                scopes.update(_collect_scope_values(item))
            else:
                scopes.update(_collect_scopes(item))
    elif isinstance(value, list):
        for item in value:
            scopes.update(_collect_scope_values(item))
    elif isinstance(value, str):
        scopes.add(value.lower())
    return scopes


def _collect_scope_values(value: Any) -> set[str]:
    if isinstance(value, str):
        return {value.lower()}
    if isinstance(value, list):
        return {str(item).lower() for item in value}
    if isinstance(value, dict):
        return _collect_scopes(value)
    return set()


def _is_forbidden(scope: str) -> bool:
    normalized = scope.replace("-", "_").lower()
    return any(term in normalized for term in FORBIDDEN_SCOPE_TERMS)


def _find_credential_fields(value: Any, prefix: str = "") -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            key_text = str(key).lower()
            path = f"{prefix}.{key}" if prefix else str(key)
            if any(term in key_text for term in SECRET_FIELD_TERMS):
                found.add(path)
            found.update(_find_credential_fields(item, path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.update(_find_credential_fields(item, f"{prefix}[{index}]"))
    return found
