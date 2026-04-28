from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from quant_os.adapters.event_store_jsonl import JsonlEventStore
from quant_os.core.events import EventType, make_event
from quant_os.integrations.freqtrade.docker_ops import DockerOperationResult, DockerOps
from quant_os.integrations.freqtrade.dry_run_adapter import FreqtradeDryRunAdapter
from quant_os.integrations.freqtrade.log_ingestion import ingest_freqtrade_logs
from quant_os.integrations.freqtrade.operational_status import write_operational_status_report
from quant_os.integrations.freqtrade.reconciliation import reconcile_freqtrade
from quant_os.security.live_trading_guard import live_trading_guard


class FreqtradeRunner:
    def __init__(self, event_store: JsonlEventStore | None = None) -> None:
        self.event_store = event_store or JsonlEventStore()
        self.adapter = FreqtradeDryRunAdapter()
        self.docker = DockerOps()

    def prepare(self) -> dict[str, object]:
        config_path = self.adapter.generate_config()
        strategy_path = self.adapter.export_strategy()
        safety = self.adapter.validate_config()
        live_guard = live_trading_guard()
        if not live_guard.passed:
            msg = ";".join(live_guard.reasons)
            raise RuntimeError(msg)
        manifest = self.adapter.write_run_manifest()
        self._augment_manifest(manifest, strategy_path)
        return {
            "config_path": str(config_path),
            "strategy_path": str(strategy_path),
            "safety_passed": safety.passed,
            "manifest": str(manifest),
        }

    def start(self) -> DockerOperationResult:
        try:
            self.prepare()
        except Exception as exc:
            result = DockerOperationResult(action="start", status="FAIL", message=str(exc))
            self.docker.write_operation_manifest(result)
            self.event_store.append(
                make_event(EventType.WATCHDOG_FAILED, "freqtrade-runner-start", result.to_dict())
            )
            return result
        result = self.docker.start_dry_run()
        self.event_store.append(
            make_event(EventType.REPORT_GENERATED, "freqtrade-start", result.to_dict())
        )
        return result

    def stop(self) -> DockerOperationResult:
        result = self.docker.stop_dry_run()
        self.event_store.append(
            make_event(EventType.REPORT_GENERATED, "freqtrade-stop", result.to_dict())
        )
        return result

    def logs(self) -> dict[str, object]:
        result = self.docker.get_logs()
        payload = ingest_freqtrade_logs(result.stdout)
        self.event_store.append(make_event(EventType.REPORT_GENERATED, "freqtrade-logs", payload))
        return payload

    def status(self) -> dict[str, object]:
        return write_operational_status_report()

    def report(self) -> dict[str, object]:
        status = write_operational_status_report()
        reconciliation = reconcile_freqtrade()
        return {"status": status, "reconciliation": reconciliation}

    def reconcile(self) -> dict[str, object]:
        return reconcile_freqtrade()

    def _augment_manifest(self, manifest: Path, strategy_path: Path) -> None:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        payload["strategy_sha256"] = hashlib.sha256(strategy_path.read_bytes()).hexdigest()
        payload["operation_manifest_generated_at"] = datetime.now(UTC).isoformat()
        manifest.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
