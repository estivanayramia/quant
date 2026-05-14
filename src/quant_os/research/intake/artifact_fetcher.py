from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from quant_os.research.intake.scrapling_adapter import (
    is_scrapling_available,
    parse_cached_text_or_html,
)
from quant_os.research.intake.source_config import (
    load_source_config,
    resolve_source_local_path,
)
from quant_os.research.intake.source_policy import summarize_source_policies
from quant_os.research.social_intake.capture_loader import load_social_capture
from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY

REPORT_ROOT = Path("reports/sequence35/intake_run")
DETERMINISTIC_FETCH_TIMESTAMP = "1970-01-01T00:00:00Z"


def write_artifact_fetch_report(
    *,
    source_config_path: str | Path,
    output_root: str | Path = ".",
    manual_network_fetch_enabled: bool = False,
    force_scrapling_absent: bool = False,
) -> dict[str, Any]:
    payload = build_artifact_fetch_report(
        source_config_path=source_config_path,
        manual_network_fetch_enabled=manual_network_fetch_enabled,
        force_scrapling_absent=force_scrapling_absent,
    )
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def build_artifact_fetch_report(
    *,
    source_config_path: str | Path,
    manual_network_fetch_enabled: bool = False,
    force_scrapling_absent: bool = False,
) -> dict[str, Any]:
    config = load_source_config(source_config_path)
    policy = summarize_source_policies(
        sources=config["sources"],
        manual_network_fetch_enabled=manual_network_fetch_enabled,
    )
    policy_by_id = {item["source_id"]: item for item in policy["sources"]}
    artifacts = []
    rejected = []
    for source in config["sources"]:
        decision = policy_by_id[source["source_id"]]
        if decision["policy_status"] != "ALLOWED":
            rejected.append(decision)
            continue
        artifacts.append(
            _load_artifact_from_source(source, source_config_path=source_config_path)
        )

    return {
        "schema_version": "research_artifact_fetch_report_v1",
        "sequence": "35",
        "fetch_status": "LOCAL_AND_CACHED_ARTIFACTS_LOADED",
        "scrapling_available": is_scrapling_available(force_absent=force_scrapling_absent),
        "manual_network_fetch_enabled": manual_network_fetch_enabled,
        "network_fetch_attempted": False,
        "fetched_artifact_count": len(artifacts),
        "rejected_source_count": len(rejected),
        "artifacts": sorted(artifacts, key=lambda item: item["artifact_id"]),
        "rejected_sources": rejected,
        "source_policy": policy,
        **SOCIAL_INTAKE_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def _load_artifact_from_source(
    source: dict[str, Any],
    *,
    source_config_path: str | Path,
) -> dict[str, Any]:
    local_path = resolve_source_local_path(source, source_config_path=source_config_path)
    source_type = str(source.get("source_type"))
    if source_type == "social_capture":
        posts = load_social_capture(local_path)
        text = "\n\n".join(post.text for post in posts)
        raw = "\n".join(f"{post.post_id}:{post.raw_text_sha256}" for post in posts)
        fetch_method = "local_capture_directory"
        post_ids = [post.post_id for post in posts]
    else:
        parsed = parse_cached_text_or_html(local_path)
        text = parsed["text"]
        raw = parsed["raw"]
        fetch_method = parsed["parser"]
        post_ids = []

    raw_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return {
        "artifact_id": f"artifact_{source['source_id']}",
        "source_id": source["source_id"],
        "source_type": source_type,
        "artifact_type": source.get("expected_artifact_type", "unknown"),
        "source_path": str(local_path),
        "source_url": source.get("url", ""),
        "fetch_method": fetch_method,
        "fetched_at": DETERMINISTIC_FETCH_TIMESTAMP,
        "raw_hash": raw_hash,
        "text_hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "text": text,
        "text_preview": text[:220],
        "post_ids": post_ids,
        "policy_decision": "ALLOW_LOCAL_OR_CACHED",
        "network_fetch_attempted": False,
        "direct_execution_allowed": False,
    }


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_artifact_fetch_report.json"
    md_path = root / "latest_artifact_fetch_report.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 35 Artifact Fetch Report",
        "",
        "Only local captures and cached artifacts were loaded. Network fetch was not attempted.",
        "",
        f"Fetched artifacts: {payload['fetched_artifact_count']}",
        f"Rejected sources: {payload['rejected_source_count']}",
        f"Scrapling available: {payload['scrapling_available']}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
        "",
        "## Artifacts",
    ]
    lines.extend(
        "- {source_id}: {method}, hash={raw_hash}".format(
            source_id=item["source_id"],
            method=item["fetch_method"],
            raw_hash=item["raw_hash"][:12],
        )
        for item in payload["artifacts"]
    )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
