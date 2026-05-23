from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

NOW = "2026-05-17T17:30:00Z"
FRESH_ORDERBOOK_TS = "2026-05-17T17:29:00Z"
FORECAST_TS = "2026-05-17T17:24:51Z"
RESOLUTION_TS = "2026-05-19T14:00:00Z"


def _market(**overrides: object) -> dict[str, object]:
    market = {
        "candidate_id": "pm_weather_forecast_market_mismatch",
        "venue": "kalshi",
        "ticker": "KXHIGHNY-26MAY18-B83.5",
        "event_ticker": "KXHIGHNY-26MAY18",
        "series_ticker": "KXHIGHNY",
        "title": "Will the high temp in NYC be 83-84 deg on May 18, 2026?",
        "status": "active",
        "open_time": "2026-05-17T14:00:00Z",
        "close_time": "2026-05-19T04:59:00Z",
        "resolution_ts": RESOLUTION_TS,
        "location": "Central Park, New York",
        "weather_variable": "temperature_max_f",
        "threshold_bucket": "83_to_84_f_inclusive",
        "floor_strike": 83,
        "cap_strike": 84,
        "strike_type": "between",
        "yes_bid": 0.25,
        "yes_ask": 0.27,
        "no_bid": 0.73,
        "no_ask": 0.75,
        "spread": 0.02,
        "liquidity": 15.0,
        "volume": 251.91,
        "orderbook_available": True,
        "orderbook_ts": FRESH_ORDERBOOK_TS,
        "source_url": "https://external-api.kalshi.com/trade-api/v2/markets?series_ticker=KXHIGHNY&status=open",
        "orderbook_url": "https://external-api.kalshi.com/trade-api/v2/markets/KXHIGHNY-26MAY18-B83.5/orderbook",
        "settlement_rules": "NWS Daily Climatological Report for Central Park, New York.",
    }
    market.update(overrides)
    return market


def _forecast(**overrides: object) -> dict[str, object]:
    forecast = {
        "status": "CURRENT_FORECAST_MATCHED",
        "source_id": "nws_api",
        "source_kind": "forecast",
        "forecast_issue_ts": FORECAST_TS,
        "forecast_valid_ts": "2026-05-18T14:00:00-04:00",
        "known_at_ts": FORECAST_TS,
        "forecast_value": 83,
        "forecast_bucket": "83_to_84_f_inclusive",
        "bucket_match": True,
        "resolution_ts": RESOLUTION_TS,
        "evidence_hash": "forecast-hash",
    }
    forecast.update(overrides)
    return forecast


def _write_json(root: Path, relative: str, payload: dict[str, object]) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _seed_structural_reports(root: Path, *, current_market_status: str) -> None:
    required = [
        "reports/profit_campaign/latest_profit_campaign.json",
        "reports/sequence52/weather_resolved_dataset/latest_weather_resolved_dataset.json",
        "reports/sequence52/weather_batch_paper_proving/latest_weather_batch_paper_proving.json",
    ]
    for path in required:
        _write_json(root, path, {"status": "SEEDED"})
    _write_json(
        root,
        "reports/first_dollar_preflight/provenance/latest_provenance_audit.json",
        {"status": "PROVENANCE_AUDIT_PASSED"},
    )
    _write_json(
        root,
        "reports/first_dollar_preflight/provenance_repair/latest_provenance_repair.json",
        {"status": "PROVENANCE_REPAIR_PASSED"},
    )
    _write_json(
        root,
        "reports/first_dollar_preflight/security/latest_first_dollar_security_scan.json",
        {"status": "FIRST_DOLLAR_SECURITY_SCAN_PASSED"},
    )
    _write_json(
        root,
        "reports/canary_readiness/final/latest_tiny_canary_readiness.json",
        {"status": "TINY_CANARY_READY_FOR_MANUAL_ARMING"},
    )
    _write_json(
        root,
        "reports/canary_readiness/manual_packet/latest_manual_canary_packet.json",
        {"status": "MANUAL_CANARY_PACKET_READY"},
    )
    _write_json(
        root,
        "reports/first_dollar_preflight/current_market/latest_current_market_eligibility.json",
        {"status": current_market_status},
    )
    if current_market_status == "CURRENT_MARKET_ELIGIBILITY_PASSED":
        _write_json(
            root,
            "reports/first_dollar_preflight/current_forecast/latest_current_forecast.json",
            {"status": "CURRENT_FORECAST_MATCHED"},
        )
    _write_json(
        root,
        "reports/first_dollar_preflight/order_preview/latest_order_preview.json",
        {"status": "NO_TRANSMIT_ORDER_PREVIEW_READY"},
    )
    _write_json(
        root,
        "reports/first_dollar_preflight/human_review/latest_human_review.json",
        {"status": "HUMAN_REVIEW_PACKET_READY"},
    )


def test_sequence57_current_market_discovery_is_public_get_only(local_project: Path) -> None:
    from quant_os.data.weather.current_weather_market_discovery import (
        evaluate_current_weather_market_discovery,
    )

    payload = evaluate_current_weather_market_discovery(
        output_root=local_project,
        markets_payload={"markets": [_market()]},
        series_payload={"series": {"ticker": "KXHIGHNY", "title": "Highest temperature in NYC"}},
        orderbook_payloads={"KXHIGHNY-26MAY18-B83.5": {"orderbook_fp": {"yes": [["0.25", "3.00"]]}}},
        captured_at=NOW,
    )

    assert payload["status"] == "CURRENT_MARKET_FOUND"
    assert payload["public_read_only"] is True
    assert payload["authenticated_endpoint_called"] is False
    assert payload["request_methods"] == ["GET"]
    assert not any("/portfolio/orders" in url for url in payload["source_urls"])
    assert payload["api_keys_loaded"] is False
    assert payload["private_keys_loaded"] is False
    assert (local_project / "reports/first_dollar_preflight/current_market_discovery/latest_current_market_discovery.json").exists()


def test_sequence57_no_current_market_keeps_structural_no_current_status(local_project: Path) -> None:
    from quant_os.data.weather.current_weather_market_discovery import (
        evaluate_current_weather_market_discovery,
    )
    from quant_os.readiness.current_market_eligibility import (
        write_current_market_eligibility_report,
    )
    from quant_os.readiness.first_dollar_preflight import write_first_dollar_preflight_report

    discovery = evaluate_current_weather_market_discovery(
        output_root=local_project,
        markets_payload={"markets": []},
        captured_at=NOW,
    )
    eligibility = write_current_market_eligibility_report(output_root=local_project)
    _seed_structural_reports(local_project, current_market_status=eligibility["status"])
    final = write_first_dollar_preflight_report(output_root=local_project)

    assert discovery["status"] == "NO_CURRENT_ELIGIBLE_MARKET"
    assert eligibility["status"] == "CURRENT_MARKET_ELIGIBILITY_NO_CURRENT_MARKET"
    assert final["status"] == "FIRST_DOLLAR_PREFLIGHT_STRUCTURALLY_READY_NO_CURRENT_MARKET"


def test_sequence57_forecast_matching_blocks_realized_values_as_forecasts(
    local_project: Path,
) -> None:
    from quant_os.data.weather.current_weather_forecast_match import evaluate_current_forecast_match

    payload = evaluate_current_forecast_match(
        output_root=local_project,
        market=_market(),
        forecast_payload=_forecast(source_kind="realized_observation"),
        known_at_ts=FORECAST_TS,
        orderbook_ts=FRESH_ORDERBOOK_TS,
    )

    assert payload["status"] == "CURRENT_FORECAST_BLOCKED"
    assert "REALIZED_WEATHER_FORBIDDEN_AS_FORECAST" in payload["blockers"]


def test_sequence57_forecast_matching_blocks_lookahead(local_project: Path) -> None:
    from quant_os.data.weather.current_weather_forecast_match import evaluate_current_forecast_match

    payload = evaluate_current_forecast_match(
        output_root=local_project,
        market=_market(),
        forecast_payload=_forecast(forecast_issue_ts="2026-05-17T17:31:00Z"),
        known_at_ts="2026-05-17T17:31:00Z",
        orderbook_ts=FRESH_ORDERBOOK_TS,
    )

    assert payload["status"] == "LOOKAHEAD_RISK_BLOCKED"
    assert "FORECAST_KNOWN_AFTER_ORDERBOOK" in payload["blockers"]


def test_sequence57_forecast_matching_blocks_ambiguous_location_mapping(
    local_project: Path,
) -> None:
    from quant_os.data.weather.current_weather_forecast_match import evaluate_current_forecast_match

    payload = evaluate_current_forecast_match(
        output_root=local_project,
        market=_market(location="London, United Kingdom", ticker="KXHIGHLON-26MAY18-T84"),
        forecast_payload=_forecast(),
        known_at_ts=FORECAST_TS,
        orderbook_ts=FRESH_ORDERBOOK_TS,
    )

    assert payload["status"] == "FORECAST_MAPPING_AMBIGUOUS"
    assert "FORECAST_SOURCE_LOCATION_UNSUPPORTED" in payload["blockers"]


def test_sequence57_forecast_matching_scans_supported_locations_and_prefers_price_discipline(
    local_project: Path,
) -> None:
    from quant_os.data.weather.current_weather_forecast_match import evaluate_current_forecast_match

    _write_json(
        local_project,
        "reports/first_dollar_preflight/current_market_discovery/latest_current_market_discovery.json",
        {
            "candidates": [
                _market(
                    ticker="KXHIGHNY-26MAY18-T60",
                    title="Will the high temp in NYC be <60 deg on May 18, 2026?",
                    threshold_bucket="less_than_60_f",
                    floor_strike=None,
                    cap_strike=60,
                    strike_type="less",
                    yes_ask=0.78,
                    yes_bid=0.75,
                    no_bid=0.22,
                    no_ask=0.25,
                ),
                _market(
                    ticker="KXHIGHMIA-26MAY18-T84",
                    event_ticker="KXHIGHMIA-26MAY18",
                    series_ticker="KXHIGHMIA",
                    title="Will the high temp in Miami be <84 deg on May 18, 2026?",
                    location="Miami, Florida",
                    threshold_bucket="less_than_84_f",
                    floor_strike=None,
                    cap_strike=84,
                    strike_type="less",
                    yes_ask=0.31,
                    yes_bid=0.29,
                    no_bid=0.69,
                    no_ask=0.71,
                ),
            ]
        },
    )

    payload = evaluate_current_forecast_match(
        output_root=local_project,
        forecast_payloads_by_location={
            "Central Park, New York": _forecast(forecast_value=58),
            "Miami, Florida": _forecast(forecast_value=83),
        },
        known_at_ts=FORECAST_TS,
        orderbook_ts=FRESH_ORDERBOOK_TS,
    )

    assert payload["status"] == "CURRENT_FORECAST_MATCHED"
    assert payload["match_count"] == 2
    assert payload["market"]["location"] == "Miami, Florida"
    assert payload["market"]["yes_ask"] == 0.31


def test_sequence57_eligibility_blocks_closed_markets(local_project: Path) -> None:
    from quant_os.readiness.current_market_eligibility import evaluate_current_market_eligibility

    payload = evaluate_current_market_eligibility(
        output_root=local_project,
        current_public_market=_market(status="closed"),
        forecast_evidence=_forecast(),
        now_ts=NOW,
    )

    assert payload["status"] == "CURRENT_MARKET_ELIGIBILITY_BLOCKED"
    assert "MARKET_NOT_OPEN" in payload["blockers"]


def test_sequence57_eligibility_blocks_wide_spreads(local_project: Path) -> None:
    from quant_os.readiness.current_market_eligibility import evaluate_current_market_eligibility

    payload = evaluate_current_market_eligibility(
        output_root=local_project,
        current_public_market=_market(spread=0.20),
        forecast_evidence=_forecast(),
        now_ts=NOW,
    )

    assert payload["status"] == "CURRENT_MARKET_ELIGIBILITY_BLOCKED"
    assert "SPREAD_ABOVE_CAP" in payload["blockers"]


def test_sequence57_eligibility_requires_public_l2_orderbook(local_project: Path) -> None:
    from quant_os.readiness.current_market_eligibility import evaluate_current_market_eligibility

    payload = evaluate_current_market_eligibility(
        output_root=local_project,
        current_public_market=_market(orderbook_available=False),
        forecast_evidence=_forecast(),
        now_ts=NOW,
    )

    assert payload["status"] == "CURRENT_MARKET_ELIGIBILITY_BLOCKED"
    assert "ORDERBOOK_PUBLIC_DATA_MISSING" in payload["blockers"]


def test_sequence57_eligibility_blocks_stale_data(local_project: Path) -> None:
    from quant_os.readiness.current_market_eligibility import evaluate_current_market_eligibility

    stale_ts = (datetime.fromisoformat(NOW.replace("Z", "+00:00")) - timedelta(hours=3)).isoformat()
    payload = evaluate_current_market_eligibility(
        output_root=local_project,
        current_public_market=_market(orderbook_ts=stale_ts),
        forecast_evidence=_forecast(),
        now_ts=NOW,
    )

    assert payload["status"] == "CURRENT_MARKET_ELIGIBILITY_BLOCKED"
    assert "ORDERBOOK_DATA_STALE" in payload["blockers"]


def test_sequence57_eligibility_blocks_missing_forecast_evidence(local_project: Path) -> None:
    from quant_os.readiness.current_market_eligibility import evaluate_current_market_eligibility

    payload = evaluate_current_market_eligibility(
        output_root=local_project,
        current_public_market=_market(),
        forecast_evidence=None,
        now_ts=NOW,
    )

    assert payload["status"] == "CURRENT_MARKET_ELIGIBILITY_BLOCKED"
    assert "CURRENT_FORECAST_MATCHED_MISSING" in payload["blockers"]


def test_sequence57_no_transmit_order_preview_requires_current_eligibility(
    local_project: Path,
) -> None:
    from quant_os.readiness.first_dollar_order_preview import build_first_dollar_order_preview

    _write_json(
        local_project,
        "reports/first_dollar_preflight/current_market/latest_current_market_eligibility.json",
        {"status": "CURRENT_MARKET_ELIGIBILITY_BLOCKED"},
    )

    payload = build_first_dollar_order_preview(output_root=local_project)

    assert payload["status"] == "NO_TRANSMIT_ORDER_PREVIEW_BLOCKED"
    assert "CURRENT_MARKET_ELIGIBILITY_PASSED_MISSING" in payload["blockers"]


def test_sequence57_order_preview_contains_no_signed_headers_private_key_or_post(
    local_project: Path,
) -> None:
    from quant_os.readiness.current_market_eligibility import evaluate_current_market_eligibility
    from quant_os.readiness.first_dollar_order_preview import build_first_dollar_order_preview

    eligibility = evaluate_current_market_eligibility(
        output_root=local_project,
        current_public_market=_market(),
        forecast_evidence=_forecast(),
        now_ts=NOW,
    )
    assert eligibility["status"] == "CURRENT_MARKET_ELIGIBILITY_PASSED"
    payload = build_first_dollar_order_preview(output_root=local_project)
    text = json.dumps(payload, sort_keys=True)

    assert payload["status"] == "NO_TRANSMIT_ORDER_PREVIEW_READY"
    assert payload["dry_run_only"] is True
    assert payload["no_send"] is True
    assert payload["contains_private_key_path"] is False
    assert "KALSHI-ACCESS-SIGNATURE" not in text
    assert "requests.post" not in text
    assert "/portfolio/orders" not in text


def test_sequence57_human_review_packet_requires_explicit_manual_confirmations(
    local_project: Path,
) -> None:
    from quant_os.readiness.first_dollar_human_review import build_first_dollar_human_review

    payload = build_first_dollar_human_review(output_root=local_project)

    assert payload["status"] == "HUMAN_REVIEW_PACKET_READY"
    assert payload["human_confirmation_collected"] is False
    assert payload["separate_manual_action_required_for_first_dollar"] is True
    assert "This packet does not place or authorize an order." in payload["required_statements"]
    assert all(value is False for value in payload["confirmation_checkboxes"].values())


def test_sequence57_final_preflight_requires_current_market_eligibility(
    local_project: Path,
) -> None:
    from quant_os.readiness.first_dollar_preflight import write_first_dollar_preflight_report

    _seed_structural_reports(
        local_project,
        current_market_status="CURRENT_MARKET_ELIGIBILITY_BLOCKED",
    )
    payload = write_first_dollar_preflight_report(output_root=local_project)

    assert payload["status"] == "FIRST_DOLLAR_PREFLIGHT_BLOCKED_BY_CURRENT_MARKET"
    assert "CURRENT_MARKET_ELIGIBILITY_PASSED_MISSING" in payload["blockers"]


def test_sequence57_final_preflight_keeps_live_and_auth_disabled(local_project: Path) -> None:
    from quant_os.readiness.first_dollar_preflight import write_first_dollar_preflight_report

    _seed_structural_reports(local_project, current_market_status="CURRENT_MARKET_ELIGIBILITY_PASSED")
    payload = write_first_dollar_preflight_report(output_root=local_project)

    assert payload["status"] == "FIRST_DOLLAR_PREFLIGHT_READY"
    assert payload["live_trading_enabled"] is False
    assert payload["execution_authority"] == "NONE"
    assert payload["order_transmission_enabled"] is False
    assert payload["authenticated_requests_enabled"] is False
    assert payload["api_keys_loaded"] is False
    assert payload["private_keys_loaded"] is False
    assert payload["actual_order_count"] == 0
    assert payload["actual_cancel_count"] == 0


def test_sequence57_current_market_watcher_is_data_only(local_project: Path) -> None:
    from quant_os.autonomy.current_market_watch_plan import write_current_market_watch_plan

    payload = write_current_market_watch_plan(output_root=local_project)

    assert payload["status"] == "CURRENT_MARKET_WATCH_PLAN_READY"
    assert payload["data_only"] is True
    assert payload["credentials_required"] is False
    assert payload["order_transmission_enabled"] is False
    assert "python -m quant_os.cli data current-weather-market-discovery --public-network-ok" in payload[
        "exact_cli_command"
    ]


def test_sequence57_guard_live_and_freqtrade_validate_remain_dry_run_valid(
    local_project: Path,
) -> None:
    commands = [
        [sys.executable, "-m", "quant_os.cli", "guard-live"],
        [sys.executable, "-m", "quant_os.cli", "freqtrade", "generate-config"],
        [sys.executable, "-m", "quant_os.cli", "freqtrade", "validate"],
    ]
    for command in commands:
        result = subprocess.run(
            command,
            cwd=local_project,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr


def test_sequence57_cli_and_make_targets_are_fixture_safe(local_project: Path) -> None:
    commands = [
        [sys.executable, "-m", "quant_os.cli", "data", "current-weather-market-discovery"],
        [sys.executable, "-m", "quant_os.cli", "data", "current-weather-forecast-match"],
        [sys.executable, "-m", "quant_os.cli", "readiness", "current-market-eligibility"],
        [sys.executable, "-m", "quant_os.cli", "readiness", "first-dollar-order-preview"],
        [sys.executable, "-m", "quant_os.cli", "readiness", "first-dollar-human-review"],
        [sys.executable, "-m", "quant_os.cli", "readiness", "first-dollar-preflight"],
        [sys.executable, "-m", "quant_os.cli", "autonomy", "current-market-watch-plan"],
    ]
    for command in commands:
        result = subprocess.run(
            command,
            cwd=local_project,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        assert "live_trading_enabled" in result.stdout

    make_cmd = (Path(__file__).resolve().parents[1] / "make.cmd").read_text(encoding="utf-8")
    assert 'if "%TARGET%"=="sequence57-smoke"' in make_cmd
    assert 'if "%TARGET%"=="current-market-preflight-smoke"' in make_cmd
