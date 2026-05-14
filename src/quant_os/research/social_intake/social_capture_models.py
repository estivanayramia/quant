from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

SOCIAL_INTAKE_SAFETY = {
    "execution_authority": "NONE",
    "wallet_signing_enabled": False,
    "live_trading_enabled": False,
    "copy_trading_enabled": False,
    "real_orders_enabled": False,
    "prediction_market_execution_authority_added": False,
    "social_posts_are_trade_signals": False,
}

OPTIONAL_CAPTURE_FILES = ("post.json", "page.html", "screenshot.png", "notes.md")


@dataclass(frozen=True)
class ManifestRow:
    post_id: str
    post_url: str
    author_handle: str
    captured_at: str
    folder: str
    notes: str


@dataclass(frozen=True)
class SocialPostArtifact:
    post_id: str
    post_url: str
    author_handle: str
    captured_at: str
    folder_path: Path
    text: str
    manifest_notes: str
    optional_paths: dict[str, Path | None]
    missing_optional_files: list[str]
    raw_text_sha256: str

    def to_report_dict(self, *, capture_root: Path) -> dict[str, object]:
        source_paths = {
            "text.txt": str(self.folder_path / "text.txt"),
            **{
                name: str(path) if path is not None else None
                for name, path in self.optional_paths.items()
            },
        }
        return {
            "post_id": self.post_id,
            "text": self.text,
            "text_preview": self.text[:180],
            "raw_text_sha256": self.raw_text_sha256,
            "missing_optional_files": self.missing_optional_files,
            "source_paths": source_paths,
            "provenance": {
                "capture_root": str(capture_root),
                "post_url": self.post_url,
                "author_handle": self.author_handle,
                "captured_at": self.captured_at,
                "folder_path": str(self.folder_path),
                "manifest_notes": self.manifest_notes,
            },
        }
