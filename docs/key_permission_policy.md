# Key Permission Policy

Phase 11 uses no real keys. Future key manifests may describe intended scopes,
but must not contain credentials.

Allowed future scopes are limited to read-only balance visibility and spot-trade
scope if a later phase explicitly implements a live canary. Forbidden scopes
include withdrawals, transfers, futures, margin, leverage, shorts, options,
admin, and universal account permissions.

Phase 12 supports local permission manifest import from JSON or YAML. The
manifest must contain descriptive scopes only and must not contain credentials.
Forbidden or ambiguous scopes fail closed.

Phase 13 credential files must remain outside the repository. Permission
manifests may describe future scopes, but forbidden scopes such as withdrawals,
transfers, futures, margin, leverage, shorting, options, universal access, or
admin access block the live canary lane.

Phase 14 keeps the same permission boundary for the single exchange adapter.
The adapter settings file may describe spot-only account mode and capability
metadata, but credentials still must be loaded only from a separate local file
outside the repo. Reports may include masked metadata and blocker names, never
API keys, secrets, passphrases, or raw credential content.
