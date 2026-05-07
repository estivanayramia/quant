from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class SourceClassification(StrEnum):
    RUNTIME_SAFE = "runtime-safe"
    REFERENCE_ONLY = "reference-only"
    OFFLINE_CACHE_ONLY = "offline-cache-only"


class BenchmarkLayer(StrEnum):
    DATA = "data_layer"
    REPLAY = "replay_layer"
    CALIBRATION_RESEARCH = "calibration_research_layer"
    SKILLS_INSTRUCTIONS = "skills_instructions_layer"
    OPERATOR_REPORT = "operator_report_layer"


class SourceEntry(BaseModel):
    source_id: str = Field(pattern=r"^[a-z0-9_]+$")
    name: str
    repository_url: str | None = None
    homepage_url: str | None = None
    classification: SourceClassification
    provenance: str
    license_name: str
    license_caveat: str
    data_caveats: tuple[str, ...]
    requires_network: bool
    requires_keys: bool = False
    requires_wallet: bool = False
    signing_required: bool = False
    read_only: bool = True
    live_capable_package: bool = False
    execution_authority: Literal["none"] = "none"
    allowed_uses: tuple[str, ...]
    forbidden_uses: tuple[str, ...]
    mapped_layers: tuple[BenchmarkLayer, ...]
    optional_import: str | None = None
    runtime_notes: str = ""

    @model_validator(mode="after")
    def enforce_read_only_boundary(self) -> SourceEntry:
        failures: list[str] = []
        if not self.read_only:
            failures.append("source entries must be read-only")
        if self.requires_keys:
            failures.append("registry entries must not require keys")
        if self.requires_wallet:
            failures.append("registry entries must not require wallets")
        if self.signing_required:
            failures.append("registry entries must not require signing")
        if self.execution_authority != "none":
            failures.append("registry entries must not grant execution authority")
        if not self.forbidden_uses:
            failures.append("forbidden_uses must explicitly document the boundary")
        if failures:
            raise ValueError("; ".join(failures))
        return self

    def to_report_dict(self) -> dict[str, object]:
        return {
            "source_id": self.source_id,
            "name": self.name,
            "classification": self.classification.value,
            "repository_url": self.repository_url,
            "homepage_url": self.homepage_url,
            "provenance": self.provenance,
            "license_name": self.license_name,
            "license_caveat": self.license_caveat,
            "data_caveats": list(self.data_caveats),
            "requires_network": self.requires_network,
            "requires_keys": self.requires_keys,
            "requires_wallet": self.requires_wallet,
            "signing_required": self.signing_required,
            "read_only": self.read_only,
            "live_capable_package": self.live_capable_package,
            "execution_authority": self.execution_authority,
            "allowed_uses": list(self.allowed_uses),
            "forbidden_uses": list(self.forbidden_uses),
            "mapped_layers": [layer.value for layer in self.mapped_layers],
            "optional_import": self.optional_import,
            "runtime_notes": self.runtime_notes,
        }


class SourceRegistry(BaseModel):
    entries: tuple[SourceEntry, ...]

    @model_validator(mode="after")
    def enforce_unique_source_ids(self) -> SourceRegistry:
        source_ids = [entry.source_id for entry in self.entries]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("source registry contains duplicate source_id values")
        return self

    def by_id(self, source_id: str) -> SourceEntry:
        for entry in self.entries:
            if entry.source_id == source_id:
                return entry
        raise KeyError(source_id)

    def classified(self, classification: SourceClassification) -> tuple[SourceEntry, ...]:
        return tuple(entry for entry in self.entries if entry.classification == classification)

    def live_capable_sources(self) -> tuple[SourceEntry, ...]:
        return tuple(entry for entry in self.entries if entry.live_capable_package)
