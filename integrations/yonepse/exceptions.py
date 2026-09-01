"""YONEPSE integration exceptions."""


class YonepseError(Exception):
    """Base exception for YONEPSE integration errors."""


class YonepseClientError(YonepseError):
    """Raised when a YONEPSE API request fails."""


class YonepseParseError(YonepseError):
    """Raised when YONEPSE response data cannot be parsed."""


class YonepseDatasetNotFoundError(YonepseError):
    """Raised when a requested YONEPSE dataset is not available."""
