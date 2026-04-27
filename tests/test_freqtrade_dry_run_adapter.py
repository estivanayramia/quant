from __future__ import annotations

from pathlib import Path

from quant_os.integrations.freqtrade.dry_run_adapter import FreqtradeDryRunAdapter


def test_freqtrade_adapter_preview_and_manifest(local_project):
    adapter = FreqtradeDryRunAdapter()
    config_path = adapter.generate_config()
    strategy_path = adapter.export_strategy()
    result = adapter.validate_config()
    manifest = adapter.write_run_manifest()
    assert result.passed
    assert config_path.exists()
    assert strategy_path.exists()
    assert manifest == Path("reports/freqtrade/latest_manifest.json")
    assert "docker compose --profile freqtrade-dry-run" in adapter.build_docker_command()


def test_freqtrade_adapter_does_not_execute_docker(local_project):
    adapter = FreqtradeDryRunAdapter()
    command = adapter.build_docker_command()
    assert isinstance(command, str)
    assert "run --rm freqtrade-dry-run --help" in command
