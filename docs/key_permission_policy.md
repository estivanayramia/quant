# Key Permission Policy

Phase 11 uses no real keys. Future key manifests may describe intended scopes,
but must not contain credentials.

Allowed future scopes are limited to read-only balance visibility and spot-trade
scope if a later phase explicitly implements a live canary. Forbidden scopes
include withdrawals, transfers, futures, margin, leverage, shorts, options,
admin, and universal account permissions.
