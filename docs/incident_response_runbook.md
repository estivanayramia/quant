# Canary Incident Response Runbook

If live-danger evidence appears, the required response is to activate or
confirm the kill switch, stop any future canary lane, preserve artifacts,
quarantine the strategy, run reconciliation, and write an incident record.

The same fail-closed posture applies to connectivity loss, reconciliation
failure, missing stoploss evidence, broad API permissions, strategy divergence,
or future loss-cap breach evidence. No automatic restart is allowed.

Phase 12 rehearsals preserve this runbook as a dry drill. They do not connect
to any exchange and cannot place or cancel real orders.

Phase 13 `canary-live-stop` activates the live canary kill switch and blocks
subsequent fire attempts until a future human-reviewed recovery workflow is
defined.
