from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from quant_os.readiness.canary_readiness_common import safety_payload, write_json_markdown_report

REPORT_DIR = Path("reports/first_dollar_preflight/security")

FORBIDDEN_PATTERNS = [
    "KALSHI-ACCESS-KEY",
    "KALSHI-ACCESS-SIGNATURE",
    "KALSHI-ACCESS-TIMESTAMP",
    "load_private_key",
    "create_signature",
    "sign_request",
    "requests.post",
    "/portfolio/orders",
    "DELETE /portfolio/orders",
]

DEFAULT_SCAN_PATHS = [
    Path("src/quant_os/proving/profit_candidate_artifacts.py"),
    Path("src/quant_os/readiness/first_dollar_provenance_audit.py"),
    Path("src/quant_os/readiness/first_dollar_provenance_repair.py"),
    Path("src/quant_os/readiness/current_market_eligibility.py"),
    Path("src/quant_os/readiness/first_dollar_order_preview.py"),
    Path("src/quant_os/readiness/first_dollar_human_review.py"),
    Path("src/quant_os/readiness/first_dollar_preflight.py"),
    Path("src/quant_os/readiness/weather_manual_canary_packet.py"),
    Path("src/quant_os/readiness/tiny_canary_readiness.py"),
    Path("src/quant_os/execution/weather_dry_run_order_intents.py"),
    Path("src/quant_os/execution/weather_dry_run_parity.py"),
]


def evaluate_security_scan(
    *,
    paths: list[str | Path] | None = None,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    root = Path(output_root)
    scan_paths = [Path(path) for path in (paths or DEFAULT_SCAN_PATHS)]
    findings = []
    for path in scan_paths:
        resolved = path if path.is_absolute() else root / path
        if not resolved.exists():
            continue
        text = resolved.read_text(encoding="utf-8")
        executable = _looks_executable(text)
        for pattern in FORBIDDEN_PATTERNS:
            if pattern in text and executable:
                findings.append(
                    {
                        "path": str(path).replace("\\", "/"),
                        "pattern": pattern,
                        "classification": "EXECUTABLE_ORDER_OR_AUTH_PATH",
                    }
                )
    status = "FIRST_DOLLAR_SECURITY_SCAN_PASSED" if not findings else "FIRST_DOLLAR_SECURITY_SCAN_BLOCKED"
    payload = safety_payload(
        schema_version="first_dollar_security_scan_v1",
        status=status,
        allowed_statuses=[
            "FIRST_DOLLAR_SECURITY_SCAN_PASSED",
            "FIRST_DOLLAR_SECURITY_SCAN_BLOCKED",
        ],
        scanned_paths=[str(path).replace("\\", "/") for path in scan_paths],
        forbidden_patterns=FORBIDDEN_PATTERNS,
        findings=findings,
        blockers=[] if not findings else ["EXECUTABLE_ORDER_OR_AUTH_PATH"],
        next_action="Run current market eligibility."
        if not findings
        else "Remove executable auth/order path before first-dollar preflight.",
        api_keys_loaded=False,
        private_keys_loaded=False,
    )
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_first_dollar_security_scan.json",
        md_name="latest_first_dollar_security_scan.md",
        title="First-Dollar Security Scan",
        summary="Scans the first-dollar no-transmit path for executable auth/order code.",
    )
    return payload


def write_first_dollar_security_scan_report(
    *,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    return evaluate_security_scan(output_root=output_root)


def _looks_executable(text: str) -> bool:
    stripped = "\n".join(
        line for line in text.splitlines() if not line.lstrip().startswith(("#", '"""', "'''"))
    )
    return bool(re.search(r"\b(def|class|return|import|from)\b", stripped))
