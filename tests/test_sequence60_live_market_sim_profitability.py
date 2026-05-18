from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

NOW = "2026-05-18T16:00:00Z"
BOOK_TS = "2026-05-18T15:59:00Z"


def _write_json(root: Path, relative: str, payload: dict[str, object]) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _market(index: int = 0, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "candidate_id": "pm_weather_forecast_market_mismatch",
        "venue": "kalshi",
        "ticker": f"KXHIGHNY-26MAY{18 + index:02d}-B83.5",
        "event_ticker": f"KXHIGHNY-26MAY{18 + index:02d}",
        "series_ticker": "KXHIGHNY",
        "title": f"Will the high temp in NYC be 83-84 deg on May {18 + index}, 2026?",
        "status": "active",
        "threshold_bucket": "83_to_84_f_inclusive",
        "yes_bid": 0.19,
        "yes_ask": 0.21,
        "no_bid": 0.79,
        "no_ask": 0.81,
        "spread": 0.02,
        "liquidity": 12.0,
        "orderbook_ts": BOOK_TS,
        "resolution_ts": f"2026-05-{19 + index:02d}T14:00:00Z",
        "market_evidence_hash": f"market-hash-{index}",
    }
    payload.update(overrides)
    return payload


def _forecast(index: int = 0, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "status": "CURRENT_FORECAST_MATCHED",
        "source_id": "nws_api",
        "source_url": "https://api.weather.gov/gridpoints/OKX/34,45/forecast/hourly",
        "source_kind": "forecast",
        "forecast_issue_ts": "2026-05-18T15:30:00Z",
        "forecast_valid_ts": f"2026-05-{18 + index:02d}T18:00:00-04:00",
        "known_at_ts": "2026-05-18T15:30:00Z",
        "orderbook_ts": BOOK_TS,
        "forecast_value": 83,
        "forecast_bucket": "83_to_84_f_inclusive",
        "bucket_match": True,
        "evidence_hash": f"forecast-hash-{index}",
    }
    payload.update(overrides)
    return payload


def _eligible_payload(index: int = 0, **market_overrides: object) -> dict[str, object]:
    return {
        "status": "CURRENT_MARKET_ELIGIBILITY_PASSED",
        "market": _market(index, **market_overrides),
        "forecast_evidence": _forecast(index),
        "forecast_evidence_hash": f"forecast-hash-{index}",
        "market_evidence_hash": f"market-hash-{index}",
        "blockers": [],
    }


def _run_filled_position(root: Path, index: int = 0) -> dict[str, object]:
    from quant_os.autonomy.live_market_profit_observer import (
        write_live_market_profit_observer_report,
    )
    from quant_os.autonomy.live_market_sim_fill_model import write_live_market_sim_fill_report
    from quant_os.autonomy.live_market_sim_intents import write_live_market_sim_intents_report
    from quant_os.autonomy.live_market_sim_ledger import write_live_market_sim_ledger_report

    observer = write_live_market_profit_observer_report(
        output_root=root,
        now_ts=NOW,
        current_market_payload=_eligible_payload(index),
        preflight_payload={"status": "FIRST_DOLLAR_PREFLIGHT_READY", "blockers": []},
    )
    write_live_market_sim_intents_report(output_root=root)
    write_live_market_sim_fill_report(output_root=root)
    ledger = write_live_market_sim_ledger_report(output_root=root)
    return {"observer": observer, "ledger": ledger}


def test_sequence60_observer_uses_public_unauthenticated_data_only(local_project: Path) -> None:
    from quant_os.autonomy.live_market_profit_observer import (
        write_live_market_profit_observer_report,
    )

    payload = write_live_market_profit_observer_report(
        output_root=local_project,
        now_ts=NOW,
        current_market_payload=_eligible_payload(),
        preflight_payload={"status": "FIRST_DOLLAR_PREFLIGHT_READY", "blockers": []},
    )

    assert payload["status"] == "LIVE_PROFIT_OBSERVER_READY"
    assert payload["public_read_only"] is True
    assert payload["authenticated_endpoint_called"] is False
    assert payload["checked_account_balance"] is False
    assert payload["checked_portfolio"] is False
    assert payload["request_methods"] == ["GET"]
    assert payload["observation"]["orderbook_snapshot"]["yes_ask"] == 0.21
    assert payload["observation"]["forecast_evidence"]["source_kind"] == "forecast"
    assert payload["api_keys_loaded"] is False
    assert payload["private_keys_loaded"] is False


def test_sequence60_observer_records_no_market_and_no_trade_states(local_project: Path) -> None:
    from quant_os.autonomy.live_market_profit_observer import (
        write_live_market_profit_observer_report,
    )
    from quant_os.autonomy.live_market_sim_intents import write_live_market_sim_intents_report

    payload = write_live_market_profit_observer_report(
        output_root=local_project,
        now_ts=NOW,
        current_market_payload={
            "status": "CURRENT_MARKET_ELIGIBILITY_NO_CURRENT_MARKET",
            "market": None,
            "forecast_evidence": {"status": "CURRENT_FORECAST_BLOCKED"},
            "blockers": ["NO_CURRENT_PUBLIC_MARKET_SUPPLIED"],
        },
        preflight_payload={"status": "FIRST_DOLLAR_PREFLIGHT_STRUCTURALLY_READY_NO_CURRENT_MARKET"},
    )
    intents = write_live_market_sim_intents_report(output_root=local_project)

    assert payload["status"] == "LIVE_PROFIT_OBSERVER_NO_ELIGIBLE_MARKET"
    assert payload["observation"]["observation_kind"] == "NO_CURRENT_MARKET"
    assert intents["status"] == "LIVE_SIM_INTENT_NO_TRADE"
    state = json.loads(
        (local_project / "reports/live_market_sim_profitability/state/latest_state.json").read_text(
            encoding="utf-8"
        )
    )
    assert state["observations_count"] == 1
    assert state["eligible_intent_count"] == 0


def test_sequence60_fake_intents_are_no_transmit_fake_money_and_unsigned(
    local_project: Path,
) -> None:
    from quant_os.autonomy.live_market_profit_observer import (
        write_live_market_profit_observer_report,
    )
    from quant_os.autonomy.live_market_sim_intents import write_live_market_sim_intents_report

    write_live_market_profit_observer_report(
        output_root=local_project,
        now_ts=NOW,
        current_market_payload=_eligible_payload(),
        preflight_payload={"status": "FIRST_DOLLAR_PREFLIGHT_READY", "blockers": []},
    )
    payload = write_live_market_sim_intents_report(output_root=local_project)

    assert payload["status"] == "LIVE_SIM_INTENT_READY"
    intent = payload["intent"]
    assert intent["fake_money"] is True
    assert intent["no_transmit"] is True
    assert intent["dry_run_only"] is True
    assert intent["order_transmission_enabled"] is False
    assert intent["authenticated_requests_enabled"] is False
    assert intent["request_signing_enabled"] is False
    assert intent["contains_signed_headers"] is False
    text = json.dumps(payload, sort_keys=True)
    assert "/portfolio/orders" not in text
    assert "KALSHI-ACCESS-SIGNATURE" not in text


def test_sequence60_fake_fill_model_is_conservative_and_never_guaranteed(
    local_project: Path,
) -> None:
    from quant_os.autonomy.live_market_sim_fill_model import apply_live_market_sim_fill_model

    filled = apply_live_market_sim_fill_model(
        intent={"fake_client_order_id": "sim-1", "market_ticker": "T", "limit_price": 0.24, "fake_contracts": 3},
        observation={"market": _market(yes_ask=0.21, yes_bid=0.19, spread=0.02, liquidity=2)},
    )
    blocked = apply_live_market_sim_fill_model(
        intent={"fake_client_order_id": "sim-2", "market_ticker": "T", "limit_price": 0.40, "fake_contracts": 3},
        observation={"market": _market(yes_ask=0.40, yes_bid=0.20, spread=0.20, liquidity=10)},
    )
    no_fill = apply_live_market_sim_fill_model(
        intent={"fake_client_order_id": "sim-3", "market_ticker": "T", "limit_price": 0.20, "fake_contracts": 1},
        observation={"market": _market(yes_ask=0.24, yes_bid=0.22, spread=0.02, liquidity=10)},
    )

    assert filled["status"] == "LIVE_SIM_FILL_APPLIED"
    assert filled["guaranteed_fill"] is False
    assert filled["fake_fill"]["filled_contracts"] == 1
    assert filled["fake_fill"]["fill_price"] >= 0.21
    assert blocked["status"] == "LIVE_SIM_FILL_BLOCKED"
    assert "SPREAD_TOO_WIDE" in blocked["blockers"]
    assert no_fill["status"] == "LIVE_SIM_NO_FILL"


def test_sequence60_ledger_tracks_pending_and_resolved_outcomes(local_project: Path) -> None:
    from quant_os.autonomy.live_market_sim_outcomes import write_live_market_sim_outcomes_report

    run = _run_filled_position(local_project, index=0)
    pending = write_live_market_sim_outcomes_report(output_root=local_project)
    resolved = write_live_market_sim_outcomes_report(
        output_root=local_project,
        public_outcome_labels={run["observer"]["observation_id"]: "yes"},
    )

    assert run["ledger"]["status"] == "LIVE_SIM_LEDGER_UPDATED"
    assert run["ledger"]["ledger_entries"][0]["outcome_status"] == "PENDING"
    assert pending["status"] == "LIVE_SIM_OUTCOME_PENDING"
    assert resolved["status"] == "LIVE_SIM_OUTCOME_RESOLVED"
    assert resolved["resolved_outcome_count"] == 1
    assert resolved["outcomes"][0]["outcome_label"] == "yes"


def test_sequence60_pnl_uses_real_outcome_labels_and_blocks_guesses(
    local_project: Path,
) -> None:
    from quant_os.autonomy.live_market_sim_outcomes import write_live_market_sim_outcomes_report
    from quant_os.autonomy.live_market_sim_pnl import write_live_market_sim_pnl_report

    run = _run_filled_position(local_project, index=0)
    guessed = write_live_market_sim_outcomes_report(
        output_root=local_project,
        public_outcome_labels={run["observer"]["observation_id"]: "probably_yes"},
    )
    blocked = write_live_market_sim_pnl_report(output_root=local_project)
    resolved = write_live_market_sim_outcomes_report(
        output_root=local_project,
        public_outcome_labels={run["observer"]["observation_id"]: "yes"},
    )
    pnl = write_live_market_sim_pnl_report(output_root=local_project)

    assert guessed["status"] == "LIVE_SIM_OUTCOME_BLOCKED"
    assert blocked["status"] == "LIVE_SIM_PNL_BLOCKED"
    assert "GUESSED_OR_INVALID_OUTCOME_LABEL" in blocked["blockers"]
    assert resolved["status"] == "LIVE_SIM_OUTCOME_RESOLVED"
    assert pnl["status"] == "LIVE_SIM_PNL_READY"
    assert pnl["fake_net_pnl"] > 0


def test_sequence60_baseline_and_placebo_comparison_can_block_success(
    local_project: Path,
) -> None:
    from quant_os.proving.live_market_sim_baselines import build_live_market_sim_baseline_comparison
    from quant_os.proving.live_market_sim_placebos import build_live_market_sim_placebo_comparison

    baseline_block = build_live_market_sim_baseline_comparison(strategy_net_pnl=0.10, baseline_pnls={"naive": 0.20})
    placebo_block = build_live_market_sim_placebo_comparison(strategy_net_pnl=0.10, placebo_pnls={"sign_flip": 0.10})
    baseline_pass = build_live_market_sim_baseline_comparison(strategy_net_pnl=0.50, baseline_pnls={"naive": 0.0})
    placebo_pass = build_live_market_sim_placebo_comparison(strategy_net_pnl=0.50, placebo_pnls={"sign_flip": -0.25})

    assert baseline_block["status"] == "LIVE_SIM_BASELINE_NOT_BEATEN"
    assert placebo_block["status"] == "LIVE_SIM_PLACEBO_NOT_BEATEN"
    assert baseline_pass["status"] == "LIVE_SIM_BASELINES_BEATEN"
    assert placebo_pass["status"] == "LIVE_SIM_BASELINES_BEATEN"


def test_sequence60_reconciliation_detects_missing_evidence_hashes(local_project: Path) -> None:
    from quant_os.autonomy.live_market_sim_reconciliation import (
        build_live_market_sim_reconciliation,
    )

    _write_json(
        local_project,
        "reports/live_market_sim_profitability/ledger/latest_ledger.json",
        {
            "status": "LIVE_SIM_LEDGER_UPDATED",
            "ledger_entries": [
                {
                    "observation_id": "obs-1",
                    "fake_client_order_id": "intent-1",
                    "fake_fill_id": "fill-1",
                    "event_hash": "",
                    "market_evidence_hash": "",
                    "forecast_evidence_hash": "forecast-hash",
                    "outcome_status": "PENDING",
                }
            ],
        },
    )
    _write_json(
        local_project,
        "reports/live_market_sim_profitability/pnl/latest_pnl.json",
        {"status": "LIVE_SIM_PNL_PENDING_OUTCOMES", "fake_net_pnl": 0.0},
    )
    _write_json(
        local_project,
        "reports/live_market_sim_profitability/comparison/latest_comparison.json",
        {"status": "LIVE_SIM_COMPARISON_PENDING"},
    )
    payload = build_live_market_sim_reconciliation(output_root=local_project)

    assert payload["status"] == "LIVE_SIM_RECONCILIATION_FAILED"
    assert "MISSING_EVIDENCE_HASH" in payload["blockers"]


def test_sequence60_readiness_requires_counts_outcomes_profit_and_comparisons(
    local_project: Path,
) -> None:
    from quant_os.readiness.live_market_sim_profitability import (
        build_live_market_sim_profitability_readiness,
    )

    too_small = build_live_market_sim_profitability_readiness(
        output_root=local_project,
        state={"observations": [{"observation_id": "obs-1"}]},
        pnl={"status": "LIVE_SIM_PNL_PENDING_OUTCOMES", "fake_net_pnl": 0.0, "pending_outcome_count": 1},
        comparison={"status": "LIVE_SIM_COMPARISON_PENDING"},
        reconciliation={"status": "LIVE_SIM_RECONCILIATION_PENDING_OUTCOMES"},
    )
    pending = build_live_market_sim_profitability_readiness(
        output_root=local_project,
        state={
            "observations": [{"observation_id": f"obs-{i}"} for i in range(10)],
            "intents": [{"fake_client_order_id": f"intent-{i}"} for i in range(3)],
            "fills": [{"fake_fill_id": "fill-1"}],
        },
        pnl={"status": "LIVE_SIM_PNL_PENDING_OUTCOMES", "fake_net_pnl": 0.0, "pending_outcome_count": 1},
        comparison={"status": "LIVE_SIM_COMPARISON_PENDING"},
        reconciliation={"status": "LIVE_SIM_RECONCILIATION_PENDING_OUTCOMES"},
    )
    not_proven = build_live_market_sim_profitability_readiness(
        output_root=local_project,
        state={
            "observations": [{"observation_id": f"obs-{i}"} for i in range(10)],
            "intents": [{"fake_client_order_id": f"intent-{i}"} for i in range(3)],
            "fills": [{"fake_fill_id": "fill-1"}],
        },
        pnl={"status": "LIVE_SIM_PNL_READY", "fake_net_pnl": -0.01, "resolved_outcome_count": 3},
        comparison={"status": "LIVE_SIM_BASELINES_BEATEN"},
        reconciliation={"status": "LIVE_SIM_RECONCILIATION_PASSED"},
    )

    assert too_small["status"] == "LIVE_MARKET_SIMULATED_PROFITABILITY_NEEDS_MORE_OBSERVATIONS"
    assert "MIN_OBSERVATIONS_NOT_MET" in too_small["blockers"]
    assert pending["status"] == "LIVE_MARKET_SIMULATED_PROFITABILITY_PENDING_OUTCOMES"
    assert not_proven["status"] == "LIVE_MARKET_SIMULATED_PROFITABILITY_NOT_PROVEN"
    assert "FAKE_NET_PNL_NOT_POSITIVE" in not_proven["blockers"]


def test_sequence60_readiness_can_prove_positive_reconciled_profitability(
    local_project: Path,
) -> None:
    from quant_os.readiness.live_market_sim_profitability import (
        build_live_market_sim_profitability_readiness,
    )

    payload = build_live_market_sim_profitability_readiness(
        output_root=local_project,
        state={
            "observations": [{"observation_id": f"obs-{i}"} for i in range(10)],
            "intents": [{"fake_client_order_id": f"intent-{i}"} for i in range(3)],
            "fills": [{"fake_fill_id": "fill-1"}],
        },
        pnl={"status": "LIVE_SIM_PNL_READY", "fake_net_pnl": 1.5, "resolved_outcome_count": 3},
        comparison={"status": "LIVE_SIM_BASELINES_BEATEN", "baseline_beaten": True, "placebo_beaten": True},
        reconciliation={"status": "LIVE_SIM_RECONCILIATION_PASSED"},
    )

    assert payload["status"] == "LIVE_MARKET_SIMULATED_PROFITABILITY_PROVEN"
    assert payload["live_trading_enabled"] is False
    assert payload["execution_authority"] == "NONE"
    assert payload["order_transmission_enabled"] is False
    assert payload["authenticated_requests_enabled"] is False
    assert payload["request_signing_enabled"] is False
    assert payload["api_keys_loaded"] is False
    assert payload["private_keys_loaded"] is False
    assert payload["actual_order_count"] == 0
    assert payload["actual_cancel_count"] == 0


def test_sequence60_scheduler_is_data_only(local_project: Path) -> None:
    from quant_os.autonomy.live_market_sim_profitability_schedule import (
        write_live_market_sim_profitability_schedule_report,
    )

    payload = write_live_market_sim_profitability_schedule_report(output_root=local_project)

    assert payload["status"] == "LIVE_MARKET_SIM_PROFITABILITY_SCHEDULE_READY"
    assert payload["data_only"] is True
    assert payload["credentials_required"] is False
    assert payload["order_transmission_enabled"] is False
    assert payload["authenticated_requests_enabled"] is False
    assert payload["request_signing_enabled"] is False
    assert payload["max_runs"] == 20
    assert "live-market-profit-observer --public-network-ok" in payload["exact_resume_command"]
    assert "for ($i = 1; $i -le 20; $i++)" in payload["exact_powershell_command"]


def test_sequence60_cli_make_target_and_no_auth_order_path(local_project: Path) -> None:
    commands = [
        [sys.executable, "-m", "quant_os.cli", "autonomy", "live-market-profit-observer"],
        [sys.executable, "-m", "quant_os.cli", "autonomy", "live-market-sim-intents"],
        [sys.executable, "-m", "quant_os.cli", "autonomy", "live-market-sim-fill"],
        [sys.executable, "-m", "quant_os.cli", "autonomy", "live-market-sim-ledger"],
        [sys.executable, "-m", "quant_os.cli", "autonomy", "live-market-sim-outcomes"],
        [sys.executable, "-m", "quant_os.cli", "autonomy", "live-market-sim-pnl"],
        [sys.executable, "-m", "quant_os.cli", "proving", "live-market-sim-comparison"],
        [sys.executable, "-m", "quant_os.cli", "autonomy", "live-market-sim-reconciliation"],
        [sys.executable, "-m", "quant_os.cli", "readiness", "live-market-sim-profitability"],
        [sys.executable, "-m", "quant_os.cli", "autonomy", "live-market-sim-profitability-schedule"],
    ]
    for command in commands:
        result = subprocess.run(command, cwd=local_project, capture_output=True, text=True, check=False)
        assert result.returncode == 0, result.stderr
        assert "live_trading_enabled" in result.stdout

    repo_root = Path(__file__).resolve().parents[1]
    make_cmd = (repo_root / "make.cmd").read_text(encoding="utf-8")
    assert 'if "%TARGET%"=="sequence60-smoke"' in make_cmd
    assert 'if "%TARGET%"=="live-market-sim-profitability-smoke"' in make_cmd
    for path in [
        "src/quant_os/autonomy/live_market_profit_observer.py",
        "src/quant_os/autonomy/live_market_sim_intents.py",
        "src/quant_os/autonomy/live_market_sim_fill_model.py",
        "src/quant_os/autonomy/live_market_sim_ledger.py",
        "src/quant_os/autonomy/live_market_sim_outcomes.py",
        "src/quant_os/autonomy/live_market_sim_pnl.py",
        "src/quant_os/autonomy/live_market_sim_reconciliation.py",
        "src/quant_os/readiness/live_market_sim_profitability.py",
    ]:
        text = (repo_root / path).read_text(encoding="utf-8")
        assert "requests.post" not in text
        assert "urllib.request.Request(" not in text
        assert "/portfolio/orders" not in text
        assert "KALSHI-ACCESS-SIGNATURE" not in text
        assert "cancel_order" not in text
