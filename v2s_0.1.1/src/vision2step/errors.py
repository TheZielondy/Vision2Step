"""Domain-specific errors raised by Vision2STEP."""


class Vision2StepError(Exception):
    """Base exception for expected application failures."""


class InvalidImageError(Vision2StepError):
    """Raised when an image cannot be sent safely to Claude."""


class AnalyzerResponseError(Vision2StepError):
    """Raised when Claude does not return a usable structured response."""

