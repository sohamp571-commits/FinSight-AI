"""
custom_exceptions.py

Defines the FinSight AI exception hierarchy. Every module in the project
should raise one of these (instead of bare Exception) so that calling
code -- and Streamlit's UI layer -- can catch and handle errors
predictably.
"""


class FinSightBaseException(Exception):
    """Base class for all custom exceptions raised within FinSight AI."""

    def __init__(self, message: str = "An unexpected error occurred in FinSight AI."):
        self.message = message
        super().__init__(self.message)


# ==========================================================
# Configuration Errors
# ==========================================================
class ConfigurationError(FinSightBaseException):
    """Raised when a required configuration/environment value is missing or invalid."""

    def __init__(self, message: str = "Invalid or missing application configuration."):
        super().__init__(message)


# ==========================================================
# Database Errors
# ==========================================================
class DatabaseConnectionError(FinSightBaseException):
    """Raised when the application cannot establish a database connection."""

    def __init__(self, message: str = "Failed to connect to the MySQL database."):
        super().__init__(message)


class DatabaseQueryError(FinSightBaseException):
    """Raised when a database query fails to execute."""

    def __init__(self, message: str = "A database query failed to execute."):
        super().__init__(message)


class RecordNotFoundError(FinSightBaseException):
    """Raised when an expected database record does not exist."""

    def __init__(self, message: str = "The requested record was not found."):
        super().__init__(message)


class DuplicateRecordError(FinSightBaseException):
    """Raised when attempting to insert a record that violates a unique constraint."""

    def __init__(self, message: str = "A record with these details already exists."):
        super().__init__(message)


# ==========================================================
# Validation Errors
# ==========================================================
class ValidationError(FinSightBaseException):
    """Raised when user-supplied input fails validation rules."""

    def __init__(self, message: str = "Input validation failed."):
        super().__init__(message)


# ==========================================================
# Authentication / Authorization Errors (used from Phase 2 onward)
# ==========================================================
class AuthenticationError(FinSightBaseException):
    """Raised when login credentials are invalid."""

    def __init__(self, message: str = "Authentication failed."):
        super().__init__(message)


class AuthorizationError(FinSightBaseException):
    """Raised when a user attempts an action outside their role's permissions."""

    def __init__(self, message: str = "You are not authorized to perform this action."):
        super().__init__(message)


# ==========================================================
# External Service Errors (used from Phase 2 onward)
# ==========================================================
class ExternalAPIError(FinSightBaseException):
    """Raised when a third-party API (yfinance, NewsAPI, etc.) fails or times out."""

    def __init__(self, message: str = "An external service failed to respond correctly."):
        super().__init__(message)


class DataProcessingError(FinSightBaseException):
    """Raised when a data-processing / analytics pipeline step fails."""

    def __init__(self, message: str = "Failed to process the requested data."):
        super().__init__(message)
