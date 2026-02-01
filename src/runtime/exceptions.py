"""
Custom exceptions for the OM1 runtime.

This module defines domain-specific exceptions for different failure modes
to enable precise error handling and better error messaging.
"""


class ComponentValidationError(ValueError):
    """
    Raised when component validation fails.

    This exception indicates that one or more components referenced in the
    configuration could not be found or validated in the codebase.
    """

    pass


class ConfigurationError(ValueError):
    """
    Raised when configuration is invalid or incomplete.

    This exception indicates structural or semantic issues with configuration,
    such as missing required fields or invalid values.
    """

    pass
