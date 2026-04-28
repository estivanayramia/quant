from __future__ import annotations

import fnmatch
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from quant_os.data.loaders import load_yaml
from quant_os.integrations.freqtrade.trade_artifacts import (
    FreqtradeArtifact,
    ensure_trade_report_dir,
    write_json_report,
)

DEFAULT_CONFIG: dict[str, Any] = {
    "enabled": True,
    "live_trading_allowed": False,
    "dry_run_only": True,
    "scan": {
        "base_paths": ["freqtrade/user_data", "reports/freqtrade"],
        "include_patterns": ["*.json", "*.jsonl", "*.log", "*.txt", "*.sqlite", "*.db"],
        "exclude_patterns": ["*.env", "*secret*", "*key*", "*credential*"],
        "max_file_size_mb": 50,
    },
}


def load_artifact_config(path: str | Path = "configs/freqtrade_artifacts.yaml") -> dict[str, Any]:
    config = json.loads(json.dumps(DEFAULT_CONFIG))
    config_path = Path(path)
    if config_path.exists():
        loaded = load_yaml(config_path)
        config.update({key: value for key, value in loaded.items() if key != "scan"})
        config["scan"].update(loaded.get("scan", {}))
    return config


def scan_freqtrade_artifacts(
    config_path: str | Path = "configs/freqtrade_artifacts.yaml",
    *,
    write: bool = True,
) -> dict[str, Any]:
    config = load_artifact_config(config_path)
    scan = config.get("scan", {})
    base_paths = [Path(str(path)) for path in scan.get("base_paths", [])]
    include_patterns = [str(pattern) for pattern in scan.get("include_patterns", [])]
    exclude_patterns = [str(pattern).lower() for pattern in scan.get("exclude_patterns", [])]
    max_size = int(float(scan.get("max_file_size_mb", 50)) * 1024 * 1024)
    artifacts: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for base in base_paths:
        if not base.exists():
            skipped.append({"path": str(base), "reason": "BASE_PATH_MISSING"})
            continue
        for path in sorted(item for item in base.rglob("*") if item.is_file()):
            name = path.name.lower()
            if _is_generated_trade_report(path):
                skipped.append({"path": str(path), "reason": "GENERATED_TRADE_REPORT"})
                continue
            if _matches(name, exclude_patterns):
                skipped.append({"path": str(path), "reason": "EXCLUDED_SUSPICIOUS_NAME"})
                continue
            if include_patterns and not _matches(path.name, include_patterns):
                continue
            size = path.stat().st_size
            if size > max_size:
                skipped.append({"path": str(path), "reason": "FILE_TOO_LARGE", "size_bytes": size})
                continue
            artifact = FreqtradeArtifact(
                path=str(path),
                artifact_type=_classify(path),
                size_bytes=size,
                modified_at=datetime.fromtimestamp(path.stat().st_mtime, tz=UTC).isoformat(),
                sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                possible_trade_db=_possible_trade_db(path),
            )
            artifacts.append(artifact.model_dump(mode="json"))

    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "PASS" if artifacts else "UNAVAILABLE",
        "dry_run_only": bool(config.get("dry_run_only", True)),
        "live_trading_allowed": bool(config.get("live_trading_allowed", False)),
        "artifacts_found": len(artifacts),
        "artifacts": artifacts,
        "skipped": skipped,
        "warnings": [] if artifacts else ["NO_FREQTRADE_TRADE_ARTIFACTS_FOUND"],
    }
    if write:
        _write_scan_reports(payload)
    return payload


def _matches(name: str, patterns: list[str]) -> bool:
    lowered = name.lower()
    return any(fnmatch.fnmatch(lowered, pattern.lower()) for pattern in patterns)


def _classify(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".json":
        return "json"
    if suffix == ".jsonl":
        return "jsonl"
    if suffix in {".log", ".txt"}:
        return "log"
    if suffix in {".sqlite", ".db"}:
        return "sqlite"
    return "unknown"


def _possible_trade_db(path: Path) -> bool:
    lowered = path.name.lower()
    return path.suffix.lower() in {".sqlite", ".db"} and any(
        token in lowered for token in ["trade", "freqtrade", "dryrun", "dry-run"]
    )


def _is_generated_trade_report(path: Path) -> bool:
    normalized = path.as_posix().lower()
    return "/reports/freqtrade/trades/" in f"/{normalized}" and path.name.startswith("latest_")


def _write_scan_reports(payload: dict[str, Any]) -> None:
    root = ensure_trade_report_dir()
    write_json_report(root / "latest_artifact_scan.json", payload)
    lines = [
        "# Freqtrade Trade Artifact Scan",
        "",
        "Dry-run only. No live trading. No artifacts are uploaded.",
        "",
        f"Status: {payload['status']}",
        f"Artifacts found: {payload['artifacts_found']}",
        "",
        "## Artifacts",
    ]
    if payload["artifacts"]:
        for artifact in payload["artifacts"]:
            lines.append(f"- {artifact['artifact_type']}: `{artifact['path']}`")
    else:
        lines.append("- None")
    if payload["skipped"]:
        lines.extend(["", "## Skipped"])
        for skipped in payload["skipped"]:
            lines.append(f"- {skipped['reason']}: `{skipped['path']}`")
    (root / "latest_artifact_scan.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
