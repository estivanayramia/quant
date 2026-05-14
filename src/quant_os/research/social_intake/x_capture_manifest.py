from __future__ import annotations

import csv
from pathlib import Path

from quant_os.research.social_intake.social_capture_models import ManifestRow


def read_capture_manifest(capture_root: str | Path) -> list[ManifestRow]:
    root = Path(capture_root)
    manifest_path = root / "manifest.csv"
    with manifest_path.open(newline="", encoding="utf-8") as handle:
        rows = []
        for row in csv.DictReader(handle):
            rows.append(
                ManifestRow(
                    post_id=(row.get("post_id") or "").strip(),
                    post_url=(row.get("post_url") or "").strip(),
                    author_handle=(row.get("author_handle") or "").strip(),
                    captured_at=(row.get("captured_at") or "").strip(),
                    folder=(row.get("folder") or "").strip(),
                    notes=(row.get("notes") or "").strip(),
                )
            )
    return sorted(rows, key=lambda item: item.post_id)
