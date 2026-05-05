from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

MARKET_FIXTURE = (
    Path(__file__).parent / "fixtures" / "prediction_markets" / "polymarket_markets_sample.json"
)
WALLET_FIXTURE = (
    Path(__file__).parent
    / "fixtures"
    / "prediction_markets"
    / "polymarket_wallet_activity_sample.json"
)
AS_OF = datetime(2026, 5, 5, 12, 0, tzinfo=UTC)


def test_polymarket_fixture_normalizes_deterministically_and_preserves_provenance() -> None:
    from quant_os.data.prediction_markets.normalization import load_prediction_market_records
    from quant_os.data.prediction_markets.schema import MarketLifecycleStatus

    first = load_prediction_market_records(MARKET_FIXTURE)
    second = load_prediction_market_records(MARKET_FIXTURE)

    assert [market.market_id for market in first] == [market.market_id for market in second]
    clean = next(market for market in first if market.market_id == "pm-clean-1")
    assert clean.source == "polymarket"
    assert clean.source_mode == "fixture"
    assert clean.condition_id == "0xcleancondition"
    assert clean.status == MarketLifecycleStatus.OPEN
    assert [outcome.contract_name for outcome in clean.outcomes] == ["YES", "NO"]
    assert [outcome.probability for outcome in clean.outcomes] == [0.42, 0.58]
    assert clean.join_keys == {
        "source": "polymarket",
        "market_id": "pm-clean-1",
        "condition_id": "0xcleancondition",
    }
    assert clean.provenance["source_path"].endswith("polymarket_markets_sample.json")

    resolved = next(market for market in first if market.market_id == "pm-resolved-1")
    assert resolved.status == MarketLifecycleStatus.RESOLVED
    assert [outcome.winning for outcome in resolved.outcomes] == [True, False]


def test_capture_provider_is_read_only_absent_safe_and_offline(tmp_path: Path) -> None:
    from quant_os.data.providers.polymarket_capture import capture_polymarket_markets
    from quant_os.data.providers.polymarket_public_provider import PolymarketPublicProvider

    provider = PolymarketPublicProvider(enabled=True)
    capabilities = provider.capabilities()
    assert capabilities["supports_execution"] is False
    assert capabilities["supports_authentication"] is False
    assert capabilities["requires_private_keys"] is False
    assert capabilities["network_default"] == "disabled"
    availability = provider.availability()
    assert availability.requires_keys is False
    assert availability.requires_network is True

    blocked = capture_polymarket_markets(
        output_dir=tmp_path,
        allow_network_fetch=True,
        explicit_network_fetch=False,
    )
    assert blocked["status"] == "BLOCKED"
    assert "NETWORK_FETCH_REQUIRES_EXPLICIT_FLAG" in blocked["blockers"]
    assert blocked["network_fetch_allowed"] is False

    captured = capture_polymarket_markets(fixture_path=MARKET_FIXTURE, output_dir=tmp_path)
    assert captured["status"] == "PASS"
    assert captured["source_mode"] == "fixture"
    assert captured["market_count"] == 5
    assert Path(captured["file_path"]).exists()
    saved = json.loads(Path(captured["file_path"]).read_text("utf-8"))
    assert saved["live_trading_enabled"] is False
    assert saved["execution_enabled"] is False


def test_market_quality_classifies_stale_thin_ambiguous_and_missing_markets() -> None:
    from quant_os.data.prediction_markets.normalization import load_prediction_market_records
    from quant_os.research.prediction_markets.quality import evaluate_market_quality

    records = load_prediction_market_records(MARKET_FIXTURE)
    report = evaluate_market_quality(records, as_of=AS_OF)
    by_market = {item["market_id"]: item for item in report["markets"]}

    assert by_market["pm-clean-1"]["research_worthiness"] == "RESEARCHABLE"
    assert by_market["pm-stale-thin-1"]["research_worthiness"] == "LOW_PRIORITY"
    assert {"STALE_MARKET", "THIN_LIQUIDITY", "LOW_VOLUME"}.issubset(
        set(by_market["pm-stale-thin-1"]["quality_flags"])
    )
    assert by_market["pm-ambiguous-1"]["research_worthiness"] == "AMBIGUOUS_MARKET_STRUCTURE"
    assert "NON_BINARY_OUTCOMES" in by_market["pm-ambiguous-1"]["quality_flags"]
    assert by_market["pm-missing-critical-1"]["research_worthiness"] == "DO_NOT_RESEARCH_YET"
    assert "MISSING_QUESTION" in by_market["pm-missing-critical-1"]["quality_flags"]
    assert report["summary"]["researchable_count"] == 1
    assert report["live_promotion_status"] == "LIVE_BLOCKED"


def test_prediction_market_reports_emit_json_and_markdown(local_project: Path) -> None:
    from quant_os.research.prediction_markets.quality_report import (
        write_market_inventory_report,
        write_market_quality_report,
        write_research_priority_report,
    )

    quality = write_market_quality_report(
        fixture_path=MARKET_FIXTURE,
        output_root=local_project,
        as_of=AS_OF,
    )
    inventory = write_market_inventory_report(
        fixture_path=MARKET_FIXTURE, output_root=local_project
    )
    priority = write_research_priority_report(
        fixture_path=MARKET_FIXTURE,
        output_root=local_project,
        as_of=AS_OF,
    )

    assert quality["report_paths"]["json"].endswith("latest_market_quality.json")
    assert inventory["report_paths"]["markdown"].endswith("latest_market_inventory.md")
    assert priority["report_paths"]["json"].endswith("latest_research_priority.json")
    for payload in (quality, inventory, priority):
        assert payload["source_mode"] == "fixture"
        assert payload["live_trading_enabled"] is False
        assert Path(payload["report_paths"]["json"]).exists()
        assert Path(payload["report_paths"]["markdown"]).exists()

    markdown = Path(priority["report_paths"]["markdown"]).read_text("utf-8")
    assert "Research-only" in markdown
    assert "Observed facts" in markdown
    assert "Inferred patterns" in markdown
    assert "Unknowns" in markdown


def test_wallet_report_is_observational_and_heuristic(local_project: Path) -> None:
    from quant_os.research.prediction_markets.wallet_reports import write_wallet_research_report

    report = write_wallet_research_report(
        activity_fixture_path=WALLET_FIXTURE,
        market_fixture_path=MARKET_FIXTURE,
        output_root=local_project,
    )

    assert report["source_mode"] == "fixture"
    assert report["observed_facts"]["wallet_count"] == 3
    assert report["observed_facts"]["activity_count"] == 4
    assert report["execution_authority"] == "NONE"
    assert report["copy_trading_enabled"] is False
    assert any(
        item["label"] == "POSSIBLE_COORDINATION_CLUSTER"
        and item["confidence_limit"] == "HEURISTIC_NOT_CERTAINTY"
        for item in report["inferred_patterns"]
    )
    assert "profitability is not inferred from wallet activity" in " ".join(report["unknowns"])
    assert Path(report["report_paths"]["json"]).exists()
    assert Path(report["report_paths"]["markdown"]).exists()


def test_reference_and_resolution_hooks_keep_future_labels_offline_and_joinable() -> None:
    from quant_os.data.prediction_markets.normalization import load_prediction_market_records
    from quant_os.research.prediction_markets.reference_context import build_reference_context_hooks
    from quant_os.research.prediction_markets.resolution_hooks import build_resolution_label_hooks

    records = load_prediction_market_records(MARKET_FIXTURE)
    reference_hooks = build_reference_context_hooks(records)
    resolution_hooks = build_resolution_label_hooks(records)

    clean_reference = next(item for item in reference_hooks if item["market_id"] == "pm-clean-1")
    assert clean_reference["reference_required"] is True
    assert clean_reference["internet_required"] is False
    assert clean_reference["join_keys"]["condition_id"] == "0xcleancondition"

    resolved_hook = next(item for item in resolution_hooks if item["market_id"] == "pm-resolved-1")
    assert resolved_hook["resolution_status"] == "RESOLVED"
    assert resolved_hook["winning_outcome"] == "YES"
    assert resolved_hook["label_ready"] is True


def test_prediction_market_spine_exposes_no_execution_or_wallet_mirroring_path() -> None:
    from quant_os.data.providers.polymarket_public_provider import PolymarketPublicProvider
    from quant_os.research.prediction_markets.wallets import WALLET_RESEARCH_SAFETY

    provider = PolymarketPublicProvider(enabled=True)
    assert provider.capabilities()["supports_execution"] is False
    assert provider.capabilities()["read_only"] is True
    assert "EXECUTION_NOT_SUPPORTED" in provider.capabilities()["safety_guards"]
    assert WALLET_RESEARCH_SAFETY["copy_trading_enabled"] is False
    assert WALLET_RESEARCH_SAFETY["execution_authority"] == "NONE"
