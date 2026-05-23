from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from quant_os.data.source_models import SourceClassification, SourceEntry
from quant_os.data.source_registry import build_source_registry_report, default_source_registry
from quant_os.research.benchmark_sources.pmxt_manifest import summarize_pmxt_manifest
from quant_os.research.benchmark_sources.polymarket_public import inspect_polymarket_public
from quant_os.research.benchmark_sources.reference_datasets import summarize_reference_datasets
from quant_os.research.benchmark_sources.yahoo_reference import inspect_yahoo_reference
from quant_os.research.lane_benchmark_report import write_lane_benchmark_report

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "benchmark_sources"


def test_source_registry_entries_validate_and_preserve_read_only_safety() -> None:
    registry = default_source_registry()

    assert len(registry.entries) >= 7
    assert registry.by_id("yfinance").classification == SourceClassification.RUNTIME_SAFE
    assert registry.by_id("openbb").classification == SourceClassification.REFERENCE_ONLY
    assert registry.by_id("pmxt_orderbook_archives").classification == (
        SourceClassification.OFFLINE_CACHE_ONLY
    )

    for entry in registry.entries:
        assert entry.read_only is True
        assert entry.execution_authority == "none"
        assert entry.requires_wallet is False
        assert entry.signing_required is False


def test_source_model_rejects_execution_authority() -> None:
    with pytest.raises(ValueError):
        SourceEntry(
            source_id="unsafe_live_source",
            name="Unsafe Live Source",
            repository_url="https://example.test/live",
            classification=SourceClassification.RUNTIME_SAFE,
            provenance="negative test",
            license_name="unknown",
            license_caveat="negative test",
            data_caveats=("negative test",),
            requires_network=True,
            requires_keys=True,
            requires_wallet=True,
            signing_required=True,
            live_capable_package=True,
            execution_authority="order_placement",
            allowed_uses=("none",),
            forbidden_uses=("live order placement",),
            mapped_layers=("data_layer",),
        )


def test_live_capable_sources_are_labeled_but_not_authorized() -> None:
    registry = default_source_registry()
    live_capable_ids = {entry.source_id for entry in registry.entries if entry.live_capable_package}

    assert {"py_clob_client_public", "pmxt_orderbook_archives", "polymarket_cli_public"} <= (
        live_capable_ids
    )
    for source_id in live_capable_ids:
        entry = registry.by_id(source_id)
        assert entry.execution_authority == "none"
        assert "wallet signing" in " ".join(entry.forbidden_uses).lower()


def test_optional_imports_fail_gracefully_and_fixtures_are_deterministic() -> None:
    yahoo = inspect_yahoo_reference(
        fixture_path=FIXTURE_ROOT / "yahoo_ohlcv.csv",
        optional_import="definitely_missing_yfinance_package",
    )
    polymarket = inspect_polymarket_public(
        manifest_path=FIXTURE_ROOT / "polymarket_public_snapshot.json",
        optional_import="definitely_missing_py_clob_client_package",
    )

    assert yahoo["optional_import_available"] is False
    assert yahoo["fixture"]["rows"] == 3
    assert yahoo["fixture"]["symbols"] == ["QQQ", "SPY"]
    assert polymarket["optional_import_available"] is False
    assert polymarket["manifest"]["markets"] == 1
    assert polymarket["manifest"]["orderbooks"] == 1
    assert polymarket["manifest"]["trades"] == 1
    assert polymarket["execution_authority_added"] is False


def test_pmxt_and_reference_dataset_manifest_readers_are_local_only() -> None:
    pmxt = summarize_pmxt_manifest(FIXTURE_ROOT / "pmxt_manifest.json")
    datasets = summarize_reference_datasets(FIXTURE_ROOT / "reference_datasets_manifest.json")

    assert pmxt["status"] == "PASS"
    assert pmxt["source_id"] == "pmxt_orderbook_archives"
    assert pmxt["internet_required"] is False
    assert pmxt["api_key_required"] is False
    assert pmxt["hosted_api_used"] is False
    assert pmxt["credential_sources_used"] == []
    assert pmxt["execution_authority_added"] is False
    assert "submitOrder" in pmxt["forbidden_surfaces"]
    assert pmxt["files_by_kind"] == {"market": 1, "orderbook": 1}
    assert pmxt["orderbook_rows"] == 12
    assert pmxt["proof_grade_ready"] is False
    assert "PMXT_ORDERBOOK_ROWS_BELOW_PROOF_GRADE_MINIMUM" in pmxt["proof_grade_blockers"]
    assert pmxt["depth_ready_orderbook_files"] == ["cache/pmxt/orderbooks/sample.parquet"]
    assert datasets["status"] == "PASS"
    assert datasets["internet_required"] is False
    assert datasets["datasets_by_source"] == {
        "polymarket_data": 1,
        "prediction_market_analysis": 1,
    }


def test_pmxt_manifest_blocks_auth_paid_cookie_and_trading_surfaces(local_project: Path) -> None:
    manifest = local_project / "unsafe_pmxt_manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "api_key_required": True,
                "hosted_api_used": True,
                "paid_api_used": True,
                "browser_cookies_used": True,
                "auth_required": True,
                "signing_required": True,
                "credential_sources_used": ["PMXT_API_KEY"],
                "surfaces_used": ["fetchOrderBook", "submitOrder", "fetchBalance"],
                "files": [
                    {
                        "kind": "orderbook",
                        "path": "cache/pmxt/orderbooks/unsafe.parquet",
                        "rows": 2000,
                        "columns": [
                            "market_id",
                            "token_id",
                            "timestamp",
                            "bid_price",
                            "ask_price",
                            "bid_size",
                            "ask_size",
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    payload = summarize_pmxt_manifest(manifest)

    assert payload["status"] == "WARN"
    assert payload["api_key_required"] is True
    assert payload["hosted_api_used"] is True
    assert payload["paid_api_used"] is True
    assert payload["browser_cookies_used"] is True
    assert payload["credential_sources_used"] == ["PMXT_API_KEY"]
    assert payload["manifest_forbidden_surfaces_used"] == ["fetchBalance", "submitOrder"]
    assert payload["proof_grade_ready"] is False
    assert "PMXT_MANIFEST_API_KEY_REQUIRED_BLOCKED" in payload["proof_grade_blockers"]
    assert "PMXT_MANIFEST_FORBIDDEN_SURFACES_USED" in payload["proof_grade_blockers"]


def test_pmxt_orderbook_sample_requires_public_network_flag() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "scripts/data/pmxt_orderbook_sample.py"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)

    assert payload["status"] == "PUBLIC_NETWORK_NOT_ENABLED"
    assert payload["network_used"] is False
    assert payload["downloaded"] is False


def test_source_registry_report_writes_deterministic_payload(local_project: Path) -> None:
    payload = build_source_registry_report(output_root=local_project, write=True)

    assert payload["status"] == "PASS"
    assert payload["live_trading_enabled"] is False
    assert payload["execution_authority_added"] is False
    assert payload["sources_count"] >= 7
    assert (
        local_project
        / "reports"
        / "external_benchmarks"
        / "source_registry"
        / "latest_source_registry.json"
    ).exists()


def test_lane_benchmark_report_uses_fixtures_and_stays_conservative(
    local_project: Path,
) -> None:
    payload = write_lane_benchmark_report(
        output_root=local_project,
        yahoo_fixture=FIXTURE_ROOT / "yahoo_ohlcv.csv",
        polymarket_fixture=FIXTURE_ROOT / "polymarket_public_snapshot.json",
        pmxt_manifest=FIXTURE_ROOT / "pmxt_manifest.json",
        reference_datasets_manifest=FIXTURE_ROOT / "reference_datasets_manifest.json",
    )

    assert payload["status"] == "PASS"
    assert payload["live_trading_enabled"] is False
    assert payload["prediction_market_execution_authority_added"] is False
    assert payload["recommendation"]["staged_order"] == (
        "prediction-market-read-only-research-first"
    )
    assert payload["top_implementation_priorities"] == [
        "Normalize read-only external source provenance before adding more strategy code.",
        "Use local manifests and offline caches to evaluate prediction-market data quality.",
        "Improve event-driven replay realism and walk-forward robustness before any new live gate.",
    ]
    assert (
        local_project
        / "reports"
        / "external_benchmarks"
        / "lane_benchmark"
        / "latest_external_benchmark_report.json"
    ).exists()


def test_cli_commands_do_not_require_network_or_keys(local_project: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env = {
        **os.environ,
        "PYTHONPATH": str(repo_root / "src"),
    }
    commands = [
        [sys.executable, "-m", "quant_os.cli", "data", "source-registry-report"],
        [sys.executable, "-m", "quant_os.cli", "research", "external-benchmark-report"],
    ]

    for command in commands:
        result = subprocess.run(
            command,
            cwd=local_project,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        assert "live_trading_enabled" in result.stdout
        assert "False" in result.stdout


def test_lane_report_json_is_deterministic(local_project: Path) -> None:
    first = write_lane_benchmark_report(
        output_root=local_project,
        yahoo_fixture=FIXTURE_ROOT / "yahoo_ohlcv.csv",
        polymarket_fixture=FIXTURE_ROOT / "polymarket_public_snapshot.json",
        pmxt_manifest=FIXTURE_ROOT / "pmxt_manifest.json",
        reference_datasets_manifest=FIXTURE_ROOT / "reference_datasets_manifest.json",
    )
    second = write_lane_benchmark_report(
        output_root=local_project,
        yahoo_fixture=FIXTURE_ROOT / "yahoo_ohlcv.csv",
        polymarket_fixture=FIXTURE_ROOT / "polymarket_public_snapshot.json",
        pmxt_manifest=FIXTURE_ROOT / "pmxt_manifest.json",
        reference_datasets_manifest=FIXTURE_ROOT / "reference_datasets_manifest.json",
    )

    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
