from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.data.source_registry import build_source_registry_report, default_source_registry
from quant_os.research.benchmark_sources.pmxt_manifest import summarize_pmxt_manifest
from quant_os.research.benchmark_sources.polymarket_public import inspect_polymarket_public
from quant_os.research.benchmark_sources.reference_datasets import summarize_reference_datasets
from quant_os.research.benchmark_sources.yahoo_reference import inspect_yahoo_reference

REPORT_ROOT = Path("reports/external_benchmarks/lane_benchmark")
SCHEMA_VERSION = "lane_benchmark_report_v1"


def write_lane_benchmark_report(
    *,
    output_root: str | Path = ".",
    yahoo_fixture: str | Path | None = None,
    polymarket_fixture: str | Path | None = None,
    pmxt_manifest: str | Path | None = None,
    reference_datasets_manifest: str | Path | None = None,
) -> dict[str, Any]:
    payload = build_lane_benchmark_report(
        yahoo_fixture=yahoo_fixture,
        polymarket_fixture=polymarket_fixture,
        pmxt_manifest=pmxt_manifest,
        reference_datasets_manifest=reference_datasets_manifest,
    )
    _write_report(Path(output_root) / REPORT_ROOT, payload)
    return payload


def build_lane_benchmark_report(
    *,
    yahoo_fixture: str | Path | None = None,
    polymarket_fixture: str | Path | None = None,
    pmxt_manifest: str | Path | None = None,
    reference_datasets_manifest: str | Path | None = None,
) -> dict[str, Any]:
    registry = default_source_registry()
    source_registry_report = build_source_registry_report(write=False)
    adapter_reports = {
        "yahoo_reference": inspect_yahoo_reference(fixture_path=yahoo_fixture),
        "polymarket_public": inspect_polymarket_public(manifest_path=polymarket_fixture),
        "pmxt_manifest": summarize_pmxt_manifest(pmxt_manifest),
        "reference_datasets": summarize_reference_datasets(reference_datasets_manifest),
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "live_trading_enabled": False,
        "prediction_market_execution_authority_added": False,
        "wallet_required": False,
        "signing_required": False,
        "source_registry": {
            "sources_count": source_registry_report["sources_count"],
            "classifications": source_registry_report["classifications"],
            "live_capable_sources": source_registry_report["live_capable_sources"],
        },
        "adapter_reports": adapter_reports,
        "directly_useful_now": _directly_useful_now(),
        "reference_only": _reference_only(),
        "dangerous_to_imitate": _dangerous_to_imitate(),
        "top_implementation_priorities": [
            "Normalize read-only external source provenance before adding more strategy code.",
            "Use local manifests and offline caches to evaluate prediction-market data quality.",
            "Improve event-driven replay realism and walk-forward robustness before any new live gate.",
        ],
        "recommendation": {
            "answer": "both, but staged and read-only first",
            "staged_order": "prediction-market-read-only-research-first",
            "rationale": (
                "The crypto proving lane already has dry-run and live-canary scaffolding, "
                "but recent lane evidence points to weak strategy edge after costs. "
                "Prediction-market sources offer a structurally different research lane, "
                "yet the safe first step is source normalization and offline replay inputs, "
                "not execution authority."
            ),
            "crypto_runtime_proving": "continue only as bounded dry-run/canary infrastructure after stronger evidence",
            "prediction_market_research": "expand read-only ingestion and manifests now",
        },
        "benchmark_mapping": _benchmark_mapping(),
        "runtime_boundary": {
            "ai_direct_order_authority": False,
            "prediction_market_order_authority": False,
            "wallet_signing": False,
            "market_making": False,
            "copy_trading": False,
            "live_default_off": True,
        },
        "registered_sources": [entry.to_report_dict() for entry in registry.entries],
    }


def _directly_useful_now() -> list[dict[str, str]]:
    return [
        {
            "repo": "ranaroussi/yfinance",
            "why": "read-only equities/ETF reference data and explicit terms caveats",
            "quant_os_use": "optional-import adapter plus fixture-backed reference summaries",
        },
        {
            "repo": "Polymarket/py-clob-client",
            "why": "clear split between no-auth public market data and L1/L2 signing/order paths",
            "quant_os_use": "public market/orderbook manifest summaries only",
        },
        {
            "repo": "Jon-Becker/prediction-market-analysis",
            "why": "pre-collected market/trade archive patterns and parquet schemas",
            "quant_os_use": "offline-cache manifests and dataset quality checks",
        },
        {
            "repo": "SII-WANGZJ/Polymarket_data",
            "why": "large cleaned Polymarket tables and unified YES-perspective research fields",
            "quant_os_use": "reference dataset manifest reader, not downloader",
        },
        {
            "repo": "evan-kolberg/prediction-market-backtesting",
            "why": "prediction-market replay realism, staged caches, and execution-model caveats",
            "quant_os_use": "replay requirements and report priorities",
        },
    ]


def _reference_only() -> list[dict[str, str]]:
    return [
        {
            "repo": "OpenBB-finance/OpenBB",
            "reason": (
                "borrow provider registry separation, not broad terminal, workspace/backend, "
                "licensed-provider, or AI-agent platform sprawl"
            ),
        },
        {
            "repo": "microsoft/qlib",
            "reason": (
                "borrow research workflow discipline and benchmark mentality, not full ML platform, "
                "auto-quant/R&D-agent, RL, online-serving, or production execution scope"
            ),
        },
        {
            "repo": "stefan-jansen/machine-learning-for-trading",
            "reason": "borrow ML workflow and backtest-pitfall framing, not notebook zoo structure",
        },
        {
            "repo": "QuantConnect/Lean",
            "reason": "borrow event-driven boundary ideas, not live deployment commands",
        },
        {
            "repo": "vnpy/vnpy",
            "reason": "borrow modular engine/plugin boundaries, not broker connectivity scope",
        },
        {
            "repo": "warproxxx/poly_data",
            "reason": "borrow schema ideas only; GPL implementation is not copied",
        },
        {
            "repo": "pmxt-dev/pmxt",
            "reason": "borrow archive manifest ideas while keeping trading-capable APIs offline-cache-only",
        },
        {
            "repo": "TauricResearch/TradingAgents",
            "reason": (
                "borrow role separation plus auditable checkpoint/decision-log patterns only; "
                "multi-agent trading is not an alpha source"
            ),
        },
        {
            "repo": "K-Dense-AI/scientific-agent-skills",
            "reason": "borrow skill packaging discipline only",
        },
        {
            "repo": "AI4Finance-Foundation/FinGPT",
            "reason": "borrow financial NLP/sentiment support framing only; no model-driven order authority",
        },
        {
            "repo": "tradingview/lightweight-charts",
            "reason": "optional future report visualization hook only",
        },
        {
            "repo": "akfamily/akshare",
            "reason": "data-catalog inspiration only; source terms and regional APIs need separate review",
        },
        {
            "repo": "wilsonfreitas/awesome-quant",
            "reason": "curation checklist only, not runtime code",
        },
        {
            "repo": "shashankvemuri/Finance",
            "reason": "educational examples only, not architecture",
        },
    ]


def _dangerous_to_imitate() -> list[dict[str, str]]:
    return [
        {
            "repo": "Polymarket/agents",
            "risk": "autonomous AI trading plus wallet/private-key setup conflicts with QuantOS live boundaries",
        },
        {
            "repo": "warproxxx/poly-maker",
            "risk": "market-making bot direction assumes liquidity provision as runtime path",
        },
        {
            "repo": "yorkeccak/Polyseer",
            "risk": "alpha-assistant/runtime-product framing is not source-normalization work",
        },
        {
            "repo": "FrondEnt/PolymarketBTC15mAssistant",
            "risk": "real-time trading assistant pattern broadens authority before evidence",
        },
        {
            "repo": "sstklen/trump-code",
            "risk": "event/social-media signal claims and broad scripts are not a robust research spine",
        },
        {
            "repo": "ashishpatel26/500-AI-Agents-Projects",
            "risk": "generic agent catalog does not improve deterministic replay, calibration, or risk controls",
        },
        {
            "repo": "maybe-finance/maybe",
            "risk": "archived consumer-finance product architecture is unrelated to QuantOps profitability path",
        },
        {
            "repo": "unionlabs/union",
            "risk": "ZK bridge and DeFi interoperability architecture is unrelated and would widen security surface",
        },
        {
            "repo": "Polymarket/py-clob-client trading paths",
            "risk": "signing, order creation, posting, and cancellation are explicitly out of scope",
        },
        {
            "repo": "Polymarket/polymarket-cli live/wallet commands",
            "risk": "operator convenience can blur read-only inspection and live authority",
        },
    ]


def _benchmark_mapping() -> dict[str, list[str]]:
    return {
        "data_layer": [
            "OpenBB provider separation",
            "yfinance optional public reference adapter",
            "py-clob-client public market/orderbook paths",
            "poly_data, prediction-market-analysis, and Polymarket_data schema references",
            "pmxt archive candidate manifests",
        ],
        "replay_layer": [
            "LEAN/vn.py event-driven boundaries",
            "prediction-market-backtesting orderbook replay caveats",
            "PMXT orderbook archive manifests",
        ],
        "calibration_research_layer": [
            "Qlib benchmark workflows",
            "machine-learning-for-trading walk-forward and backtest pitfall emphasis",
            "reference prediction-market datasets for robustness studies",
        ],
        "skills_instructions_layer": [
            "scientific-agent-skills packaging discipline",
            "TradingAgents role separation and auditable resume/log ideas without autonomous trading authority",
            "FinGPT as support-only financial NLP/sentiment reference",
        ],
        "operator_report_layer": [
            "OpenBB consume-everywhere reporting mindset",
            "lightweight-charts as optional future visualization hook",
            "Polymarket CLI public command taxonomy as a cautionary boundary reference",
        ],
    }


def _write_report(root: Path, payload: dict[str, Any]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "latest_external_benchmark_report.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    lines = [
        "# External Benchmark Lane Report",
        "",
        "Conservative, read-only benchmark synthesis for QuantOS. No live trading.",
        "",
        f"Status: {payload['status']}",
        f"Recommendation: {payload['recommendation']['answer']}",
        f"Staged order: {payload['recommendation']['staged_order']}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
        f"Prediction-market execution authority added: {payload['prediction_market_execution_authority_added']}",
        "",
        "## Top Priorities",
    ]
    lines.extend(f"- {priority}" for priority in payload["top_implementation_priorities"])
    lines.extend(["", "## Directly Useful Now"])
    lines.extend(
        f"- {item['repo']}: {item['quant_os_use']}" for item in payload["directly_useful_now"]
    )
    lines.extend(["", "## Dangerous To Imitate"])
    lines.extend(f"- {item['repo']}: {item['risk']}" for item in payload["dangerous_to_imitate"])
    (root / "latest_external_benchmark_report.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )
