from __future__ import annotations

from typing import Any


def dedupe_artifacts(artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    seen: dict[str, dict[str, Any]] = {}
    unique = []
    duplicates = []
    for artifact in sorted(artifacts, key=lambda item: item["artifact_id"]):
        raw_hash = artifact["raw_hash"]
        if raw_hash in seen:
            duplicate = {
                **artifact,
                "duplicate_of": seen[raw_hash]["artifact_id"],
                "dedupe_status": "DUPLICATE",
            }
            duplicates.append(duplicate)
            continue
        record = {**artifact, "dedupe_status": "UNIQUE"}
        seen[raw_hash] = record
        unique.append(record)
    return {
        "unique_artifacts": unique,
        "duplicate_artifacts": duplicates,
        "unique_count": len(unique),
        "duplicate_count": len(duplicates),
    }
