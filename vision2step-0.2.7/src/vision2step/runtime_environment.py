"""Environment filtering for trusted local Vision2STEP subprocesses."""

from __future__ import annotations

import os
from collections.abc import Mapping

SENSITIVE_ENV_NAMES = {
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
    "GOOGLE_APPLICATION_CREDENTIALS",
}
SENSITIVE_ENV_SUFFIXES = (
    "_API_KEY",
    "_AUTH_TOKEN",
    "_ACCESS_TOKEN",
    "_CREDENTIAL",
    "_CREDENTIALS",
    "_PASSWORD",
    "_PRIVATE_KEY",
    "_SECRET",
    "_TOKEN",
)


def sanitized_runtime_environment(
    source: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Preserve OS runtime state while removing secrets and Python injection settings."""

    original = os.environ if source is None else source
    environment: dict[str, str] = {}
    for key, value in original.items():
        normalized = key.upper()
        if normalized.startswith("PYTHON"):
            continue
        if normalized in SENSITIVE_ENV_NAMES:
            continue
        if normalized.endswith(SENSITIVE_ENV_SUFFIXES):
            continue
        environment[key] = value
    return environment
