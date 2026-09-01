"""NEPSE integration exceptions."""


class NepseError(Exception):
    """Base exception for all NEPSE integration errors."""


class NepseAuthenticationError(NepseError):
    """Raised when authentication with NEPSE API fails."""


class NepseSSLError(NepseError):
    """Raised when SSL certificate verification fails.

    This is often due to the NEPSE server's incomplete certificate chain.
    The client supports a verify_ssl option; use with caution.
    """


class NepseRateLimitError(NepseError):
    """Raised when NEPSE API rate limit is exceeded (HTTP 429)."""


class NepseConnectionError(NepseError):
    """Raised when connection to NEPSE API fails."""


class NepseTimeoutError(NepseError):
    """Raised when a request to NEPSE API times out."""


class NepseInvalidResponseError(NepseError):
    """Raised when NEPSE API returns an invalid or unexpected response."""


class NepseServerError(NepseError):
    """Raised when NEPSE API returns a 5xx error."""
