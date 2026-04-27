from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import duckdb

from quant_os.adapters.ai_mock import MockAIProvider
from quant_os.adapters.event_store_jsonl import JsonlEventStore
from quant_os.adapters.market_data_parquet import LocalParquetMarketData
from quant_os.adapters.reports_local import LocalReportWriter
from quant_os.core.events import EventType, make_event
from quant_os.data.quality import validate_ohlcv
from quant_os.projections.rebuild import rebuild_read_models

DISCLAIMER = "This is simulation only. No live trading."


def generate_daily_report(
    event_store: JsonlEventStore | None = None,
    report_dir: str | Path = "reports",
    db_path: str | Path = "data/read_models/quant_os.duckdb",
) -> dict[str, object]:
    event_store = event_store or JsonlEventStore()
    data = LocalParquetMarketData().load()
    data_summary = validate_ohlcv(data) if not data.empty else {"rows": 0, "symbols": []}
    db_file = rebuild_read_models(event_store, db_path)
    projections = _projection_summary(db_file)
    ai = MockAIProvider()
    context = {"data_rows": data_summary["rows"], "events": projections["event_count"]}
    ai_summary = ai.daily_report_summary(context)
    risk_notes = ai.risk_notes({"risk_rejections": projections["risk_rejections"]})
    payload = {
        "run_timestamp": projections["generated_at"],
        "data_quality_summary": data_summary,
        "backtest_metrics": projections["latest_backtest_metrics"],
        "strategy_comparison": _load_tournament_summary(),
        "risk_rejections": projections["risk_rejections"],
        "open_positions": projections["open_positions"],
        "kill_switch_status": projections["kill_switch_status"],
        "ai_notes": {"summary": ai_summary, "risk_notes": risk_notes},
        "disclaimer": DISCLAIMER,
    }
    writer = LocalReportWriter(report_dir)
    md_path = writer.write_markdown("daily_report.md", _markdown(payload))
    json_path = writer.write_json("daily_report.json", payload)
    event_store.append(
        make_event(
            EventType.REPORT_GENERATED,
            "daily-report",
            {"report_path": str(md_path), "json_path": str(json_path)},
        )
    )
    return payload


def _projection_summary(db_path: Path) -> dict[str, object]:
    with duckdb.connect(str(db_path)) as con:
        event_count = con.execute("select count(*) from events").fetchone()[0]
        risk_rejections = con.execute(
            "select count(*) from risk_decisions where approved = false"
        ).fetchone()[0]
        open_positions = con.execute(
            "select * from positions where abs(quantity) > 1e-12"
        ).fetch_df()
        latest_backtest = con.execute(
            "select metrics_json from backtest_runs order by completed_at desc limit 1"
        ).fetchone()
        kill_active = con.execute(
            "select count(*) from events where event_type = 'KILL_SWITCH_ACTIVATED'"
        ).fetchone()[0]
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "event_count": int(event_count),
        "risk_rejections": int(risk_rejections),
        "open_positions": open_positions.to_dict(orient="records"),
        "latest_backtest_metrics": latest_backtest[0] if latest_backtest else "{}",
        "kill_switch_status": "active" if kill_active else "inactive",
    }


def _load_tournament_summary() -> dict[str, object]:
    path = Path("reports/tournament_summary.json")
    if not path.exists():
        return {}
    import json

    return json.loads(path.read_text(encoding="utf-8"))


def _markdown(payload: dict[str, object]) -> str:
    return "\n".join(
        [
            "# Daily QuantOps Report",
            "",
            f"Run timestamp: {payload['run_timestamp']}",
            "",
            f"Disclaimer: {DISCLAIMER}",
            "",
            "## Data Quality",
            f"`{payload['data_quality_summary']}`",
            "",
            "## Backtest Metrics",
            f"`{payload['backtest_metrics']}`",
            "",
            "## Strategy Comparison",
            f"`{payload['strategy_comparison']}`",
            "",
            "## Risk Rejections",
            str(payload["risk_rejections"]),
            "",
            "## Open Positions",
            f"`{payload['open_positions']}`",
            "",
            "## Kill Switch",
            str(payload["kill_switch_status"]),
            "",
            "## Mock AI Notes",
            f"`{payload['ai_notes']}`",
            "",
        ]
    )
