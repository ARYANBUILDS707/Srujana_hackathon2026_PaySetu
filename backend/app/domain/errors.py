"""Domain exceptions. The HTTP layer maps them to problem responses in Phase 1 (T1.3)."""


class DomainError(Exception):
    """Base class for all domain errors."""


class DomainValidationError(DomainError, ValueError):
    """Inputs violate a documented constraint (e.g. a future delivery date)."""


class RuleSetError(DomainError, ValueError):
    """A rule-set document is malformed, incomplete or uses unsupported values."""


class MissingRateError(DomainError, LookupError):
    """No bank-rate period covers a date for which interest must be computed."""
