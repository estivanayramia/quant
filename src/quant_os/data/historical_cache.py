from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from quant_os.data.loaders import load_yaml

CONFIG_PATH = Path("configs/historical_data.yaml")
REPO_ROOT = Path(__file__).resolve().parents[3]
HISTORICAL_ROOT = Path("data/historical")
RAW_DIR = HISTORICAL_ROOT / "raw"
NORMALIZED_DIR = HISTORICAL_ROOT / "normalized"
NORMALIZED_LATEST = NORMALIZED_DIR / "latest.parquet"
CACHE_DIR = HISTORICAL_ROOT / "cache"
REPORT_ROOT = Path("reports/historical")
IMPORT_ROOT = REPORT_ROOT / "imports"
STATUS_JSON = REPORT_ROOT / "latest_status.json"
STATUS_MD = REPORT_ROOT / "latest_status.md"
DEFAULT_FIXTURE = REPO_ROOT / "tests/fixtures/historical/sample_ohlcv_standard.csv"
SCHEMA_VERSION = "historical_ohlcv_v1"
SECRET_PATTERNS = ("secret", "credential", "apikey", "api_key", "password", ".env", "token")


def load_historical_config(path: str | Path = CONFIG_PATH) -> dict[str, Any]:
    return load_yaml(path) if Path(path).exists() else {}


def ensure_historical_dirs() -> None:
    for path in [
        RAW_DIR,
        NORMALIZED_DIR,
        CACHE_DIR,
        IMPORT_ROOT,
        REPORT_ROOT / "manifests",
        REPORT_ROOT / "quality",
        REPORT_ROOT / "evidence",
    ]:
        path.mkdir(parents=True, exist_ok=True)


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_secret_like_path(path: str | Path) -> bool:
    lowered = str(path).lower()
    return any(pattern in lowered for pattern in SECRET_PATTERNS)


def assert_safe_import_path(path: str | Path, allow_external_path: bool = False) -> Path:
    candidate = Path(path)
    if is_secret_like_path(candidate):
        msg = f"refusing secret-like historical import path: {candidate}"
        raise ValueError(msg)
    if not candidate.exists():
        msg = f"historical import path does not exist: {candidate}"
        raise FileNotFoundError(msg)
    if not allow_external_path:
        allowed_roots = [DEFAULT_FIXTURE.parent.resolve(), HISTORICAL_ROOT.resolve()]
        resolved = candidate.resolve()
        if not any(resolved.is_relative_to(root) for root in allowed_roots):
            msg = f"historical import outside allowed roots requires explicit local import: {candidate}"
            raise ValueError(msg)
    return candidate


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")


def read_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def latest_import_record() -> dict[str, Any] | None:
    path = IMPORT_ROOT / "latest_import.json"
    if not path.exists():
        return None
    return read_json(path)


def write_status(payload: dict[str, Any]) -> None:
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    write_json(STATUS_JSON, payload)
    lines = [
        "# Historical Data Status",
        "",
        "Offline/cache-first historical data status. No live trading.",
        "",
        f"Status: {payload.get('status', 'UNKNOWN')}",
        f"Datasets: {payload.get('imported_datasets_count', 0)}",
        f"Live promotion: {payload.get('live_promotion_status', 'LIVE_BLOCKED')}",
        "",
        "## Notes",
    ]
    lines.extend(f"- {item}" for item in payload.get("warnings", []) or ["No warnings"])
    STATUS_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def now_utc() -> str:
    return datetime.now(UTC).isoformat()
