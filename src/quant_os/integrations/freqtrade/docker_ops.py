from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from quant_os.data.loaders import load_yaml
from quant_os.integrations.freqtrade.artifacts import ensure_freqtrade_artifact_dirs


@dataclass
class DockerOperationResult:
    action: str
    status: str
    command: list[str] = field(default_factory=list)
    stdout: str = ""
    stderr: str = ""
    returncode: int | None = None
    docker_available: bool = False
    compose_available: bool = False
    message: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class DockerOps:
    def __init__(self, config_path: str | Path = "configs/freqtrade.yaml") -> None:
        self.config = load_yaml(config_path)
        docker = self.config.get("docker", {})
        self.compose_file = str(docker.get("compose_file", "docker-compose.yml"))
        self.service = str(docker.get("service", "freqtrade-dry-run"))
        self.profile = str(docker.get("profile", "freqtrade-dry-run"))
        self.project_name = str(docker.get("project_name", "quant-os-freqtrade"))
        self.logs_tail_lines = int(docker.get("logs_tail_lines", 300))

    def docker_available(self) -> bool:
        return shutil.which("docker") is not None

    def compose_available(self) -> bool:
        if not self.docker_available():
            return False
        result = subprocess.run(
            ["docker", "compose", "version"],
            check=False,
            capture_output=True,
            text=True,
        )
        return result.returncode == 0

    def base_command(self) -> list[str]:
        return [
            "docker",
            "compose",
            "--profile",
            self.profile,
            "-f",
            self.compose_file,
            "-p",
            self.project_name,
        ]

    def build_command_preview(self) -> str:
        return " ".join(self.base_command() + ["run", "--rm", self.service, "--help"])

    def start_dry_run(self) -> DockerOperationResult:
        command = self.base_command() + ["up", "-d", "--pull", "never", self.service]
        if not self.compose_available():
            result = DockerOperationResult(
                action="start",
                status="UNAVAILABLE",
                command=command,
                docker_available=self.docker_available(),
                compose_available=False,
                message="Docker Compose is unavailable; container was not started.",
            )
            self.write_operation_manifest(result)
            return result
        completed = subprocess.run(command, check=False, capture_output=True, text=True)
        result = DockerOperationResult(
            action="start",
            status="PASS" if completed.returncode == 0 else "FAIL",
            command=command,
            stdout=completed.stdout,
            stderr=completed.stderr,
            returncode=completed.returncode,
            docker_available=True,
            compose_available=True,
        )
        self.write_operation_manifest(result)
        return result

    def stop_dry_run(self) -> DockerOperationResult:
        command = self.base_command() + ["stop", self.service]
        if not self.compose_available():
            result = DockerOperationResult(
                action="stop",
                status="UNAVAILABLE",
                command=command,
                docker_available=self.docker_available(),
                compose_available=False,
                message="Docker Compose is unavailable; no container was stopped.",
            )
            self.write_operation_manifest(result)
            return result
        completed = subprocess.run(command, check=False, capture_output=True, text=True)
        result = DockerOperationResult(
            action="stop",
            status="PASS" if completed.returncode == 0 else "FAIL",
            command=command,
            stdout=completed.stdout,
            stderr=completed.stderr,
            returncode=completed.returncode,
            docker_available=True,
            compose_available=True,
        )
        self.write_operation_manifest(result)
        return result

    def get_logs(self) -> DockerOperationResult:
        command = self.base_command() + ["logs", "--tail", str(self.logs_tail_lines), self.service]
        if not self.compose_available():
            result = DockerOperationResult(
                action="logs",
                status="UNAVAILABLE",
                command=command,
                docker_available=self.docker_available(),
                compose_available=False,
                message="Docker Compose is unavailable; logs were not fetched from Docker.",
            )
            self.write_operation_manifest(result)
            return result
        completed = subprocess.run(command, check=False, capture_output=True, text=True)
        result = DockerOperationResult(
            action="logs",
            status="PASS" if completed.returncode == 0 else "WARN",
            command=command,
            stdout=completed.stdout,
            stderr=completed.stderr,
            returncode=completed.returncode,
            docker_available=True,
            compose_available=True,
        )
        self.write_operation_manifest(result)
        return result

    def get_container_status(self) -> DockerOperationResult:
        command = self.base_command() + ["ps", "--format", "json", self.service]
        if not self.compose_available():
            return DockerOperationResult(
                action="status",
                status="UNAVAILABLE",
                command=command,
                docker_available=self.docker_available(),
                compose_available=False,
                message="Docker Compose is unavailable.",
            )
        completed = subprocess.run(command, check=False, capture_output=True, text=True)
        status = "UNKNOWN"
        if completed.returncode == 0 and completed.stdout.strip():
            status = "running" if "running" in completed.stdout.lower() else "stopped"
        elif completed.returncode == 0:
            status = "stopped"
        return DockerOperationResult(
            action="status",
            status=status,
            command=command,
            stdout=completed.stdout,
            stderr=completed.stderr,
            returncode=completed.returncode,
            docker_available=True,
            compose_available=True,
        )

    def write_operation_manifest(
        self,
        result: DockerOperationResult,
        output_path: str | Path | None = None,
    ) -> Path:
        dirs = ensure_freqtrade_artifact_dirs()
        path = (
            Path(output_path)
            if output_path
            else dirs["manifests_dir"] / "latest_operation_manifest.json"
        )
        payload = {
            **result.to_dict(),
            "generated_at": datetime.now(UTC).isoformat(),
            "dry_run_only": True,
            "live_trading_enabled": False,
            "command_preview": self.build_command_preview(),
        }
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return path
