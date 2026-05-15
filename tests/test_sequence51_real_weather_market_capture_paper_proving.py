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
            "frequency": "daily",
            "settlement_sources": [
                {
                    "name": "NWS Climatological Report",
                    "url": "https://forecast.weather.gov/product.php?site=OKX&product=CLI&issuedby=NYC",
                }
            ],
            "product_metadata": {
                "important_info": {
                    "message": (
                        "The official and final value used to determine this market is the "
                        "highest temperature as reported by the relevant NWS Daily Climate Report."
                    )
                }
            },
        }
    }


def _markets_fixture() -> dict:
    return {
        "markets": [
            {
                "ticker": "KXHIGHNY-26MAY16-B78.5",
                "event_ticker": "KXHIGHNY-26MAY16",
                "title": "Will the **high temp in NYC** be 78-79 deg on May 16, 2026?",
                "status": "active",
                "market_type": "binary",
                "strike_type": "between",
                "floor_strike": 78,
                "cap_strike": 79,
                "yes_bid_dollars": "0.3800",
                "yes_ask_dollars": "0.4100",
                "yes_bid_size_fp": "1.00",
                "yes_ask_size_fp": "6.00",
                "no_bid_dollars": "0.5900",
                "no_ask_dollars": "0.6200",
                "volume_fp": "1701.64",
                "open_interest_fp": "1288.65",
                "open_time": "2026-05-15T14:00:00Z",
                "close_time": "2026-05-17T04:59:00Z",
                "expected_expiration_time": "2026-05-17T14:00:00Z",
                "occurrence_datetime": "2026-05-16T14:00:00Z",
                "expiration_value": "",
                "result": "",
                "rules_primary": (
                    "If the highest temperature recorded in Central Park, New York for "
                    "May 16, 2026 as reported by the National Weather Service's "
                    "Climatological Report (Daily), is between 78-79 deg, then the market "
                    "resolves to Yes."
                ),
                "rules_secondary": (
                    "The official and final value used to determine this market is the "
                    "highest temperature as reported by the corresponding NWS "
                    "Climatological Report (Daily) linked in the rules above."
                ),
            },
            {
                "ticker": "KXHIGHNY-26MAY16-T83",
                "event_ticker": "KXHIGHNY-26MAY16",
                "title": "Will the **high temp in NYC** be >83 deg on May 16, 2026?",
                "status": "active",
                "market_type": "binary",
                "strike_type": "greater",
                "floor_strike": 83,
                "yes_bid_dollars": "0.0400",
                "yes_ask_dollars": "0.0500",
                "yes_bid_size_fp": "114.00",
                "yes_ask_size_fp": "176.00",
                "volume_fp": "534.00",
                "open_interest_fp": "528.00",
                "open_time": "2026-05-15T14:00:00Z",
                "close_time": "2026-05-17T04:59:00Z",
                "expected_expiration_time": "2026-05-17T14:00:00Z",
                "occurrence_datetime": "2026-05-16T14:00:00Z",
                "expiration_value": "",
                "result": "",
                "rules_primary": (
                    "If the highest temperature recorded in Central Park, New York for "
                    "May 16, 2026 as reported by the National Weather Service's "
                    "Climatological Report (Daily), is greater than 83 deg, then the "
                    "market resolves to Yes."
                ),
            },
        ]
    }


def _orderbook_fixture() -> dict:
    return {
        "orderbook_fp": {
            "yes_dollars": [["0.2700", "614.00"], ["0.3800", "1.00"]],
            "no_dollars": [["0.4000", "616.40"], ["0.5900", "6.00"]],
        }
    }


def _forecast_fixture() -> dict:
    return {
        "properties": {
            "generatedAt": "2026-05-15T22:01:46+00:00",
            "updateTime": "2026-05-15T18:26:01+00:00",
            "periods": [
                {
                    "startTime": "2026-05-16T09:00:00-04:00",
                    "endTime": "2026-05-16T10:00:00-04:00",
                    "temperature": 75,
                    "temperatureUnit": "F",
                },
                {
                    "startTime": "2026-05-16T15:00:00-04:00",
                    "endTime": "2026-05-16T16:00:00-04:00",
                    "temperature": 79,
                    "temperatureUnit": "F",
                },
                {
                    "startTime": "2026-05-16T16:00:00-04:00",
                    "endTime": "2026-05-16T17:00:00-04:00",
                    "temperature": 78,
                    "temperatureUnit": "F",
                },
            ],
        }
    }


def _captured_bundle(local_project: Path) -> dict:
    from quant_os.data.weather.weather_market_public_capture import (
        run_weather_market_public_capture,
    )

    return run_weather_market_public_capture(
        output_root=local_project,
        public_network_ok=True,
        run_id="fixture_capture_051",
        series_payload=_series_fixture(),
        markets_payload=_markets_fixture(),
        orderbook_payload=_orderbook_fixture(),
        forecast_payload=_forecast_fixture(),
        captured_at="2026-05-15T22:10:00Z",
    )


def test_sequence51_weather_market_discovery_is_deterministic_under_fixtures(
    local_project: Path,
) -> None:
    from quant_os.data.weather.weather_market_discovery import (
        discover_weather_markets,
        write_weather_market_discovery_report,
    )

    first = discover_weather_markets(
        series_payload=_series_fixture(),
        markets_payload=_markets_fixture(),
        captured_at="2026-05-15T22:10:00Z",
    )
    second = discover_weather_markets(
        series_payload=_series_fixture(),
        markets_payload=_markets_fixture(),
        captured_at="2026-05-15T22:10:00Z",
    )
    report = write_weather_market_discovery_report(
        output_root=local_project,
        series_payload=_series_fixture(),
        markets_payload=_markets_fixture(),
        captured_at="2026-05-15T22:10:00Z",
    )

    assert first == second
    assert first["status"] == "PUBLIC_WEATHER_MARKET_FOUND"
    assert first["selected_market"]["ticker"] == "KXHIGHNY-26MAY16-B78.5"
    assert first["selected_market"]["location"] == "Central Park, New York"
    assert first["selected_market"]["variable"] == "temperature_max_f"
    assert first["selected_market"]["bucket_range"] == "78_to_79_f_inclusive"
    assert first["source_policy_verdict"] == "PUBLIC_READ_ONLY_ALLOWED"
    assert first["live_trading_enabled"] is False
    assert Path(report["report_paths"]["json"]).exists()
    assert Path(report["report_paths"]["markdown"]).exists()


def test_sequence51_source_matching_rejects_ambiguous_location_variable_or_bucket() -> None:
    from quant_os.data.weather.weather_source_matching import match_weather_source_to_market

    ambiguous = {
        "ticker": "KXHIGHNY-26MAY16-AMBIG",
        "title": "Will it be warm?",
        "rules_primary": "Weather decides this market.",
    }

    payload = match_weather_source_to_market(ambiguous, _series_fixture()["series"])

    assert payload["status"] == "WEATHER_DATA_CAPTURE_BLOCKED"
    assert "AMBIGUOUS_LOCATION" in payload["blockers"]
    assert "AMBIGUOUS_VARIABLE" in payload["blockers"]
    assert "AMBIGUOUS_BUCKET" in payload["blockers"]
    assert payload["proof_mapping_ready"] is False


def test_sequence51_public_capture_runner_is_read_only_local_only_and_ci_disabled(
    local_project: Path,
) -> None:
    from quant_os.data.weather.weather_market_public_capture import (
        run_weather_market_public_capture,
    )

    payload = run_weather_market_public_capture(
        output_root=local_project,
        public_network_ok=False,
        run_id="network_disabled_051",
    )

    assert payload["status"] == "PUBLIC_NETWORK_DISABLED"
    assert payload["read_only"] is True
    assert payload["network_fetch_attempted"] is False
    assert payload["ci_network_dependency"] is False
    assert payload["auth_headers_allowed"] is False
    assert payload["browser_cookies_allowed"] is False
    assert payload["order_placement_allowed"] is False
    assert payload["order_cancellation_allowed"] is False
    assert payload["raw_captures_commit_allowed"] is False


def test_sequence51_capture_artifacts_preserve_provenance_hashes(
    local_project: Path,
) -> None:
    from quant_os.data.weather.weather_market_capture_artifacts import (
        canonical_provenance_hash,
        write_capture_artifact,
    )

    artifact = write_capture_artifact(
        local_project / "data/external/manual_captures/weather_market_mismatch/hash/probe.json",
        {"alpha": 1, "beta": ["two"]},
        artifact_type="probe",
        source_id="fixture_source",
    )

    assert artifact["provenance_hash"] == canonical_provenance_hash(
        {"alpha": 1, "beta": ["two"]}
    )
    assert Path(artifact["path"]).exists()
    assert artifact["read_only"] is True


def test_sequence51_dataset_builder_enforces_no_lookahead_timestamps(
    local_project: Path,
) -> None:
    from quant_os.research.replay_candidates.weather_market_dataset_builder import (
        build_weather_market_dataset_from_capture,
    )

    bundle = _captured_bundle(local_project)
    market_artifact = bundle["artifacts"]["market_metadata"]
    forecast_artifact = bundle["artifacts"]["forecast_snapshot"]

    with pytest.raises(ValueError, match="known_at_ts must be <= orderbook_ts"):
        build_weather_market_dataset_from_capture(
            capture_manifest_path=bundle["manifest_path"],
            market_artifact_path=market_artifact["path"],
            orderbook_artifact_path=bundle["artifacts"]["orderbook_snapshot"]["path"],
            forecast_artifact_path=forecast_artifact["path"],
            resolution_artifact_path=bundle["artifacts"]["resolution_snapshot"]["path"],
            output_root=local_project,
            override_known_at_ts="2026-05-15T23:00:00Z",
            override_orderbook_ts="2026-05-15T22:10:00Z",
        )


def test_sequence51_dataset_builder_blocks_proof_rows_without_resolution_labels(
    local_project: Path,
) -> None:
    from quant_os.research.replay_candidates.weather_market_dataset_builder import (
        build_weather_market_dataset_from_capture,
    )

    bundle = _captured_bundle(local_project)
    dataset = build_weather_market_dataset_from_capture(
        capture_manifest_path=bundle["manifest_path"],
        market_artifact_path=bundle["artifacts"]["market_metadata"]["path"],
        orderbook_artifact_path=bundle["artifacts"]["orderbook_snapshot"]["path"],
        forecast_artifact_path=bundle["artifacts"]["forecast_snapshot"]["path"],
        resolution_artifact_path=bundle["artifacts"]["resolution_snapshot"]["path"],
        output_root=local_project,
    )

    assert dataset["dataset_status"] == "RESOLUTION_LABELS_MISSING"
    assert dataset["real_public_row_count"] == 1
    assert dataset["proof_row_count"] == 0
    assert dataset["rows"][0]["fixture_only"] is False
    assert dataset["rows"][0]["proof_eligible"] is False
    assert dataset["rows"][0]["resolution_label"] == ""


def test_sequence51_fixture_rows_cannot_support_profit_claims(local_project: Path) -> None:
    from quant_os.proving.weather_market_real_paper_proving import (
        run_weather_market_real_paper_proving,
    )
    from quant_os.readiness.weather_market_paper_profit_readiness import (
        evaluate_weather_market_paper_profit_readiness,
    )
    from quant_os.research.replay_candidates.weather_market_replay_schema import (
        WeatherMarketReplayRow,
        build_fixture_weather_market_replay_row,
    )

    row = WeatherMarketReplayRow.model_validate(build_fixture_weather_market_replay_row())
    paper = run_weather_market_real_paper_proving([row], output_root=local_project)
    readiness = evaluate_weather_market_paper_profit_readiness(
        dataset_payload={
            "dataset_status": "FIXTURE_ONLY_NOT_PROOF",
            "rows": [row.to_report_dict()],
            "real_public_row_count": 0,
            "proof_row_count": 0,
        },
        paper_payload=paper,
        output_root=local_project,
    )

    assert paper["readiness_status"] == "NO_PROFIT_CLAIM_ALLOWED"
    assert readiness["readiness_status"] == "NO_PROFIT_CLAIM_ALLOWED"
    assert "FIXTURE_ROWS_CANNOT_SUPPORT_PROOF" in readiness["blockers"]
    assert readiness["paper_profit_candidate"] is False


def test_sequence51_real_weather_paper_proving_includes_costs_fills_baselines_placebos(
    local_project: Path,
) -> None:
    from quant_os.proving.weather_market_real_paper_proving import (
        run_weather_market_real_paper_proving,
    )
    from quant_os.research.replay_candidates.weather_market_dataset_builder import (
        build_weather_market_dataset_from_capture,
    )

    bundle = _captured_bundle(local_project)
    dataset = build_weather_market_dataset_from_capture(
        capture_manifest_path=bundle["manifest_path"],
        market_artifact_path=bundle["artifacts"]["market_metadata"]["path"],
        orderbook_artifact_path=bundle["artifacts"]["orderbook_snapshot"]["path"],
        forecast_artifact_path=bundle["artifacts"]["forecast_snapshot"]["path"],
        resolution_artifact_path=bundle["artifacts"]["resolution_snapshot"]["path"],
        output_root=local_project,
    )
    paper = run_weather_market_real_paper_proving(dataset["rows"], output_root=local_project)

    assert paper["readiness_status"] == "RESOLUTION_LABELS_MISSING"
    assert paper["costs_included"] is True
    assert paper["fill_assumptions_included"] is True
    assert paper["baseline_comparison"]["included"] is True
    assert paper["baseline_comparison"]["baseline_count"] >= 3
    assert paper["placebo_comparison"]["included"] is True
    assert paper["placebo_comparison"]["placebo_count"] >= 3
    assert paper["proof_row_count"] == 0
    assert "RESOLUTION_LABELS_MISSING" in paper["sample_warnings"]


def test_sequence51_profit_claim_guard_blocks_thin_missing_oos_missing_label_results(
    local_project: Path,
) -> None:
    from quant_os.proving.weather_market_real_paper_proving import (
        run_weather_market_real_paper_proving,
    )
    from quant_os.readiness.weather_market_paper_profit_readiness import (
        evaluate_weather_market_paper_profit_readiness,
    )
    from quant_os.research.replay_candidates.weather_market_dataset_builder import (
        build_weather_market_dataset_from_capture,
    )

    bundle = _captured_bundle(local_project)
    dataset = build_weather_market_dataset_from_capture(
        capture_manifest_path=bundle["manifest_path"],
        market_artifact_path=bundle["artifacts"]["market_metadata"]["path"],
        orderbook_artifact_path=bundle["artifacts"]["orderbook_snapshot"]["path"],
        forecast_artifact_path=bundle["artifacts"]["forecast_snapshot"]["path"],
        resolution_artifact_path=bundle["artifacts"]["resolution_snapshot"]["path"],
        output_root=local_project,
    )
    paper = run_weather_market_real_paper_proving(dataset["rows"], output_root=local_project)
    readiness = evaluate_weather_market_paper_profit_readiness(
        dataset_payload=dataset,
        paper_payload=paper,
        output_root=local_project,
    )

    assert readiness["readiness_status"] == "RESOLUTION_LABELS_MISSING"
    assert "RESOLUTION_LABELS_MISSING" in readiness["blockers"]
    assert "OOS_WALK_FORWARD_MISSING" in readiness["blockers"]
    assert readiness["paper_profit_candidate"] is False
    assert readiness["allowed_statuses"] == [
        "PAPER_PROFIT_CANDIDATE",
        "PAPER_PROFIT_DIAGNOSTIC_ONLY",
        "SELECTED_LANE_NEEDS_MORE_DATA",
        "WEATHER_DATA_CAPTURE_BLOCKED",
        "MARKET_DATA_CAPTURE_BLOCKED",
        "RESOLUTION_LABELS_MISSING",
        "PAPER_PROFIT_BLOCKED_BY_SAMPLE",
        "PAPER_PROFIT_BLOCKED_BY_BASELINE",
        "PAPER_PROFIT_BLOCKED_BY_PLACEBO",
        "PAPER_PROFIT_BLOCKED_BY_COSTS",
        "PAPER_PROFIT_BLOCKED_BY_FILLS",
        "NO_PROFIT_CLAIM_ALLOWED",
    ]


def test_sequence51_readiness_cannot_claim_live_or_canary_readiness(
    local_project: Path,
) -> None:
    from quant_os.readiness.weather_market_paper_profit_readiness_report import (
        write_weather_market_paper_profit_readiness_report,
    )

    payload = write_weather_market_paper_profit_readiness_report(output_root=local_project)

    assert payload["canary_ready"] is False
    assert payload["live_ready"] is False
    assert payload["canary_readiness_claimed"] is False
    assert payload["live_readiness_claimed"] is False
    assert payload["live_trading_enabled"] is False
    assert payload["execution_authority"] == "NONE"
    assert payload["autonomy_milestones"]["weather_lane_selected"] == "met"
    assert payload["autonomy_milestones"]["canary_live"] == "blocked"


def test_sequence51_cli_make_targets_are_fixture_safe(local_project: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env = {**os.environ, "PYTHONPATH": str(repo_root / "src")}
    commands = [
        [sys.executable, "-m", "quant_os.cli", "data", "weather-market-discover"],
        [sys.executable, "-m", "quant_os.cli", "data", "weather-source-match"],
        [sys.executable, "-m", "quant_os.cli", "data", "weather-market-public-capture"],
        [sys.executable, "-m", "quant_os.cli", "research", "weather-market-dataset"],
        [sys.executable, "-m", "quant_os.cli", "proving", "weather-market-real-paper-proving"],
        [
            sys.executable,
            "-m",
            "quant_os.cli",
            "readiness",
            "weather-market-paper-profit-readiness",
        ],
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
    assert 'if "%TARGET%"=="sequence51-smoke"' in make_cmd
    assert "tests/test_sequence51_real_weather_market_capture_paper_proving.py" in make_cmd


def test_sequence51_no_auth_signing_order_cancel_wallet_copy_trade_or_evasion_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_paths = [
        "src/quant_os/data/weather/weather_market_discovery.py",
        "src/quant_os/data/weather/weather_source_matching.py",
        "src/quant_os/data/weather/weather_market_public_capture.py",
        "src/quant_os/data/weather/weather_market_capture_artifacts.py",
        "src/quant_os/research/replay_candidates/weather_market_dataset_builder.py",
        "src/quant_os/proving/weather_market_real_paper_proving.py",
        "src/quant_os/readiness/weather_market_paper_profit_readiness.py",
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
