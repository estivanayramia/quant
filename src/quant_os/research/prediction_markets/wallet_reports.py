from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.data.prediction_markets.normalization import load_prediction_market_records
from quant_os.research.prediction_markets.wallets import (
    aggregate_wallet_activity,
    load_wallet_activity,
)

REPORT_ROOT = Path("reports/sequence20/wallet_research")


def write_wallet_research_report(
    *,
    activity_fixture_path: str | Path,
    market_fixture_path: str | Path,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    markets = load_prediction_market_records(market_fixture_path)
    activity = load_wallet_activity(activity_fixture_path)
    payload = aggregate_wallet_activity(activity, markets=markets)
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_wallet_research.json"
    md_path = root / "latest_wallet_research.md"
    json_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    lines = [
        "# Sequence 20 Wallet Research",
        "",
        "Research-only wallet activity report. No wallet mirroring or execution authority.",
        "",
        f"Source mode: {payload['source_mode']}",
        f"Live promotion: {payload['live_promotion_status']}",
        "",
        "## Observed facts",
    ]
    for key, value in payload["observed_facts"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Inferred patterns"])
    if payload["inferred_patterns"]:
        for item in payload["inferred_patterns"]:
            lines.append(f"- {item['label']}: {item.get('confidence_limit')}")
    else:
        lines.append("- None")
    lines.extend(["", "## Unknowns"])
    lines.extend(f"- {item}" for item in payload["unknowns"])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
