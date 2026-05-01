from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml


def load_live_credentials(
    credential_path: str | Path | None = None,
    *,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    blockers: list[str] = []
    warnings: list[str] = []
    root = Path(repo_root or Path.cwd()).resolve()
    if credential_path is None:
        blockers.append("LIVE_CREDENTIAL_FILE_MISSING")
        return _payload(blockers, warnings, None, {}, root)
    path = Path(credential_path).expanduser()
    if path.name.lower().startswith(".env") or path.suffix.lower() == ".env":
        blockers.append("LIVE_CREDENTIAL_ENV_FILE_REJECTED")
    try:
        resolved = path.resolve(strict=False)
    except OSError:
        blockers.append("LIVE_CREDENTIAL_PATH_UNRESOLVABLE")
        resolved = path
    if _is_relative_to(resolved, root):
        blockers.append("LIVE_CREDENTIAL_PATH_INSIDE_REPO")
    if not resolved.exists():
        blockers.append("LIVE_CREDENTIAL_FILE_MISSING")
        return _payload(blockers, warnings, resolved, {}, root)
    raw: dict[str, Any] = {}
    try:
        raw = _read_credentials(resolved)
    except (json.JSONDecodeError, yaml.YAMLError, OSError):
        blockers.append("LIVE_CREDENTIAL_FILE_MALFORMED")
    if raw:
        missing = [field for field in ["exchange_name", "api_key", "api_secret"] if not raw.get(field)]
        blockers.extend(f"LIVE_CREDENTIAL_FIELD_MISSING:{field}" for field in missing)
    return _payload(blockers, warnings, resolved, raw, root)


def _read_credentials(path: Path) -> dict[str, Any]:
    if path.suffix.lower() == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
    else:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _payload(
    blockers: list[str],
    warnings: list[str],
    path: Path | None,
    raw: dict[str, Any],
    repo_root: Path,
) -> dict[str, Any]:
    metadata = {
        "credential_path": str(path) if path is not None else None,
        "repo_root": str(repo_root),
        "exchange_name": raw.get("exchange_name"),
        "account_label": raw.get("account_label"),
        "api_key_masked": _mask(raw.get("api_key")),
        "api_secret_present": bool(raw.get("api_secret")),
        "passphrase_present": bool(raw.get("passphrase")),
        "loaded_at": datetime.now(UTC).isoformat(),
    }
    return {
        "status": "PASS" if not blockers else "FAIL",
        "credential_present": bool(raw),
        "blockers": blockers,
        "warnings": warnings,
        "metadata": metadata,
        "secrets_returned": False,
        "live_promotion_status": "LIVE_BLOCKED",
    }


def _mask(value: Any) -> str | None:
    if not value:
        return None
    text = str(value)
    if len(text) <= 4:
        return "****"
    return f"{text[:2]}***{text[-2:]}"


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True

