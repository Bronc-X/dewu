class ProviderError(RuntimeError):
    """Base error for external provider calls."""


class ProviderNotConfiguredError(ProviderError):
    """Raised when a real provider call is requested without credentials."""


class ProviderRateLimitError(ProviderError):
    """Raised when a provider asks us to stop sending requests for a long window."""

    def __init__(self, message: str, retry_after_seconds: float | None = None) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds
