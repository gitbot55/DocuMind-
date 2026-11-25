"""Custom exceptions used across services."""


class IngestionError(Exception):
    """A PDF could not be accepted (bad type, too big, unreadable, no text)."""


class LLMUnavailable(Exception):
    """The language model cannot be called (missing key or API error)."""
