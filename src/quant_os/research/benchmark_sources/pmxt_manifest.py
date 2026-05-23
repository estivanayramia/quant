from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

REQUIRED_ORDERBOOK_COLUMNS = ("market_id", "token_id", "timestamp", "bid_price", "ask_price")
OPTIONAL_DEPTH_COLUMNS = ("bid_size", "ask_size")
FORBIDDEN_PMXT_SURFACES = (
    "createOrder",
    "buildOrder",
    "submitOrder",
    "cancelOrder",
    "fetchBalance",
    "fetchPositions",
    "fetchOpenOrders",
)
BLOCKED_MANIFEST_FLAGS = (
    "api_key_required",
    "hosted_api_used",
    "paid_api_used",
    "browser_cookies_used",
    "auth_required",
    "signing_required",
)
MIN_PROOF_GRADE_ORDERBOOK_ROWS = 1000


def summarize_pmxt_manifest(manifest_path: str | Path | None) -> dict[str, Any]:
    if manifest_path is None:
        return _empty("NOT_PROVIDED")
    path = Path(manifest_path)
    if not path.exists():
        return _empty("MISSING", path)

    payload = _read_manifest(path)
    manifest_blockers = _manifest_safety_blockers(payload)
    files = payload.get("files", []) or []
    files_by_kind = dict(
        sorted(Counter(str(item.get("kind", "unknown")) for item in files).items())
    )
    orderbook_files = [item for item in files if item.get("kind") == "orderbook"]
    missing_columns = {
        str(item.get("path", "unknown")): [
            column for column in REQUIRED_ORDERBOOK_COLUMNS if column not in item.get("columns", [])
        ]
        for item in orderbook_files
    }
    missing_columns = {path_key: cols for path_key, cols in missing_columns.items() if cols}
    orderbook_rows = sum(int(item.get("rows", 0) or 0) for item in orderbook_files)
    depth_ready_files = [
        str(item.get("path", "unknown"))
        for item in orderbook_files
        if all(column in item.get("columns", []) for column in OPTIONAL_DEPTH_COLUMNS)
    ]
    proof_grade_ready = (
        not missing_columns
        and bool(orderbook_files)
        and orderbook_rows >= MIN_PROOF_GRADE_ORDERBOOK_ROWS
        and not manifest_blockers
    )
    status = "PASS" if not missing_columns and files and not manifest_blockers else "WARN"
    return {
        "source_id": "pmxt_orderbook_archives",
        "status": status,
        "path": str(path),
        "internet_required": False,
        "api_key_required": bool(payload.get("api_key_required", False)),
        "hosted_api_used": bool(payload.get("hosted_api_used", False)),
        "paid_api_used": bool(payload.get("paid_api_used", False)),
        "browser_cookies_used": bool(payload.get("browser_cookies_used", False)),
        "auth_required": bool(payload.get("auth_required", False)),
        "signing_required": bool(payload.get("signing_required", False)),
        "credential_sources_used": list(payload.get("credential_sources_used", []) or []),
        "forbidden_surfaces": list(FORBIDDEN_PMXT_SURFACES),
        "manifest_forbidden_surfaces_used": _manifest_forbidden_surfaces_used(payload),
        "proof_grade_ready": proof_grade_ready,
        "proof_grade_blockers": []
        if proof_grade_ready
        else _proof_grade_blockers(
            missing_columns=missing_columns,
            orderbook_rows=orderbook_rows,
            manifest_blockers=manifest_blockers,
        ),
        "execution_authority_added": False,
        "files_count": len(files),
        "files_by_kind": files_by_kind,
        "rows": sum(int(item.get("rows", 0) or 0) for item in files),
        "orderbook_rows": orderbook_rows,
        "depth_ready_orderbook_files": depth_ready_files,
        "required_orderbook_columns": list(REQUIRED_ORDERBOOK_COLUMNS),
        "optional_depth_columns": list(OPTIONAL_DEPTH_COLUMNS),
        "missing_orderbook_columns": missing_columns,
    }


def _read_manifest(path: Path) -> dict[str, Any]:
    if path.suffix.lower() in {".yaml", ".yml"}:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return json.loads(path.read_text(encoding="utf-8"))


def _empty(status: str, path: Path | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "source_id": "pmxt_orderbook_archives",
        "status": status,
        "internet_required": False,
        "api_key_required": False,
        "hosted_api_used": False,
        "paid_api_used": False,
        "browser_cookies_used": False,
        "auth_required": False,
        "signing_required": False,
        "credential_sources_used": [],
        "forbidden_surfaces": list(FORBIDDEN_PMXT_SURFACES),
        "manifest_forbidden_surfaces_used": [],
        "proof_grade_ready": False,
        "proof_grade_blockers": ["PMXT_MANIFEST_NOT_AVAILABLE"],
        "execution_authority_added": False,
        "files_count": 0,
        "files_by_kind": {},
        "rows": 0,
        "orderbook_rows": 0,
        "depth_ready_orderbook_files": [],
        "required_orderbook_columns": list(REQUIRED_ORDERBOOK_COLUMNS),
        "optional_depth_columns": list(OPTIONAL_DEPTH_COLUMNS),
        "missing_orderbook_columns": {},
    }
    if path is not None:
        payload["path"] = str(path)
    return payload


def _proof_grade_blockers(
    *,
    missing_columns: dict[str, list[str]],
    orderbook_rows: int,
    manifest_blockers: list[str],
) -> list[str]:
    blockers: list[str] = []
    blockers.extend(manifest_blockers)
    if missing_columns:
        blockers.append("PMXT_ORDERBOOK_REQUIRED_COLUMNS_MISSING")
    if orderbook_rows < MIN_PROOF_GRADE_ORDERBOOK_ROWS:
        blockers.append("PMXT_ORDERBOOK_ROWS_BELOW_PROOF_GRADE_MINIMUM")
    return blockers


def _manifest_safety_blockers(payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    for flag in BLOCKED_MANIFEST_FLAGS:
        if payload.get(flag):
            blockers.append(f"PMXT_MANIFEST_{flag.upper()}_BLOCKED")
    if payload.get("credential_sources_used"):
        blockers.append("PMXT_MANIFEST_CREDENTIAL_SOURCES_BLOCKED")
    if _manifest_forbidden_surfaces_used(payload):
        blockers.append("PMXT_MANIFEST_FORBIDDEN_SURFACES_USED")
    return blockers


def _manifest_forbidden_surfaces_used(payload: dict[str, Any]) -> list[str]:
    used = {str(surface) for surface in payload.get("surfaces_used", []) or []}
    used.update(str(surface) for surface in payload.get("methods_used", []) or [])
    return sorted(surface for surface in used if surface in FORBIDDEN_PMXT_SURFACES)
