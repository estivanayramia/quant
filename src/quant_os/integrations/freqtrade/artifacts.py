from __future__ import annotations

from pathlib import Path

from quant_os.data.loaders import load_yaml


def freqtrade_artifact_dirs(config_path: str | Path = "configs/freqtrade.yaml") -> dict[str, Path]:
    config = load_yaml(config_path)
    artifacts = config.get("artifacts", {})
    defaults = {
        "logs_dir": "reports/freqtrade/logs",
        "status_dir": "reports/freqtrade/status",
        "reconciliation_dir": "reports/freqtrade/reconciliation",
        "manifests_dir": "reports/freqtrade/manifests",
    }
    return {key: Path(str(artifacts.get(key, value))) for key, value in defaults.items()}


def ensure_freqtrade_artifact_dirs() -> dict[str, Path]:
    dirs = freqtrade_artifact_dirs()
    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)
    return dirs
