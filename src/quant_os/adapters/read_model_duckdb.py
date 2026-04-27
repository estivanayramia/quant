from __future__ import annotations

import json
from pathlib import Path

import duckdb

from quant_os.core.events import DomainEvent, EventType


class DuckDBReadModelStore:
    def __init__(self, path: str | Path = "data/read_models/quant_os.duckdb") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def rebuild(self, events: list[DomainEvent]) -> Path:
        if self.path.exists():
            self.path.unlink()
        con = duckdb.connect(str(self.path))
        try:
            self._create_tables(con)
            self._insert_events(con, events)
            self._insert_orders(con, events)
            self._insert_positions(con, events)
            self._insert_risk(con, events)
            self._insert_backtests(con, events)
            self._insert_reports(con, events)
        finally:
            con.close()
        return self.path

    def _create_tables(self, con: duckdb.DuckDBPyConnection) -> None:
        con.execute(
            """
            create table events (
                event_id varchar,
                event_type varchar,
                timestamp timestamp,
                aggregate_id varchar,
                payload_json varchar,
                schema_version integer
            )
            """
        )
        con.execute(
            """
            create table orders (
                client_order_id varchar,
                strategy_id varchar,
                symbol varchar,
                side varchar,
                quantity double,
                status varchar,
                created_at timestamp,
                updated_at timestamp
            )
            """
        )
        con.execute(
            """
            create table positions (
                symbol varchar,
                quantity double,
                average_entry_price double,
                realized_pnl double,
                updated_at timestamp
            )
            """
        )
        con.execute(
            """
            create table risk_decisions (
                event_id varchar,
                approved boolean,
                reasons_json varchar,
                strategy_id varchar,
                symbol varchar,
                checked_at timestamp
            )
            """
        )
        con.execute(
            """
            create table backtest_runs (
                event_id varchar,
                strategy_id varchar,
                metrics_json varchar,
                completed_at timestamp
            )
            """
        )
        con.execute(
            """
            create table reports (
                event_id varchar,
                report_path varchar,
                generated_at timestamp
            )
            """
        )

    def _insert_events(self, con: duckdb.DuckDBPyConnection, events: list[DomainEvent]) -> None:
        rows = [
            (
                event.event_id,
                str(event.event_type),
                event.timestamp,
                event.aggregate_id,
                json.dumps(event.payload, sort_keys=True, default=str),
                event.schema_version,
            )
            for event in events
        ]
        if rows:
            con.executemany("insert into events values (?, ?, ?, ?, ?, ?)", rows)

    def _insert_orders(self, con: duckdb.DuckDBPyConnection, events: list[DomainEvent]) -> None:
        orders: dict[str, dict[str, object]] = {}
        for event in events:
            payload = event.payload
            order_payload = payload.get("order")
            if event.event_type == EventType.ORDER_SUBMITTED and isinstance(order_payload, dict):
                orders[str(order_payload["client_order_id"])] = dict(order_payload)
            elif event.event_type in {
                EventType.ORDER_ACCEPTED,
                EventType.ORDER_REJECTED,
                EventType.ORDER_CANCELLED,
            } and isinstance(order_payload, dict):
                client_order_id = str(order_payload["client_order_id"])
                orders.setdefault(client_order_id, {}).update(order_payload)
            elif event.event_type == EventType.ORDER_FILLED:
                fill = payload.get("fill", {})
                client_order_id = str(fill.get("client_order_id", ""))
                if client_order_id in orders:
                    orders[client_order_id]["status"] = "FILLED"
                    orders[client_order_id]["updated_at"] = event.timestamp
        rows = [
            (
                order.get("client_order_id"),
                order.get("strategy_id"),
                order.get("symbol"),
                order.get("side"),
                order.get("quantity"),
                order.get("status"),
                order.get("created_at"),
                order.get("updated_at"),
            )
            for order in orders.values()
        ]
        if rows:
            con.executemany("insert into orders values (?, ?, ?, ?, ?, ?, ?, ?)", rows)

    def _insert_positions(self, con: duckdb.DuckDBPyConnection, events: list[DomainEvent]) -> None:
        positions: dict[str, dict[str, object]] = {}
        for event in events:
            if event.event_type in {
                EventType.POSITION_OPENED,
                EventType.POSITION_UPDATED,
                EventType.POSITION_CLOSED,
            }:
                position = event.payload.get("position", {})
                if isinstance(position, dict):
                    positions[str(position["symbol"])] = position
        rows = [
            (
                position.get("symbol"),
                position.get("quantity", 0.0),
                position.get("average_entry_price", 0.0),
                position.get("realized_pnl", 0.0),
                position.get("updated_at"),
            )
            for position in positions.values()
        ]
        if rows:
            con.executemany("insert into positions values (?, ?, ?, ?, ?)", rows)

    def _insert_risk(self, con: duckdb.DuckDBPyConnection, events: list[DomainEvent]) -> None:
        rows = []
        for event in events:
            if event.event_type in {EventType.RISK_APPROVED, EventType.RISK_REJECTED}:
                decision = event.payload.get("decision", {})
                if isinstance(decision, dict):
                    rows.append(
                        (
                            event.event_id,
                            decision.get("approved"),
                            json.dumps(decision.get("reasons", []), sort_keys=True),
                            decision.get("strategy_id"),
                            decision.get("symbol"),
                            decision.get("checked_at"),
                        )
                    )
        if rows:
            con.executemany("insert into risk_decisions values (?, ?, ?, ?, ?, ?)", rows)

    def _insert_backtests(self, con: duckdb.DuckDBPyConnection, events: list[DomainEvent]) -> None:
        rows = [
            (
                event.event_id,
                event.payload.get("strategy_id"),
                json.dumps(event.payload.get("metrics", {}), sort_keys=True, default=str),
                event.timestamp,
            )
            for event in events
            if event.event_type == EventType.BACKTEST_COMPLETED
        ]
        if rows:
            con.executemany("insert into backtest_runs values (?, ?, ?, ?)", rows)

    def _insert_reports(self, con: duckdb.DuckDBPyConnection, events: list[DomainEvent]) -> None:
        rows = [
            (event.event_id, event.payload.get("report_path"), event.timestamp)
            for event in events
            if event.event_type == EventType.REPORT_GENERATED
        ]
        if rows:
            con.executemany("insert into reports values (?, ?, ?)", rows)
