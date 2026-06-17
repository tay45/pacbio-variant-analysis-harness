"""Typed exceptions for operator-facing failures."""


class HarnessError(Exception):
    """Base class for expected harness errors."""


class ConfigError(HarnessError):
    """Configuration validation failed."""


class ManifestError(HarnessError):
    """Sample manifest validation failed."""


class ValidationError(HarnessError):
    """Input or output validation failed."""


class CommandError(HarnessError):
    """External command failed."""


class ResumeError(HarnessError):
    """A previous stage cannot be reused safely."""


class CleanupSafetyError(HarnessError):
    """A cleanup request targeted an unsafe path."""
