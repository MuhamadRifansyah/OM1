"""
Enhanced exception context and structured error handling utilities.

This module provides utilities for improving exception handling with:
- Contextual information about where and why errors occur
- Consistent error message formatting
- Chain of causation tracking
- Structured logging with context

This enables better diagnostics, faster debugging, and improved user experience
when runtime errors occur.
"""

import logging
import traceback
import sys
from typing import Optional, Any, Callable, TypeVar, cast
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum


# Type variable for generic function decoration
F = TypeVar("F", bound=Callable[..., Any])


class ErrorContext(str, Enum):
    """Enumeration of common error contexts in the OM1 runtime."""

    COMPONENT_INITIALIZATION = "component_initialization"
    CONFIG_LOADING = "config_loading"
    CONFIG_VALIDATION = "config_validation"
    RUNTIME_STARTUP = "runtime_startup"
    RUNTIME_EXECUTION = "runtime_execution"
    RUNTIME_SHUTDOWN = "runtime_shutdown"
    CONNECTOR_EXECUTION = "connector_execution"
    ORCHESTRATOR_OPERATION = "orchestrator_operation"
    LLM_INFERENCE = "llm_inference"
    INPUT_PROCESSING = "input_processing"
    OUTPUT_EXECUTION = "output_execution"
    PLUGIN_LOADING = "plugin_loading"
    NETWORK_COMMUNICATION = "network_communication"
    FILE_OPERATION = "file_operation"
    ASYNC_TASK = "async_task"


@dataclass
class ContextInfo:
    """Structured context information for exceptions."""

    error_context: ErrorContext
    operation: str
    component: Optional[str] = None
    details: Optional[dict[str, Any]] = None
    parent_exception: Optional[Exception] = None

    def to_message(self) -> str:
        """Format context into a human-readable message."""
        msg = f"[{self.error_context.value}] {self.operation}"

        if self.component:
            msg += f" (component: {self.component})"

        if self.details:
            detail_str = ", ".join(
                f"{k}={v}" for k, v in self.details.items() if v is not None
            )
            if detail_str:
                msg += f" [{detail_str}]"

        return msg


class ContextualException(Exception):
    """Exception with structured context information."""

    def __init__(
        self,
        context: ContextInfo,
        message: str,
        cause: Optional[Exception] = None,
    ):
        """
        Initialize contextual exception.

        Parameters
        ----------
        context : ContextInfo
            Structured context information about the error
        message : str
            Human-readable error message
        cause : Exception, optional
            The original exception that caused this error
        """
        self.context = context
        self.cause = cause
        self.message = message

        # Build full error message with context
        full_message = f"{context.to_message()}\n{message}"
        if cause:
            full_message += f"\nCause: {type(cause).__name__}: {str(cause)}"

        super().__init__(full_message)

    def __str__(self) -> str:
        """Return formatted error message."""
        return self.args[0] if self.args else self.message


def format_exception_chain(exc: Exception) -> str:
    """
    Format exception with full chain of causation.

    Parameters
    ----------
    exc : Exception
        The exception to format

    Returns
    -------
    str
        Formatted exception chain
    """
    lines = []
    current: Optional[Exception] = exc

    while current is not None:
        lines.append(f"{type(current).__name__}: {str(current)}")

        if hasattr(current, "__cause__") and current.__cause__:
            current = current.__cause__
        elif hasattr(current, "__context__") and current.__context__:
            current = current.__context__
        else:
            break

    return "\n  caused by: ".join(lines)


def log_exception_with_context(
    logger: logging.Logger,
    context: ErrorContext,
    operation: str,
    exc: Exception,
    component: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
    level: int = logging.ERROR,
) -> None:
    """
    Log exception with structured context information.

    Parameters
    ----------
    logger : logging.Logger
        Logger instance to use
    context : ErrorContext
        The error context
    operation : str
        Description of the operation that failed
    exc : Exception
        The exception that occurred
    component : str, optional
        Name of the component involved
    details : dict, optional
        Additional context details
    level : int, optional
        Logging level (default: ERROR)
    """
    context_info = ContextInfo(
        error_context=context,
        operation=operation,
        component=component,
        details=details,
    )

    formatted_chain = format_exception_chain(exc)

    logger.log(
        level,
        f"{context_info.to_message()}\n{formatted_chain}",
        exc_info=False,
    )


@contextmanager
def handle_exception_context(
    logger: logging.Logger,
    context: ErrorContext,
    operation: str,
    component: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
    reraise: bool = False,
):
    """
    Context manager for exception handling with contextual logging.

    Parameters
    ----------
    logger : logging.Logger
        Logger to use for error reporting
    context : ErrorContext
        The error context
    operation : str
        Description of the operation
    component : str, optional
        Component name
    details : dict, optional
        Additional context details
    reraise : bool, optional
        Whether to reraise the exception after logging (default: False)

    Yields
    ------
    None

    Raises
    ------
    ContextualException
        If reraise is True and an exception occurs
    """
    try:
        yield
    except Exception as exc:
        log_exception_with_context(
            logger,
            context=context,
            operation=operation,
            exc=exc,
            component=component,
            details=details,
        )

        if reraise:
            context_info = ContextInfo(
                error_context=context,
                operation=operation,
                component=component,
                details=details,
                parent_exception=exc,
            )
            raise ContextualException(
                context=context_info,
                message=str(exc),
                cause=exc,
            ) from exc


def wrap_with_exception_context(
    logger: logging.Logger,
    context: ErrorContext,
    operation: str,
    component: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
    reraise: bool = True,
) -> Callable[[F], F]:
    """
    Decorator for wrapping functions with exception context handling.

    Parameters
    ----------
    logger : logging.Logger
        Logger to use for error reporting
    context : ErrorContext
        The error context
    operation : str
        Description of the operation
    component : str, optional
        Component name
    details : dict, optional
        Additional context details
    reraise : bool, optional
        Whether to reraise exceptions (default: True)

    Returns
    -------
    Callable
        Decorator function

    Examples
    --------
    @wrap_with_exception_context(
        logger,
        ErrorContext.COMPONENT_INITIALIZATION,
        "Initializing camera input",
        component="CameraInput"
    )
    def initialize_camera(device_id: int):
        ...
    """

    def decorator(func: F) -> F:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with handle_exception_context(
                logger=logger,
                context=context,
                operation=operation,
                component=component,
                details=details,
                reraise=reraise,
            ):
                return func(*args, **kwargs)

        return cast(F, wrapper)

    return decorator


class ExceptionContextManager:
    """
    Manages exception context for a module or component.

    Provides consistent exception handling across related operations.
    """

    def __init__(self, logger: logging.Logger, component_name: str):
        """
        Initialize exception context manager.

        Parameters
        ----------
        logger : logging.Logger
            Logger instance for this component
        component_name : str
            Name of the component using this manager
        """
        self.logger = logger
        self.component_name = component_name

    def handle_exception(
        self,
        context: ErrorContext,
        operation: str,
        exc: Exception,
        details: Optional[dict[str, Any]] = None,
        reraise: bool = False,
    ) -> Optional[ContextualException]:
        """
        Handle exception with context.

        Parameters
        ----------
        context : ErrorContext
            The error context
        operation : str
            Description of the operation
        exc : Exception
            The exception to handle
        details : dict, optional
            Additional context details
        reraise : bool, optional
            Whether to reraise the exception

        Returns
        -------
        ContextualException or None
            The contextual exception (if not reraised)

        Raises
        ------
        ContextualException
            If reraise is True
        """
        log_exception_with_context(
            logger=self.logger,
            context=context,
            operation=operation,
            exc=exc,
            component=self.component_name,
            details=details,
        )

        if reraise:
            context_info = ContextInfo(
                error_context=context,
                operation=operation,
                component=self.component_name,
                details=details,
                parent_exception=exc,
            )
            contextual_exc = ContextualException(
                context=context_info,
                message=str(exc),
                cause=exc,
            )
            raise contextual_exc from exc

        return None

    def context(
        self,
        error_context: ErrorContext,
        operation: str,
        details: Optional[dict[str, Any]] = None,
        reraise: bool = False,
    ):
        """
        Return a context manager for exception handling.

        Parameters
        ----------
        error_context : ErrorContext
            The error context
        operation : str
            Description of the operation
        details : dict, optional
            Additional context details
        reraise : bool, optional
            Whether to reraise exceptions

        Returns
        -------
        contextmanager
            Context manager for the operation
        """
        return handle_exception_context(
            logger=self.logger,
            context=error_context,
            operation=operation,
            component=self.component_name,
            details=details,
            reraise=reraise,
        )


def extract_exception_info(exc: Exception) -> dict[str, Any]:
    """
    Extract structured information from an exception.

    Parameters
    ----------
    exc : Exception
        The exception to analyze

    Returns
    -------
    dict
        Dictionary with exception information including:
        - type: Exception class name
        - message: Exception message
        - module: Module where exception was raised
        - line: Line number (if available)
        - traceback: Formatted traceback
    """
    tb = sys.exc_info()[2]
    tb_lines = traceback.format_exception(type(exc), exc, tb)

    return {
        "type": type(exc).__name__,
        "message": str(exc),
        "module": exc.__class__.__module__,
        "traceback": "".join(tb_lines),
        "cause": (
            format_exception_chain(exc) if exc.__cause__ or exc.__context__ else None
        ),
    }
