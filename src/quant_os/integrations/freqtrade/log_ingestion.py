from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from quant_os.integrations.freqtrade.artifacts import ensure_freqtrade_artifact_dirs

LOG_PATTERN = re.compile(
    r"(?P<timestamp>\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:,\d+)?)?\s*"
    r"(?P<level>INFO|WARNING|WARN|ERROR|CRITICAL|DEBUG)?\s*[:|-]?\s*(?P<message>.*)",
    re.IGNORECASE,
)
PAIR_PATTERN = re.compile(r"\b([A-Z0-9]+/[A-Z0-9]+)\b")


@dataclass
class ParsedLogLine:
    timestamp: str | None
    level: str
    message: str
    pair: str | None
    dry_run_indicator: bool
    warning: bool
    error: bool
    raw: str


def ingest_freqtrade_logs(
    docker_stdout: str = "",
    local_logs_dir: str | Path = "freqtrade/user_data/logs",
) -> dict[str, object]:
    dirs = ensure_freqtrade_artifact_dirs()
    raw_text = _collect_raw_logs(docker_stdout, local_logs_dir)
    parsed = [parse_log_line(line) for line in raw_text.splitlines() if line.strip()]
    latest_text = dirs["logs_dir"] / "latest_logs.txt"
    latest_json = dirs["logs_dir"] / "latest_logs.json"
    latest_text.write_text(raw_text, encoding="utf-8")
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "line_count": len(parsed),
        "warnings": sum(1 for item in parsed if item.warning),
        "errors": sum(1 for item in parsed if item.error),
        "dry_run_indicators": sum(1 for item in parsed if item.dry_run_indicator),
        "pairs": sorted({item.pair for item in parsed if item.pair}),
        "entries": [asdict(item) for item in parsed],
        "latest_logs_path": str(latest_text),
    }
    latest_json.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return payload


def parse_log_line(line: str) -> ParsedLogLine:
    match = LOG_PATTERN.match(line.strip())
    groups = match.groupdict() if match else {}
    message = (groups.get("message") or line).strip()
    level = (groups.get("level") or "RAW").upper()
    pair_match = PAIR_PATTERN.search(line)
    lower = line.lower()
    return ParsedLogLine(
        timestamp=groups.get("timestamp"),
        level=level,
        message=message,
        pair=pair_match.group(1) if pair_match else None,
        dry_run_indicator="dry-run" in lower or "dry_run" in lower,
        warning=level in {"WARNING", "WARN"} or "warning" in lower,
        error=level in {"ERROR", "CRITICAL"} or "error" in lower,
        raw=line,
    )


def _collect_raw_logs(docker_stdout: str, local_logs_dir: str | Path) -> str:
    chunks = [docker_stdout.strip()] if docker_stdout.strip() else []
    root = Path(local_logs_dir)
    if root.exists():
        for path in sorted(root.glob("*.log")):
            chunks.append(path.read_text(encoding="utf-8", errors="replace"))
    if not chunks:
        return ""
    return "\n".join(chunks).strip() + "\n"
