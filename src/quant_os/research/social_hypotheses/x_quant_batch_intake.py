from __future__ import annotations

import re
import zipfile
from pathlib import Path
from typing import Any

from quant_os.research.strategy_factory.campaign_common import (
    safe_payload,
    stable_id,
    write_json_md,
)

DEFAULT_ZIP = Path("C:/Users/estiv/Downloads/output_x_quant_batch_4_recursive_20260518_010103.zip")

SAFE_PATTERNS = {
    "prediction_market_up_down_microstructure": [
        "up down",
        "basket arbitrage",
        "underlying repricing",
        "orderbook imbalance",
        "near resolution",
        "final seconds",
    ],
    "weather_forecast_market_mismatch": [
        "weather",
        "forecast",
        "nwp",
        "mos",
        "temperature",
        "bucket",
    ],
    "prediction_market_structural": [
        "negation",
        "mutually exclusive",
        "cross platform",
        "resolution rule",
        "settlement timing",
    ],
    "agent_workflow": [
        "handoff",
        "state rehydration",
        "subagent",
        "conflict detector",
        "veto",
    ],
    "tool_repo_lead": [
        "sdk",
        "docs",
        "backtest",
        "dataset",
        "repo",
    ],
    "public_orderbook_microstructure": [
        "orderbook",
        "imbalance",
        "spread",
        "liquidity",
    ],
}

UNSAFE_PATTERNS = {
    "COPY_TRADE_OR_WALLET_FOLLOWING_REJECTED": ["copy trade", "wallet", "mirror"],
    "STEALTH_OR_ANTI_BOT_TOOLING_REJECTED": ["stealth", "captcha", "proxy", "anti-bot"],
    "SOCIAL_PNL_SCREENSHOT_NOT_EVIDENCE": ["pnl", "screenshot", "profit"],
}


def extract_x_quant_hypotheses(zip_path: Path | None = None) -> dict[str, Any]:
    path = zip_path or DEFAULT_ZIP
    text = _read_zip_text(path) if path.exists() else ""
    lowered = text.lower()
    hypotheses = []
    for family, keywords in SAFE_PATTERNS.items():
        matched = [keyword for keyword in keywords if keyword in lowered]
        if matched:
            hypotheses.append(
                {
                    "id": stable_id("xh", {"family": family, "matched": matched}, length=12),
                    "family": family,
                    "matched_terms": matched,
                    "source": str(path),
                    "classification": "UNTRUSTED_HYPOTHESIS_ONLY",
                    "requires_public_replayable_data": True,
                    "social_claim_is_proof": False,
                    "promotion_allowed": True,
                }
            )
    rejection_reasons = [
        reason
        for reason, keywords in UNSAFE_PATTERNS.items()
        if any(keyword in lowered for keyword in keywords)
    ]
    return safe_payload(
        status="X_QUANT_HYPOTHESES_EXTRACTED" if hypotheses or text else "X_QUANT_ZIP_NOT_FOUND",
        zip_path=str(path),
        social_claims_are_proof=False,
        safe_hypotheses=hypotheses,
        safe_hypotheses_count=len(hypotheses),
        unsafe_claims_rejected=len(rejection_reasons),
        rejection_reasons=rejection_reasons,
        raw_text_hash=stable_id("xraw", re.sub(r"\s+", " ", text[:20000]), length=16),
    )


def write_x_quant_hypotheses_report(
    *,
    zip_path: Path | None = None,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    payload = extract_x_quant_hypotheses(zip_path)
    lines = [
        "Social/X capture is untrusted hypothesis input only.",
        f"Status: {payload['status']}",
        f"Safe hypotheses: {payload['safe_hypotheses_count']}",
        f"Unsafe claims rejected: {payload['unsafe_claims_rejected']}",
        f"Rejection reasons: {', '.join(payload['rejection_reasons'] or ['None'])}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
        f"Execution authority: {payload['execution_authority']}",
    ]
    return write_json_md(
        payload,
        output_root=output_root,
        report_dir="social_hypotheses",
        json_name="latest_x_quant_hypotheses.json",
        md_name="latest_x_quant_hypotheses.md",
        title="X Quant Hypotheses",
        lines=lines,
    )


def _read_zip_text(path: Path) -> str:
    chunks = []
    with zipfile.ZipFile(path) as archive:
        for name in sorted(archive.namelist()):
            if name.endswith("/"):
                continue
            if not name.lower().endswith((".txt", ".md", ".json", ".csv", ".html")):
                continue
            with archive.open(name) as handle:
                raw = handle.read(250_000)
            chunks.append(raw.decode("utf-8", errors="ignore"))
    return "\n".join(chunks)
