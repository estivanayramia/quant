from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest


def _series_fixture() -> dict:
    return {
        "series": {
            "ticker": "KXHIGHNY",
            "title": "Highest temperature in NYC",
            "category": "Climate and Weather",
            "settlement_sources": [
                {
                    "name": "NWS Climatological Report",
                    "url": "https://forecast.weather.gov/product.php?site=OKX&product=CLI&issuedby=NYC",
                }
            ],
        }
    }


def _resolved_markets_fixture() -> dict:
    markets = []
    for day, result, value, yes_bid, yes_ask, low, high in [
        (12, "YES", "73", "0.9300", "0.9500", 73, 74),
        (13, "NO", "68", "0.0400", "0.0600", 72, 73),
        (14, "YES", "80", "0.8600", "0.8800", 80, 81),
    ]:
        markets.append(
            {
                "ticker": f"KXHIGHNY-26MAY{day}-B{low}.5",
                "event_ticker": f"KXHIGHNY-26MAY{day}",
                "title": f"Will the high temp in NYC be {low}-{high} deg on May {day}, 2026?",
                "status": "settled",
                "market_type": "binary",
                "strike_type": "between",
                "floor_strike": low,
                "cap_strike": high,
                "yes_bid_dollars": yes_bid,
                "yes_ask_dollars": yes_ask,
                "yes_bid_size_fp": "120.00",
                "yes_ask_size_fp": "140.00",
                "no_bid_dollars": f"{1 - float(yes_ask):.4f}",
                "no_ask_dollars": f"{1 - float(yes_bid):.4f}",
                "volume_fp": str(1000 + day),
                "open_interest_fp": str(800 + day),
                "open_time": f"2026-05-{day - 1:02d}T14:00:00Z",
                "close_time": f"2026-05-{day + 1:02d}T04:59:00Z",
                "expected_expiration_time": f"2026-05-{day + 1:02d}T14:00:00Z",
                "occurrence_datetime": f"2026-05-{day:02d}T14:00:00Z",
                "expiration_value": value,
                "result": result,
                "rules_primary": (
                    f"If the highest temperature recorded in Central Park, New York for May {day}, "
                    "2026 as reported by the National Weather Service's Climatological Report "
                    f"(Daily), is between {low}-{high} deg, then the market resolves to Yes."
                ),
            }
        )
    markets.append(
        {
            "ticker": "KXHIGHNY-26MAY15-T65",
            "event_ticker": "KXHIGHNY-26MAY15",
            "title": "Will the high temp in NYC be <65 deg on May 15, 2026?",
            "status": "closed",
            "market_type": "binary",
            "strike_type": "less",
            "cap_strike": 65,
            "yes_bid_dollars": "0.1200",
            "yes_ask_dollars": "0.1400",
            "yes_bid_size_fp": "55.00",
            "yes_ask_size_fp": "67.00",
            "volume_fp": "211.00",
            "open_interest_fp": "188.00",
            "open_time": "2026-05-14T14:00:00Z",
            "close_time": "2026-05-16T04:59:00Z",
            "expected_expiration_time": "2026-05-16T14:00:00Z",
            "occurrence_datetime": "2026-05-15T14:00:00Z",
            "expiration_value": "",
            "result": "",
            "rules_primary": (
                "If the highest temperature recorded in Central Park, New York for May 15, "
                "2026 as reported by the National Weather Service's Climatological Report "
                "(Daily), is less than 65 deg, then the market resolves to Yes."
            ),
        }
    )
    return {"markets": markets}


def _forecast_fixture() -> dict:
    periods = []
    for day, temps in [(12, [70, 73, 74]), (13, [67, 68, 69]), (14, [78, 80, 79])]:
        for hour, temp in enumerate(temps, start=13):
            periods.append(
                {
                    "startTime": f"2026-05-{day:02d}T{hour}:00:00-04:00",
                    "endTime": f"2026-05-{day:02d}T{hour + 1}:00:00-04:00",
                    "temperature": temp,
                    "temperatureUnit": "F",
                }
            )
    return {
        "properties": {
            "generatedAt": "2026-05-11T22:01:46+00:00",
            "updateTime": "2026-05-11T18:26:01+00:00",
            "periods": periods,
        }
    }


def _iem_mos_fixture() -> dict:
    rows = []
    for hour, temp in [
        ("2026-05-12T12:00:00.000", 70),
        ("2026-05-12T15:00:00.000", 73),
        ("2026-05-12T18:00:00.000", 74),
        ("2026-05-12T21:00:00.000", 72),
    ]:
        rows.append(
            {
                "model": "GFS",
                "station": "KNYC",
                "runtime_utc": "2026-05-11T12:00:00.000",
                "ftime_utc": hour,
                "tmp": temp,
            }
        )
    return {"data": rows}


def _orderbook_fixture() -> dict:
    return {
        "orderbooks": {
            "KXHIGHNY-26MAY12-B73.5": {
                "orderbook_fp": {
                    "yes_dollars": [["0.9200", "125.00"]],
                    "no_dollars": [["0.0500", "150.00"]],
                }
            },
            "KXHIGHNY-26MAY13-B72.5": {
                "orderbook_fp": {
                    "yes_dollars": [["0.0300", "120.00"]],
                    "no_dollars": [["0.9400", "160.00"]],
                }
            },
            "KXHIGHNY-26MAY14-B80.5": {
                "orderbook_fp": {
                    "yes_dollars": [["0.8500", "140.00"]],
                    "no_dollars": [["0.1200", "190.00"]],
                }
            },
        }
    }


def _label_payloads() -> dict[str, str]:
    return {
        "KXHIGHNY-26MAY12-B73.5": "CLIMATE REPORT\nMAXIMUM 73\nISSUED 1200 AM EDT MAY 13 2026\n",
        "KXHIGHNY-26MAY13-B72.5": "CLIMATE REPORT\nMAXIMUM 68\nISSUED 1200 AM EDT MAY 14 2026\n",
        "KXHIGHNY-26MAY14-B80.5": "CLIMATE REPORT\nMAXIMUM 80\nISSUED 1200 AM EDT MAY 15 2026\n",
        "KXHIGHNY-26MAY15-T65": "",
    }


def test_sequence52_weather_archive_source_policy_prefers_iem_and_blocks_open_meteo_for_profit() -> None:
    from quant_os.data.weather.weather_historical_forecast_archive import (
        evaluate_weather_historical_forecast_sources,
    )

    payload = evaluate_weather_historical_forecast_sources(campaign_context="profit_campaign")
    by_source = {item["source_id"]: item for item in payload["sources"]}

    assert payload["status"] == "WEATHER_ARCHIVE_SOURCE_POLICY_EVALUATED"
    assert by_source["iem_mos_historical_forecast"]["status"] == "WEATHER_ARCHIVE_SOURCE_ALLOWED"
    assert by_source["iem_mos_historical_forecast"]["auth_required"] is False
    assert by_source["iem_mos_historical_forecast"]["paid_required"] is False
    assert by_source["open_meteo_historical_forecast"]["status"] == "WEATHER_ARCHIVE_SOURCE_BLOCKED"
    assert by_source["open_meteo_historical_forecast"]["exact_reason"] == (
        "FREE_TIER_NON_COMMERCIAL_ONLY_FOR_PROFIT_CAMPAIGN"
    )


def test_sequence52_iem_mos_archive_preserves_issue_valid_and_known_at_times() -> None:
    from quant_os.data.weather.weather_historical_forecast_archive import (
        build_weather_historical_forecast_archive,
    )

    market = _resolved_markets_fixture()["markets"][0]
    payload = build_weather_historical_forecast_archive(
        markets=[market],
        mos_payloads_by_market={market["ticker"]: _iem_mos_fixture()},
        captured_at="2026-05-11T13:00:00Z",
    )

    snapshot = payload["forecasts_by_market"][market["ticker"]]
    assert payload["status"] == "WEATHER_HISTORICAL_FORECASTS_CAPTURED"
    assert snapshot["forecast_source"] == "iem_mos_historical_forecast"
    assert snapshot["forecast_ts"] == "2026-05-11T12:00:00Z"
    assert snapshot["known_at_ts"] == "2026-05-11T12:00:00Z"
    assert snapshot["forecast_value"] == 74.0
    assert snapshot["valid_times"] == [
        "2026-05-12T12:00:00Z",
        "2026-05-12T15:00:00Z",
        "2026-05-12T18:00:00Z",
        "2026-05-12T21:00:00Z",
    ]
    assert snapshot["uses_realized_weather"] is False
    assert snapshot["uses_resolution_as_forecast"] is False


def test_sequence52_batch_capture_can_use_iem_historical_forecast_archive(
    local_project: Path,
) -> None:
    from quant_os.data.weather.weather_historical_forecast_archive import (
        build_weather_historical_forecast_archive,
    )
    from quant_os.data.weather.weather_market_batch_capture import (
        run_weather_market_batch_capture,
    )
    from quant_os.research.replay_candidates.weather_market_resolved_dataset_builder import (
        build_weather_market_resolved_dataset_from_batch_capture,
    )

    market = _resolved_markets_fixture()["markets"][0]
    archive = build_weather_historical_forecast_archive(
        markets=[market],
        mos_payloads_by_market={market["ticker"]: _iem_mos_fixture()},
        captured_at="2026-05-11T13:00:00Z",
    )
    capture = run_weather_market_batch_capture(
        output_root=local_project,
        public_network_ok=True,
        run_id="fixture_iem_archive_052",
        series_payload=_series_fixture(),
        markets_payload={"markets": [market]},
        orderbook_payload=_orderbook_fixture(),
        forecast_archive_payload=archive,
        label_payloads=_label_payloads(),
        captured_at="2026-05-11T13:05:00Z",
    )
    dataset = build_weather_market_resolved_dataset_from_batch_capture(
        capture_manifest_path=capture["manifest_path"],
        output_root=local_project,
    )

    row = dataset["rows"][0]
    assert capture["status"] == "WEATHER_HISTORICAL_FORECASTS_CAPTURED"
    assert capture["proof_rows_created"] == 1
    assert dataset["dataset_status"] == "WEATHER_PROOF_ROWS_BUILT"
    assert row["forecast_source"] == "iem_mos_historical_forecast"
    assert row["forecast_ts"] == "2026-05-11T12:00:00Z"
    assert row["known_at_ts"] == "2026-05-11T12:00:00Z"
    assert row["orderbook_ts"] == "2026-05-13T04:59:00Z"
    assert row["forecast_value"] == 74.0
    assert row["resolution_value"] == 73.0


def test_sequence52_resolved_market_discovery_is_deterministic_under_fixtures(
    local_project: Path,
) -> None:
    from quant_os.data.weather.weather_resolved_market_discovery import (
        discover_resolved_weather_markets,
        write_weather_resolved_discovery_report,
    )

    first = discover_resolved_weather_markets(
        series_payload=_series_fixture(),
        markets_payload=_resolved_markets_fixture(),
        captured_at="2026-05-16T19:00:00Z",
    )
    second = discover_resolved_weather_markets(
        series_payload=_series_fixture(),
        markets_payload=_resolved_markets_fixture(),
        captured_at="2026-05-16T19:00:00Z",
    )
    report = write_weather_resolved_discovery_report(
        output_root=local_project,
        series_payload=_series_fixture(),
        markets_payload=_resolved_markets_fixture(),
        captured_at="2026-05-16T19:00:00Z",
    )

    assert first == second
    assert first["status"] == "RESOLVED_WEATHER_BATCH_READY"
    assert first["resolved_market_count"] == 3
    assert first["pending_market_count"] == 1
    assert first["markets"][0]["proof_label_available"] is True
    assert Path(report["report_paths"]["json"]).exists()
    assert Path(report["report_paths"]["markdown"]).exists()


def test_sequence52_resolution_label_fetcher_rejects_guessed_or_ambiguous_labels() -> None:
    from quant_os.data.weather.weather_resolution_label_fetcher import (
        fetch_weather_resolution_labels,
        parse_high_temp_resolution_label,
    )

    market = _resolved_markets_fixture()["markets"][0]
    good = parse_high_temp_resolution_label(
        market=market,
        cli_text="CLIMATE REPORT\nMAXIMUM 73\nISSUED 1200 AM EDT MAY 13 2026\n",
        source_url="https://forecast.weather.gov/product.php?site=OKX&product=CLI&issuedby=NYC",
    )
    ambiguous = parse_high_temp_resolution_label(
        market=market,
        cli_text="CLIMATE REPORT\nMAXIMUM M\n",
        source_url="https://forecast.weather.gov/product.php?site=OKX&product=CLI&issuedby=NYC",
    )
    missing = fetch_weather_resolution_labels(markets=[market], label_payloads={})

    assert good["status"] == "RESOLUTION_LABEL_AVAILABLE"
    assert good["resolution_label"] == "IN_BUCKET"
    assert good["label_confidence"] == "HIGH"
    assert ambiguous["status"] == "RESOLUTION_LABEL_AMBIGUOUS"
    assert "OBSERVED_MAX_TEMP_MISSING" in ambiguous["blockers"]
    assert missing["labels"][0]["status"] == "RESOLUTION_LABELS_MISSING"
    assert missing["labels"][0]["resolution_label"] == ""


def test_sequence52_batch_capture_is_read_only_local_only_ci_disabled_and_preserves_hashes(
    local_project: Path,
) -> None:
    from quant_os.data.weather.weather_market_batch_capture import (
        run_weather_market_batch_capture,
    )

    disabled = run_weather_market_batch_capture(output_root=local_project, public_network_ok=False)
    captured = run_weather_market_batch_capture(
        output_root=local_project,
        public_network_ok=True,
        run_id="fixture_capture_052",
        series_payload=_series_fixture(),
        markets_payload=_resolved_markets_fixture(),
        orderbook_payload=_orderbook_fixture(),
        forecast_payload=_forecast_fixture(),
        label_payloads=_label_payloads(),
        captured_at="2026-05-16T19:00:00Z",
    )

    assert disabled["status"] == "PUBLIC_NETWORK_DISABLED"
    assert disabled["network_fetch_attempted"] is False
    assert disabled["ci_network_dependency"] is False
    assert captured["read_only"] is True
    assert captured["auth_headers_allowed"] is False
    assert captured["browser_cookies_allowed"] is False
    assert captured["order_placement_allowed"] is False
    assert captured["artifacts_accepted"] >= 10
    assert captured["proof_rows_created"] == 3
    assert captured["rows_pending_labels"] == 1
    assert captured["combined_provenance_hash"].startswith("sha256:")


def test_sequence52_proof_dataset_builder_requires_labels_enforces_no_lookahead_and_pending_not_proof(
    local_project: Path,
) -> None:
    from quant_os.data.weather.weather_market_batch_capture import run_weather_market_batch_capture
    from quant_os.research.replay_candidates.weather_market_resolved_dataset_builder import (
        build_weather_market_resolved_dataset_from_batch_capture,
    )

    capture = run_weather_market_batch_capture(
        output_root=local_project,
        public_network_ok=True,
        run_id="fixture_dataset_052",
        series_payload=_series_fixture(),
        markets_payload=_resolved_markets_fixture(),
        orderbook_payload=_orderbook_fixture(),
        forecast_payload=_forecast_fixture(),
        label_payloads=_label_payloads(),
        captured_at="2026-05-16T19:00:00Z",
    )
    dataset = build_weather_market_resolved_dataset_from_batch_capture(
        capture_manifest_path=capture["manifest_path"],
        output_root=local_project,
    )

    assert dataset["dataset_status"] == "WEATHER_RESOLVED_DATASET_READY"
    assert dataset["real_public_row_count"] == 4
    assert dataset["proof_row_count"] == 3
    assert any(row["market_id"] == "KXHIGHNY-26MAY15-T65" for row in dataset["pending_rows"])
    assert all(row["resolution_label"] for row in dataset["rows"] if row["proof_eligible"])

    with pytest.raises(ValueError, match="known_at_ts must be <= orderbook_ts"):
        build_weather_market_resolved_dataset_from_batch_capture(
            capture_manifest_path=capture["manifest_path"],
            output_root=local_project,
            override_known_at_ts="2026-05-16T20:00:00Z",
            override_orderbook_ts="2026-05-16T19:00:00Z",
        )


def test_sequence52_batch_paper_proving_includes_costs_fills_baselines_placebos(
    local_project: Path,
) -> None:
    from quant_os.data.weather.weather_market_batch_capture import run_weather_market_batch_capture
    from quant_os.proving.weather_market_batch_paper_proving import (
        run_weather_market_batch_paper_proving,
    )
    from quant_os.research.replay_candidates.weather_market_resolved_dataset_builder import (
        build_weather_market_resolved_dataset_from_batch_capture,
    )

    capture = run_weather_market_batch_capture(
        output_root=local_project,
        public_network_ok=True,
        run_id="fixture_proving_052",
        series_payload=_series_fixture(),
        markets_payload=_resolved_markets_fixture(),
        orderbook_payload=_orderbook_fixture(),
        forecast_payload=_forecast_fixture(),
        label_payloads=_label_payloads(),
        captured_at="2026-05-16T19:00:00Z",
    )
    dataset = build_weather_market_resolved_dataset_from_batch_capture(
        capture_manifest_path=capture["manifest_path"],
        output_root=local_project,
    )
    paper = run_weather_market_batch_paper_proving(dataset["rows"], output_root=local_project)

    assert paper["proof_row_count"] == 3
    assert paper["costs_included"] is True
    assert paper["fill_assumptions_included"] is True
    assert paper["baseline_comparison"]["baseline_count"] >= 3
    assert paper["placebo_comparison"]["placebo_count"] >= 3
    assert paper["oos_walk_forward_status"] == "OOS_WALK_FORWARD_MISSING"
    assert "SAMPLE_TOO_THIN" in paper["sample_warnings"]


def test_sequence52_readiness_blocks_thin_samples_one_row_dominance_and_live_claims(
    local_project: Path,
) -> None:
    from quant_os.proving.weather_market_batch_paper_proving import (
        run_weather_market_batch_paper_proving,
    )
    from quant_os.readiness.weather_market_batch_paper_readiness import (
        evaluate_weather_market_batch_paper_readiness,
    )
    from quant_os.research.replay_candidates.weather_market_replay_schema import (
        WeatherMarketReplayRow,
        build_fixture_weather_market_replay_row,
    )

    base = build_fixture_weather_market_replay_row()
    base.update(
        {
            "market_id": "real_public_thin_1",
            "event_id": "real_public_thin_event_1",
            "fixture_only": False,
            "synthetic": False,
            "proof_eligible": True,
            "source_quality": "PUBLIC_READ_ONLY_ALLOWED",
            "provenance_hash": "sha256:real_public_thin_1",
        }
    )
    row = WeatherMarketReplayRow.model_validate(base)
    paper = run_weather_market_batch_paper_proving([row], output_root=local_project)
    readiness = evaluate_weather_market_batch_paper_readiness(
        dataset_payload={
            "dataset_status": "WEATHER_RESOLVED_DATASET_READY",
            "rows": [row.to_report_dict()],
            "real_public_row_count": 1,
            "proof_row_count": 1,
            "fixture_row_count": 0,
            "blockers": [],
        },
        paper_payload=paper,
        output_root=local_project,
    )

    assert readiness["readiness_status"] == "PAPER_PROFIT_BLOCKED_BY_SAMPLE"
    assert "SAMPLE_TOO_THIN" in readiness["blockers"]
    assert readiness["paper_profit_candidate"] is False
    assert readiness["canary_ready"] is False
    assert readiness["live_ready"] is False
    assert readiness["canary_readiness_claimed"] is False
    assert readiness["live_readiness_claimed"] is False


def test_sequence52_readiness_records_baseline_and_placebo_guard_failures(
    local_project: Path,
) -> None:
    from quant_os.readiness.weather_market_batch_paper_readiness import (
        evaluate_weather_market_batch_paper_readiness,
    )

    paper = {
        "readiness_status": "PAPER_PROFIT_BLOCKED",
        "costs_included": True,
        "fill_assumptions_included": True,
        "baseline_comparison": {"included": True, "paper_beats_comparison": False},
        "placebo_comparison": {"included": True, "paper_beats_comparison": False},
        "one_row_dominance": {"detected": False},
        "oos_walk_forward_status": "OOS_WALK_FORWARD_AVAILABLE",
        "synthetic_rows_counted_as_profit_evidence": False,
        "execution_authority": "NONE",
        "live_trading_enabled": False,
        "sample_warnings": [],
    }
    readiness = evaluate_weather_market_batch_paper_readiness(
        dataset_payload={
            "dataset_status": "WEATHER_PROOF_ROWS_BUILT",
            "rows": [{} for _ in range(30)],
            "pending_rows": [],
            "real_public_row_count": 30,
            "proof_row_count": 30,
            "fixture_row_count": 0,
            "blockers": [],
        },
        paper_payload=paper,
        output_root=local_project,
    )

    assert readiness["readiness_status"] == "PAPER_PROFIT_BLOCKED_BY_BASELINE"
    assert "BASELINE_COMPARISON_NOT_BEATEN" in readiness["blockers"]
    assert "PLACEBO_COMPARISON_NOT_BEATEN" in readiness["blockers"]
    assert readiness["paper_profit_candidate"] is False


def test_sequence52_pending_monitor_tracks_phase51_unresolved_market(local_project: Path) -> None:
    from quant_os.data.weather.weather_pending_resolution_monitor import (
        write_weather_pending_resolution_monitor_report,
    )

    payload = write_weather_pending_resolution_monitor_report(output_root=local_project)

    assert payload["status"] == "RESOLUTION_LABELS_MISSING"
    assert payload["pending_markets"][0]["market_id"] == "KXHIGHNY-26MAY15-T65"
    assert "weather-resolution-labels" in payload["pending_markets"][0]["recheck_command"]
    assert payload["live_trading_enabled"] is False
    assert payload["execution_authority"] == "NONE"


def test_sequence52_cli_make_targets_are_fixture_safe(local_project: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env = {**os.environ, "PYTHONPATH": str(repo_root / "src")}
    commands = [
        [sys.executable, "-m", "quant_os.cli", "data", "weather-resolved-market-discovery"],
        [sys.executable, "-m", "quant_os.cli", "data", "weather-resolution-labels"],
        [sys.executable, "-m", "quant_os.cli", "data", "weather-market-batch-capture"],
        [sys.executable, "-m", "quant_os.cli", "research", "weather-resolved-dataset"],
        [sys.executable, "-m", "quant_os.cli", "proving", "weather-batch-paper-proving"],
        [sys.executable, "-m", "quant_os.cli", "readiness", "weather-batch-paper-readiness"],
        [sys.executable, "-m", "quant_os.cli", "data", "weather-pending-resolution-monitor"],
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
        assert "execution_authority" in result.stdout
        assert "NONE" in result.stdout

    make_cmd = (repo_root / "make.cmd").read_text(encoding="utf-8")
    assert 'if "%TARGET%"=="sequence52-smoke"' in make_cmd
    assert "tests/test_sequence52_weather_resolved_batch_paper_proving.py" in make_cmd


def test_sequence52_no_auth_signing_order_cancel_wallet_copy_trade_or_evasion_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_paths = [
        "src/quant_os/data/weather/weather_resolved_market_discovery.py",
        "src/quant_os/data/weather/weather_historical_forecast_archive.py",
        "src/quant_os/data/weather/weather_resolution_label_fetcher.py",
        "src/quant_os/data/weather/weather_market_batch_capture.py",
        "src/quant_os/research/replay_candidates/weather_market_resolved_dataset_builder.py",
        "src/quant_os/proving/weather_market_batch_paper_proving.py",
        "src/quant_os/readiness/weather_market_batch_paper_readiness.py",
        "src/quant_os/data/weather/weather_pending_resolution_monitor.py",
    ]
    forbidden_tokens = [
        "create_order(",
        "cancel_order(",
        "post_order(",
        "place_order(",
        "sign_order(",
        "wallet_signer",
        "authenticated_client",
        "authorization:",
        "cookie:",
        "bypass_captcha(",
        "proxy_evasion(",
        "copy_trade(",
        "mirror_wallet(",
        "live_ready = True",
        "canary_ready = True",
        "guaranteed",
        "safe profit",
    ]

    for relative_path in source_paths:
        source_path = repo_root / relative_path
        assert source_path.exists(), source_path
        text = source_path.read_text(encoding="utf-8").lower()
        for token in forbidden_tokens:
            assert token not in text
