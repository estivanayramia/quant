from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from quant_os.data.prediction_markets.normalization import load_prediction_market_records
from quant_os.research.prediction_markets.quality import (
    RESEARCHABLE,
    evaluate_market_quality,
)

QUALITY_ROOT = Path("reports/sequence20/market_quality")
INVENTORY_ROOT = Path("reports/sequence20/market_inventory")
PRIORITY_ROOT = Path("reports/sequence20/research_priority")


def write_market_quality_report(
    *,
    fixture_path: str | Path,
    output_root: str | Path = ".",
    as_of: datetime | None = None,
) -> dict[str, Any]:
    records = load_prediction_market_records(fixture_path)
    payload = evaluate_market_quality(records, as_of=as_of)
    payload["report_paths"] = _write_report(
        payload,
        output_root=output_root,
        report_root=QUALITY_ROOT,
        json_name="latest_market_quality.json",
        md_name="latest_market_quality.md",
        title="Sequence 20 Market Quality",
        sections=_quality_sections(payload),
    )
    return payload


def write_market_inventory_report(
    *,
    fixture_path: str | Path,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    records = load_prediction_market_records(fixture_path)
    generated_at = datetime.now(UTC).isoformat()
    markets = [
        {
            "market_id": record.market_id,
            "condition_id": record.condition_id,
            "slug": record.slug,
            "title": record.title,
            "status": record.status.value,
            "outcomes": [outcome.contract_name for outcome in record.outcomes],
            "end_time": record.end_time.isoformat() if record.end_time else None,
            "resolution_time": record.resolution_time.isoformat()
            if record.resolution_time
            else None,
            "volume": record.volume,
            "liquidity": record.liquidity,
            "category": record.category,
            "tags": record.tags,
            "join_keys": record.join_keys,
        }
        for record in records
    ]
    payload = {
        "generated_at": generated_at,
        "sequence": "20",
        "source": "polymarket",
        "source_mode": _source_mode(records),
        "market_count": len(markets),
        "markets": markets,
        "observed_facts": [
            "Inventory is built from saved prediction-market metadata only.",
            "Outcomes, timing, volume, liquidity, tags, and join keys are preserved.",
        ],
        "inferred_patterns": [
            "No edge is inferred from inventory membership.",
        ],
        "unknowns": [
            "Reference context, wallet causality, and final resolution labels may be incomplete.",
        ],
        "live_trading_enabled": False,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }
    payload["report_paths"] = _write_report(
        payload,
        output_root=output_root,
        report_root=INVENTORY_ROOT,
        json_name="latest_market_inventory.json",
        md_name="latest_market_inventory.md",
        title="Sequence 20 Market Inventory",
        sections=_inventory_sections(payload),
    )
    return payload


def write_research_priority_report(
    *,
    fixture_path: str | Path,
    output_root: str | Path = ".",
    as_of: datetime | None = None,
) -> dict[str, Any]:
    quality = evaluate_market_quality(load_prediction_market_records(fixture_path), as_of=as_of)
    candidates = [
        item for item in quality["markets"] if item["research_worthiness"] == RESEARCHABLE
    ]
    candidates = sorted(
        candidates,
        key=lambda item: (float(item.get("liquidity") or 0.0), float(item.get("volume") or 0.0)),
        reverse=True,
    )
    payload = {
        "generated_at": quality["generated_at"],
        "sequence": "20",
        "source": "polymarket",
        "source_mode": quality["source_mode"],
        "status": "RESEARCH_ONLY",
        "top_candidate_research_lanes": [
            {
                "market_id": item["market_id"],
                "title": item["title"],
                "reason": "clean binary structure with sufficient saved liquidity and volume",
                "next_research_need": "attach resolution/reference context before replay design",
                "join_keys": item["join_keys"],
            }
            for item in candidates
        ],
        "quality_summary": quality["summary"],
        "missing_data": _missing_data_summary(quality["markets"]),
        "likely_failure_modes": [
            "Ambiguous market terms may make labels unreliable.",
            "Thin markets may not support realistic replay assumptions.",
            "Wallet clusters can be manipulation, hedging, or coincidence; no causality is assumed.",
            "Saved samples may not represent current market state.",
        ],
        "observed_facts": quality["observed_facts"],
        "inferred_patterns": quality["inferred_patterns"],
        "unknowns": quality["unknowns"],
        "live_trading_enabled": False,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }
    payload["report_paths"] = _write_report(
        payload,
        output_root=output_root,
        report_root=PRIORITY_ROOT,
        json_name="latest_research_priority.json",
        md_name="latest_research_priority.md",
        title="Sequence 20 Research Priority",
        sections=_priority_sections(payload),
    )
    return payload


def _write_report(
    payload: dict[str, Any],
    *,
    output_root: str | Path,
    report_root: Path,
    json_name: str,
    md_name: str,
    title: str,
    sections: list[str],
) -> dict[str, str]:
    root = Path(output_root) / report_root
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / json_name
    md_path = root / md_name
    json_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    lines = [
        f"# {title}",
        "",
        "Research-only prediction-market report. No execution authority.",
        "",
        f"Source mode: {payload['source_mode']}",
        f"Live promotion: {payload['live_promotion_status']}",
        "",
        *sections,
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}


def _quality_sections(payload: dict[str, Any]) -> list[str]:
    lines = ["## Summary"]
    for key, value in payload["summary"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Markets"])
    for item in payload["markets"]:
        flags = ", ".join(item["quality_flags"]) or "None"
        lines.append(f"- {item['market_id']}: {item['research_worthiness']} ({flags})")
    lines.extend(_fact_sections(payload))
    return lines


def _inventory_sections(payload: dict[str, Any]) -> list[str]:
    lines = ["## Markets"]
    for item in payload["markets"]:
        lines.append(f"- {item['market_id']}: {item['status']} - {item['title']}")
    lines.extend(_fact_sections(payload))
    return lines


def _priority_sections(payload: dict[str, Any]) -> list[str]:
    lines = ["## Top Candidate Research Lanes"]
    if payload["top_candidate_research_lanes"]:
        for item in payload["top_candidate_research_lanes"]:
            lines.append(f"- {item['market_id']}: {item['reason']}")
    else:
        lines.append("- None")
    lines.extend(["", "## Likely Failure Modes"])
    lines.extend(f"- {item}" for item in payload["likely_failure_modes"])
    lines.extend(_fact_sections(payload))
    return lines


def _fact_sections(payload: dict[str, Any]) -> list[str]:
    lines = ["", "## Observed facts"]
    lines.extend(f"- {item}" for item in payload["observed_facts"])
    lines.extend(["", "## Inferred patterns"])
    lines.extend(f"- {item}" for item in payload["inferred_patterns"])
    lines.extend(["", "## Unknowns"])
    lines.extend(f"- {item}" for item in payload["unknowns"])
    return lines


def _missing_data_summary(markets: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in markets:
        for flag in item["quality_flags"]:
            if flag.startswith("MISSING_"):
                counts[flag] = counts.get(flag, 0) + 1
    return counts


def _source_mode(records: list[Any]) -> str:
    modes = sorted({record.source_mode for record in records})
    return modes[0] if len(modes) == 1 else "mixed"
