from __future__ import annotations


def systemd_unit() -> str:
    return "\n".join(
        [
            "[Unit]",
            "Description=Quant OS autonomous safe runbook",
            "",
            "[Service]",
            "WorkingDirectory=/path/to/quant",
            "ExecStart=python -m quant_os.cli autonomous run-once",
        ]
    )
