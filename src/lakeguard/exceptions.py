from __future__ import annotations


class LakeGuardError(Exception):
    """Base user-facing error."""

class ConfigError(LakeGuardError):
    """Invalid configuration."""

class SourceError(LakeGuardError):
    """Source file cannot be read."""

class ColumnNotFoundError(LakeGuardError):
    """A configured field does not exist."""

class RuleExecutionError(LakeGuardError):
    """A rule cannot be evaluated."""

class ReportError(LakeGuardError):
    """A report cannot be written."""
