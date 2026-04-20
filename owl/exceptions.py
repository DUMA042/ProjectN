"""
owl.exceptions
~~~~~~~~~~~~~~
Custom exception hierarchy for the owl pipeline.

Raising typed exceptions at each pipeline layer makes downstream error handling
and logging deterministic — callers can catch a specific layer's error without
accidentally swallowing unrelated exceptions.

Hierarchy
---------
OwlBaseError
├── ExtractionError     — failures reading / parsing Excel files
├── TransformationError — data-cleaning or normalisation failures
│   └── ValidationError — Pydantic schema violations
├── LoadError           — database write failures
└── AnalysisError       — SQL / statistical modelling failures
"""


class OwlBaseError(Exception):
    """Root exception for all owl pipeline errors.

    Parameters
    ----------
    message:
        Human-readable description of the failure.
    context:
        Optional dict of extra diagnostic information (file name, sheet name,
        row number, column, etc.).  Logged alongside the message.
    """

    def __init__(self, message: str, context: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.context: dict = context or {}

    def __repr__(self) -> str:  # pragma: no cover
        ctx = f", context={self.context}" if self.context else ""
        return f"{type(self).__name__}(message={self.message!r}{ctx})"


# ── Layer 1: Extract ──────────────────────────────────────────────────────────

class ExtractionError(OwlBaseError):
    """Raised when a raw Excel file cannot be read or parsed."""


# ── Layer 2: Transform ────────────────────────────────────────────────────────

class TransformationError(OwlBaseError):
    """Raised when data cannot be cleaned or normalised."""


class ValidationError(TransformationError):
    """Raised when a Pydantic model rejects a row or record."""


# ── Layer 3: Load ─────────────────────────────────────────────────────────────

class LoadError(OwlBaseError):
    """Raised when normalised data cannot be persisted to the database."""


# ── Layer 4: Analyse ──────────────────────────────────────────────────────────

class AnalysisError(OwlBaseError):
    """Raised when a SQL query or statistical model fails."""
