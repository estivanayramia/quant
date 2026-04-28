from __future__ import annotations

import shutil

from quant_os.integrations.freqtrade.docker_ops import DockerOps


def test_docker_unavailable_is_graceful(local_project, monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda _name: None)
    ops = DockerOps()
    assert ops.docker_available() is False
    result = ops.get_container_status()
    assert result.status == "UNAVAILABLE"


def test_docker_command_preview_does_not_execute(local_project, monkeypatch):
    calls = []
    monkeypatch.setattr(shutil, "which", lambda _name: "docker")

    def fake_run(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("subprocess should not run for preview")

    monkeypatch.setattr("subprocess.run", fake_run)
    preview = DockerOps().build_command_preview()
    assert "docker compose --profile freqtrade-dry-run" in preview
    assert calls == []


def test_stop_command_builds_safe_command(local_project, monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda _name: None)
    result = DockerOps().stop_dry_run()
    assert result.status == "UNAVAILABLE"
    assert "stop" in result.command
    assert "freqtrade-dry-run" in result.command
