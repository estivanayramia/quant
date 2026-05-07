from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.data.source_models import (
    BenchmarkLayer,
    SourceClassification,
    SourceEntry,
    SourceRegistry,
)

REPORT_ROOT = Path("reports/external_benchmarks/source_registry")
SCHEMA_VERSION = "source_registry_v1"


def default_source_registry() -> SourceRegistry:
    return SourceRegistry(entries=tuple(_source_entries()))


def build_source_registry_report(
    *,
    output_root: str | Path = ".",
    write: bool = True,
) -> dict[str, Any]:
    registry = default_source_registry()
    sources = [entry.to_report_dict() for entry in registry.entries]
    classifications = {
        classification.value: len(registry.classified(classification))
        for classification in SourceClassification
    }
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "sources_count": len(sources),
        "sources": sources,
        "classifications": classifications,
        "live_capable_sources": [entry.source_id for entry in registry.live_capable_sources()],
        "live_trading_enabled": False,
        "execution_authority_added": False,
        "wallet_required": False,
        "signing_required": False,
        "internet_required_for_ci": False,
        "summary": (
            "Read-only external-source registry for research provenance. "
            "Live-capable packages are identified but not authorized."
        ),
    }
    if write:
        _write_report(Path(output_root) / REPORT_ROOT, payload)
    return payload


def _source_entries() -> list[SourceEntry]:
    return [
        SourceEntry(
            source_id="yfinance",
            name="yfinance public Yahoo Finance adapter",
            repository_url="https://github.com/ranaroussi/yfinance",
            homepage_url="https://ranaroussi.github.io/yfinance",
            classification=SourceClassification.RUNTIME_SAFE,
            provenance="Public Yahoo Finance access through optional yfinance dependency.",
            license_name="Apache-2.0 for yfinance code; Yahoo data terms apply to downloaded data",
            license_caveat=(
                "Yahoo Finance data is described by yfinance as personal-use oriented; "
                "cache and provenance must remain explicit."
            ),
            data_caveats=(
                "Not exchange-grade market data.",
                "Network fetch must be explicitly enabled outside CI.",
                "Suitable for reference research, sanity checks, and equities/ETF baselines only.",
            ),
            requires_network=True,
            allowed_uses=(
                "Optional read-only OHLCV/reference data pulls.",
                "Fixture-backed baseline reports.",
                "Source-normalization tests.",
            ),
            forbidden_uses=(
                "live order placement",
                "wallet signing",
                "broker routing",
                "unattended network fetch in CI",
            ),
            mapped_layers=(BenchmarkLayer.DATA, BenchmarkLayer.CALIBRATION_RESEARCH),
            optional_import="yfinance",
            runtime_notes="Runtime-safe only as a read-only provider with network fetch default-off.",
        ),
        SourceEntry(
            source_id="openbb",
            name="OpenBB Open Data Platform reference",
            repository_url="https://github.com/OpenBB-finance/OpenBB",
            homepage_url="https://docs.openbb.co",
            classification=SourceClassification.REFERENCE_ONLY,
            provenance="Benchmark for source integration architecture and provider separation.",
            license_name="AGPL-3.0-style project license; provider data licenses vary",
            license_caveat="Use as architecture reference only unless license review approves direct reuse.",
            data_caveats=(
                "Provider catalog mixes public, licensed, and proprietary sources.",
                "Do not turn QuantOS into a broad data terminal.",
                "Do not follow the workspace/backend/API-server or AI-agent platform path.",
            ),
            requires_network=True,
            allowed_uses=(
                "Provider registry inspiration.",
                "Connect-once consume-everywhere architecture notes.",
                "Optional-import reference mode.",
            ),
            forbidden_uses=(
                "copying provider code",
                "live order placement",
                "wallet signing",
                "broadening QuantOS into a generic data platform",
                "turning source integration into an AI-agent workspace backend",
            ),
            mapped_layers=(BenchmarkLayer.DATA, BenchmarkLayer.OPERATOR_REPORT),
            optional_import="openbb",
            runtime_notes=(
                "Reference-only in this tranche; keep the useful provider-separation idea "
                "without importing the broader workspace/backend platform."
            ),
        ),
        SourceEntry(
            source_id="py_clob_client_public",
            name="py-clob-client public read-only paths",
            repository_url="https://github.com/Polymarket/py-clob-client",
            classification=SourceClassification.RUNTIME_SAFE,
            provenance="Polymarket CLOB client public methods such as health, server time, markets, prices, and books.",
            license_name="MIT for client code; Polymarket API/data terms apply",
            license_caveat="The package also supports trading and signing; only level-0 public methods are in scope.",
            data_caveats=(
                "Public CLOB snapshots are point-in-time and need cache manifests for replay.",
                "Authenticated user trades and order management are out of scope.",
            ),
            requires_network=True,
            live_capable_package=True,
            allowed_uses=(
                "Read-only market discovery.",
                "Read-only midpoint, price, and orderbook snapshots.",
                "Local fixture and manifest parsing.",
            ),
            forbidden_uses=(
                "private key loading",
                "wallet signing",
                "API credential derivation",
                "order creation",
                "order posting",
                "live order placement",
                "order cancellation",
                "credentialed user-order queries",
                "wallet mirroring",
            ),
            mapped_layers=(BenchmarkLayer.DATA, BenchmarkLayer.REPLAY),
            optional_import="py_clob_client",
            runtime_notes="The registry authorizes public paths only; trading methods remain forbidden.",
        ),
        SourceEntry(
            source_id="poly_data_reference",
            name="poly_data Polymarket data pipeline reference",
            repository_url="https://github.com/warproxxx/poly_data",
            classification=SourceClassification.REFERENCE_ONLY,
            provenance="Reference pattern for markets, order-filled events, and structured trade data.",
            license_name="GPL-3.0",
            license_caveat="GPL license makes direct code copying inappropriate for this tranche.",
            data_caveats=(
                "Use schemas and provenance ideas only.",
                "Live fetching is not required for CI.",
            ),
            requires_network=True,
            allowed_uses=(
                "Schema inspiration for market/trade/order-filled data.",
                "Offline fixture shape comparisons.",
            ),
            forbidden_uses=(
                "copying GPL implementation",
                "live order placement",
                "wallet signing",
                "wallet mirroring",
            ),
            mapped_layers=(BenchmarkLayer.DATA, BenchmarkLayer.REPLAY),
            runtime_notes="Reference-only due license and scope.",
        ),
        SourceEntry(
            source_id="pmxt_orderbook_archives",
            name="PMXT orderbook archive candidates",
            repository_url="https://github.com/pmxt-dev/pmxt",
            homepage_url="https://pmxt.dev",
            classification=SourceClassification.OFFLINE_CACHE_ONLY,
            provenance="Unified prediction-market API and archive candidate manifests.",
            license_name="MIT for PMXT code; venue data terms vary",
            license_caveat="PMXT supports trading APIs; QuantOS uses local manifests and cache metadata only here.",
            data_caveats=(
                "Prediction-market APIs differ by venue and may omit historical L2 depth.",
                "Only local archive manifests are CI-safe.",
            ),
            requires_network=False,
            live_capable_package=True,
            allowed_uses=(
                "Local orderbook cache manifest inspection.",
                "Venue schema comparison.",
                "Future replay input evaluation.",
            ),
            forbidden_uses=(
                "live order placement",
                "wallet signing",
                "credentialed venue actions",
                "market making",
                "copy trading",
            ),
            mapped_layers=(BenchmarkLayer.DATA, BenchmarkLayer.REPLAY),
            optional_import="pmxt",
            runtime_notes="Offline-cache-only in this tranche.",
        ),
        SourceEntry(
            source_id="prediction_market_analysis",
            name="prediction-market-analysis public datasets",
            repository_url="https://github.com/Jon-Becker/prediction-market-analysis",
            classification=SourceClassification.OFFLINE_CACHE_ONLY,
            provenance="Public Polymarket/Kalshi market and trade data research archive and schemas.",
            license_name="MIT for code; dataset terms and citation expectations must be reviewed",
            license_caveat="Large external dataset should be referenced by manifest, not committed.",
            data_caveats=(
                "Large archive; no internet download in CI.",
                "Use local subset manifests for tests and smoke checks.",
            ),
            requires_network=False,
            allowed_uses=(
                "Offline manifest and schema inspection.",
                "Reference market/trade parquet layout.",
                "Research-only calibration studies.",
            ),
            forbidden_uses=(
                "committing large archives",
                "live order placement",
                "wallet signing",
                "wallet mirroring",
            ),
            mapped_layers=(BenchmarkLayer.DATA, BenchmarkLayer.CALIBRATION_RESEARCH),
            runtime_notes="Offline-cache-only; no downloader is introduced.",
        ),
        SourceEntry(
            source_id="polymarket_data",
            name="Polymarket_data research dataset",
            repository_url="https://github.com/SII-WANGZJ/Polymarket_data",
            homepage_url="https://huggingface.co/datasets/SII-WANGZJ/Polymarket_data",
            classification=SourceClassification.OFFLINE_CACHE_ONLY,
            provenance="Large Polymarket dataset with blockchain-derived trades, market metadata, and research tables.",
            license_name="MIT for code; Hugging Face dataset terms and source data terms must be reviewed",
            license_caveat="Dataset is too large for repo storage and must remain external/offline-cache referenced.",
            data_caveats=(
                "Hundreds of millions of rows; local subsets only for smoke tests.",
                "Use market/user/trade tables for research, not live decisions.",
            ),
            requires_network=False,
            allowed_uses=(
                "Offline manifest inspection.",
                "Reference schema for unified YES perspective research.",
                "Market microstructure analysis inputs.",
            ),
            forbidden_uses=(
                "committing downloaded parquet archives",
                "live order placement",
                "wallet signing",
                "wallet mirroring",
            ),
            mapped_layers=(BenchmarkLayer.DATA, BenchmarkLayer.CALIBRATION_RESEARCH),
            runtime_notes="Offline-cache-only; no Hugging Face download is introduced.",
        ),
        SourceEntry(
            source_id="polymarket_cli_public",
            name="Polymarket CLI public-command reference",
            repository_url="https://github.com/Polymarket/polymarket-cli",
            classification=SourceClassification.REFERENCE_ONLY,
            provenance="CLI benchmark for separating public inspection commands from wallet/order commands.",
            license_name="Repository license must be reviewed before reuse",
            license_caveat="Use as boundary reference only; do not vendor CLI behavior.",
            data_caveats=(
                "CLI-style tools can hide authority escalation if not explicitly classified.",
                "Public inspection ideas belong behind read-only registry checks.",
            ),
            requires_network=True,
            live_capable_package=True,
            allowed_uses=(
                "Command taxonomy reference.",
                "Read-only operator report inspiration.",
            ),
            forbidden_uses=(
                "wallet signing",
                "live order placement",
                "order cancellation",
                "wallet mirroring",
                "copy trading",
            ),
            mapped_layers=(BenchmarkLayer.DATA, BenchmarkLayer.OPERATOR_REPORT),
            runtime_notes="Reference-only; no CLI dependency or commands are introduced.",
        ),
    ]


def _write_report(root: Path, payload: dict[str, Any]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "latest_source_registry.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    lines = [
        "# Source Registry Report",
        "",
        "Read-only external-source registry. No live trading, keys, wallets, or signing.",
        "",
        f"Status: {payload['status']}",
        f"Sources: {payload['sources_count']}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
        f"Execution authority added: {payload['execution_authority_added']}",
        "",
        "## Sources",
    ]
    for source in payload["sources"]:
        lines.append(
            "- {source_id}: {classification} read_only={read_only} live_capable_package={live_capable_package}".format(
                **source
            )
        )
    (root / "latest_source_registry.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
