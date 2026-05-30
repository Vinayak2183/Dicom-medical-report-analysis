"""Domain-specific exceptions."""


class DicomProcessingError(Exception):
    """Raised when DICOM input cannot be parsed or processed."""


class AIProviderError(Exception):
    """Raised when the configured AI provider fails."""
