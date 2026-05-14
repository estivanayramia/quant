from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from quant_os.research.social_intake.social_capture_models import (
    OPTIONAL_CAPTURE_FILES,
    SOCIAL_INTAKE_SAFETY,
    SocialPostArtifact,
)
from quant_os.research.social_intake.x_capture_manifest import read_capture_manifest

REPORT_ROOT = Path("reports/sequence34/social_intake")


def load_social_capture(capture_root: str | Path) -> list[SocialPostArtifact]:
    root = Path(capture_root)
    artifacts = []
    for row in read_capture_manifest(root):
        folder_path = root / row.folder
        text_path = folder_path / "text.txt"
        text = text_path.read_text(encoding="utf-8") if text_path.exists() else ""
        optional_paths = {
            name: folder_path / name if (folder_path / name).exists() else None
            for name in OPTIONAL_CAPTURE_FILES
        }
        missing = [name for name, path in optional_paths.items() if path is None]
        artifacts.append(
            SocialPostArtifact(
                post_id=row.post_id,
                post_url=row.post_url,
                author_handle=row.author_handle,
                captured_at=row.captured_at,
                folder_path=folder_path,
                text=text,
                manifest_notes=row.notes,
                optional_paths=optional_paths,
                missing_optional_files=missing,
                raw_text_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
            )
        )
    return sorted(artifacts, key=lambda item: item.post_id)


def build_capture_inventory(*, capture_root: str | Path) -> dict[str, Any]:
    root = Path(capture_root)
    artifacts = load_social_capture(root)
    posts = [artifact.to_report_dict(capture_root=root) for artifact in artifacts]
    return {
        "schema_version": "social_capture_inventory_v1",
        "sequence": "34",
        "capture_root": str(root),
        "post_count": len(posts),
        "posts": posts,
        "missing_optional_file_count": sum(
            len(post["missing_optional_files"]) for post in posts
        ),
        "network_fetch_performed": False,
        "login_or_session_required": False,
        "screenshots_required_for_tests": False,
        "secrets_detected": _secrets_detected(posts),
        "provenance_preserved": True,
        **SOCIAL_INTAKE_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def write_capture_inventory(
    *,
    capture_root: str | Path,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    payload = build_capture_inventory(capture_root=capture_root)
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _secrets_detected(posts: list[dict[str, Any]]) -> bool:
    credential_markers = ("api key", "access token", "bearer ", "password=")
    for post in posts:
        text = str(post["text"]).lower()
        if any(marker in text for marker in credential_markers):
            return True
    return False


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_capture_inventory.json"
    md_path = root / "latest_capture_inventory.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 34 Social Capture Inventory",
        "",
        "Local captured social artifacts only. No network fetch, login, or screenshots required.",
        "",
        f"Post count: {payload['post_count']}",
        f"Missing optional files: {payload['missing_optional_file_count']}",
        f"Live promotion: {payload['live_promotion_status']}",
        "",
        "## Posts",
    ]
    lines.extend(
        "- {post_id}: {url}, missing={missing}".format(
            post_id=post["post_id"],
            url=post["provenance"]["post_url"],
            missing=",".join(post["missing_optional_files"]) or "none",
        )
        for post in payload["posts"]
    )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
