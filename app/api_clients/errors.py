class ProviderError(RuntimeError):
    """Base error for external provider calls."""


class ProviderNotConfiguredError(ProviderError):
    """Raised when a real provider call is requested without credentials."""

