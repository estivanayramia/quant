from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from quant_os.research.intake.source_policy import summarize_source_policies

REPORT_ROOT = Path("reports/sequence35/intake_sources")


def load_source_config(source_config_path: str | Path) -> dict[str, Any]:
    path = _resolve_source_config_path(source_config_path)
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {
        "source_config_path": str(path),
        "sources": list(payload.get("sources") or []),
    }


def source_config_repo_root(source_config_path: str | Path) -> Path:
    path = _resolve_source_config_path(source_config_path)
    if path.parent.name == "configs":
        return path.parent.parent
    return path.parent


def resolve_source_local_path(source: dict[str, Any], *, source_config_path: str | Path) -> Path:
    local_path = Path(str(source.get("local_path") or ""))
    if local_path.is_absolute():
        return local_path
    return source_config_repo_root(source_config_path) / local_path


def _resolve_source_config_path(source_config_path: str | Path) -> Path:
    path = Path(source_config_path)
    if path.exists():
        return path.resolve()
    repo_root = Path(__file__).resolve().parents[4]
    fallback = repo_root / path
    if fallback.exists():
        return fallback.resolve()
    return path.resolve()


def write_source_policy_report(
    *,
    source_config_path: str | Path,
    output_root: str | Path = ".",
    manual_network_fetch_enabled: bool = False,
) -> dict[str, Any]:
    config = load_source_config(source_config_path)
    payload = summarize_source_policies(
        sources=config["sources"],
        manual_network_fetch_enabled=manual_network_fetch_enabled,
    )
    payload["source_config_path"] = str(source_config_path)
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_source_policy.json"
    md_path = root / "latest_source_policy.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 35 Research Intake Source Policy",
        "",
        "Governed research intake is fail-closed. Network fetches are disabled by default.",
        "",
        f"Allowed sources: {payload['allowed_source_count']}",
        f"Blocked sources: {payload['blocked_source_count']}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
        f"Execution authority: {payload['execution_authority']}",
        "",
        "## Source Decisions",
    ]
    lines.extend(
        "- {source_id}: {status} ({mode}) blockers={blockers}".format(
            source_id=item["source_id"],
            status=item["policy_status"],
            mode=item["allowed_fetch_mode"],
            blockers=",".join(item["blockers"]) or "none",
        )
        for item in payload["sources"]
    )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
