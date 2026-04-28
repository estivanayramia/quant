from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HistoricalSourceInfo:
    name: str
    source_type: str
    requires_network: bool
    requires_keys: bool
    enabled: bool
    license_note: str


LOCAL_FILE_SOURCE = HistoricalSourceInfo(
    name="LOCAL_FILE",
    source_type="user_provided_file",
    requires_network=False,
    requires_keys=False,
    enabled=True,
    license_note="User-provided files remain local; user must verify license terms.",
)
