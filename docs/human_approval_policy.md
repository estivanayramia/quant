# Human Approval Policy

Human approval is a required future gate and cannot unlock live trading by
itself. Approval records must include an approver placeholder, written
rationale, scope, expiry, acknowledged risks, and a revocation path.

Missing, expired, malformed, or revoked approvals block canary readiness. The
approval registry is local scaffolding for auditability only; it is not an
execution permission system.
