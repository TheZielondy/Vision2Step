"""Domain-specific errors raised by Vision2STEP."""


class Vision2StepError(Exception):
    """Base exception for expected application failures."""


class InvalidImageError(Vision2StepError):
    """Raised when an image cannot be sent safely to Claude."""


class AnalyzerResponseError(Vision2StepError):
    """Raised when Claude does not return a usable structured response."""


class BuilderResponseError(Vision2StepError):
    """Raised when Builder Claude does not return a usable proposal."""


class SourcePolicyError(Vision2StepError):
    """Raised when generated Python violates the restricted CadQuery policy."""


class CandidateExecutionError(Vision2StepError):
    """Raised when a candidate cannot be executed or validated."""
