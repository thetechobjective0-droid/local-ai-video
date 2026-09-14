"""Domain-specific exceptions used by the local video pipeline."""


class VideoAgentError(Exception):
    """Base exception for expected application failures."""


class ConfigurationError(VideoAgentError):
    """Raised when application configuration is invalid."""


class ProviderUnavailableError(VideoAgentError):
    """Raised when a required local provider is unavailable."""


class InsufficientDiskError(VideoAgentError):
    """Raised when the configured storage location lacks enough free space."""


class OutOfMemoryRiskError(VideoAgentError):
    """Raised when a preflight check predicts unsafe memory pressure."""
