from __future__ import annotations

DEFAULT_LICENSE_NOTE = (
    "User-provided or public historical sample. Verify source terms before research use; "
    "do not commit proprietary datasets."
)


def validate_license_note(license_note: str | None, required: bool = True) -> list[str]:
    if required and not (license_note or "").strip():
        return ["LICENSE_NOTE_MISSING"]
    return []
