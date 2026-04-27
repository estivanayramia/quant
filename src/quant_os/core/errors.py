class QuantOSError(Exception):
    """Base error for deterministic QuantOps failures."""


class DomainError(QuantOSError):
    """Raised when a domain invariant is violated."""


class InvalidOrderTransition(DomainError):
    """Raised when an order state transition is not allowed."""


class DataQualityError(QuantOSError):
    """Raised when market data fails validation."""


class LiveTradingDisabledError(QuantOSError):
    """Raised if a live execution path is attempted in Milestone 1."""
