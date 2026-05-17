from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def utc_now_string() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize_utc_timestamp(value: str) -> str:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def canonical_provenance_hash(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def write_capture_artifact(
    path: str | Path,
    payload: dict[str, Any],
    *,
    artifact_type: str,
    source_id: str,
    captured_at: str | None = None,
) -> dict[str, Any]:
    captured_at = captured_at or utc_now_string()
    artifact_path = Path(path)
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    provenance_hash = canonical_provenance_hash(payload)
    envelope = {
        "artifact_type": artifact_type,
        "source_id": source_id,
        "captured_at": captured_at,
        "read_only": True,
        "payload": payload,
        "provenance_hash": provenance_hash,
    }
    artifact_path.write_text(
        json.dumps(envelope, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return {
        "path": str(artifact_path).replace("\\", "/"),
        "artifact_type": artifact_type,
        "source_id": source_id,
        "captured_at": captured_at,
        "read_only": True,
        "provenance_hash": provenance_hash,
    }


def load_capture_artifact(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if "payload" in payload and "provenance_hash" in payload:
        return payload
    return {
        "artifact_type": "legacy_payload",
        "source_id": "unknown",
        "captured_at": "",
        "read_only": True,
        "payload": payload,
        "provenance_hash": canonical_provenance_hash(payload),
    }
