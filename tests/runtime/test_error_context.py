"""
Tests for enhanced exception context and error handling.

Verifies that exceptions are properly contextualized with:
- Clear error context information
- Proper exception chaining
- Structured logging
- Component identification
"""

import logging
import pytest
from unittest.mock import MagicMock, patch

from runtime.error_context import (
    ErrorContext,
    ContextInfo,
    ContextualException,
    ExceptionContextManager,
    log_exception_with_context,
    format_exception_chain,
    extract_exception_info,
    handle_exception_context,
    wrap_with_exception_context,
)


class TestContextInfo:
    """Test ContextInfo data class."""

    def test_context_info_basic(self):
        """Test basic context info creation."""
        context = ContextInfo(
            error_context=ErrorContext.RUNTIME_STARTUP,
            operation="Initialize runtime",
        )

        assert context.error_context == ErrorContext.RUNTIME_STARTUP
        assert context.operation == "Initialize runtime"
        assert context.component is None

    def test_context_info_with_component(self):
        """Test context info with component name."""
        context = ContextInfo(
            error_context=ErrorContext.COMPONENT_INITIALIZATION,
            operation="Load input module",
            component="CameraInput",
        )

        assert context.component == "CameraInput"

    def test_context_info_to_message(self):
        """Test message formatting."""
        context = ContextInfo(
            error_context=ErrorContext.NETWORK_COMMUNICATION,
            operation="Connect to device",
            component="Unitree",
            details={"adapter": "eth0", "timeout": 30},
        )

        message = context.to_message()
        assert "network_communication" in message
        assert "Connect to device" in message
        assert "Unitree" in message


class TestContextualException:
    """Test ContextualException class."""

    def test_contextual_exception_basic(self):
        """Test creating contextual exception."""
        context = ContextInfo(
            error_context=ErrorContext.RUNTIME_STARTUP,
            operation="Initialize components",
        )

        cause = ValueError("Invalid config")
        exc = ContextualException(
            context=context,
            message="Failed to initialize",
            cause=cause,
        )

        assert isinstance(exc, Exception)
        assert exc.context == context
        assert exc.cause == cause

    def test_contextual_exception_message(self):
        """Test exception message formatting."""
        context = ContextInfo(
            error_context=ErrorContext.CONFIG_LOADING,
            operation="Parse config file",
            component="ConfigLoader",
        )

        cause = FileNotFoundError("config.json5 not found")
        exc = ContextualException(
            context=context,
            message="Configuration file missing",
            cause=cause,
        )

        message = str(exc)
        assert "config_loading" in message
        assert "Parse config file" in message
        assert "ConfigLoader" in message
        assert "Configuration file missing" in message


class TestFormatExceptionChain:
    """Test exception chain formatting."""

    def test_single_exception(self):
        """Test formatting single exception."""
        try:
            raise ValueError("Test error")
        except Exception as e:
            formatted = format_exception_chain(e)
            assert "ValueError" in formatted
            assert "Test error" in formatted

    def test_exception_chain(self):
        """Test formatting chained exceptions."""
        try:
            try:
                raise ValueError("Inner error")
            except ValueError as inner:
                raise RuntimeError("Outer error") from inner
        except Exception as e:
            formatted = format_exception_chain(e)
            assert "RuntimeError" in formatted
            assert "ValueError" in formatted
            assert "caused by" in formatted


class TestExceptionContextManager:
    """Test ExceptionContextManager class."""

    def test_manager_creation(self):
        """Test creating context manager."""
        logger = logging.getLogger(__name__)
        manager = ExceptionContextManager(logger, "TestComponent")

        assert manager.component_name == "TestComponent"
        assert manager.logger == logger

    def test_handle_exception_no_reraise(self, caplog):
        """Test handling exception without reraising."""
        logger = logging.getLogger(__name__)
        manager = ExceptionContextManager(logger, "TestComponent")

        with caplog.at_level(logging.ERROR):
            error = ValueError("Test error")
            result = manager.handle_exception(
                context=ErrorContext.RUNTIME_EXECUTION,
                operation="Test operation",
                exc=error,
                reraise=False,
            )

        # Should not have raised
        assert result is None
        # Should have logged
        assert "test_operation" in caplog.text.lower() or "Test operation" in caplog.text


class TestHandleExceptionContext:
    """Test handle_exception_context context manager."""

    def test_no_exception(self):
        """Test context manager with no exception."""
        logger = logging.getLogger(__name__)

        with handle_exception_context(
            logger=logger,
            context=ErrorContext.RUNTIME_STARTUP,
            operation="Initialize",
            reraise=False,
        ):
            result = 42

        # Should execute normally
        assert result == 42

    def test_exception_with_reraise(self):
        """Test exception with reraise enabled."""
        logger = logging.getLogger(__name__)

        with pytest.raises(ContextualException):
            with handle_exception_context(
                logger=logger,
                context=ErrorContext.COMPONENT_INITIALIZATION,
                operation="Load component",
                component="TestComponent",
                reraise=True,
            ):
                raise ValueError("Component load failed")

    def test_exception_without_reraise(self):
        """Test exception without reraise."""
        logger = logging.getLogger(__name__)

        # Should not raise
        with handle_exception_context(
            logger=logger,
            context=ErrorContext.CONFIG_LOADING,
            operation="Load config",
            reraise=False,
        ):
            raise ValueError("Config load failed")


class TestWrapWithExceptionContext:
    """Test wrap_with_exception_context decorator."""

    def test_successful_execution(self):
        """Test decorated function with successful execution."""
        logger = logging.getLogger(__name__)

        @wrap_with_exception_context(
            logger=logger,
            context=ErrorContext.RUNTIME_EXECUTION,
            operation="Execute operation",
            reraise=False,
        )
        def successful_function():
            return "success"

        result = successful_function()
        assert result == "success"

    def test_function_with_exception(self):
        """Test decorated function that raises exception."""
        logger = logging.getLogger(__name__)

        @wrap_with_exception_context(
            logger=logger,
            context=ErrorContext.CONNECTOR_EXECUTION,
            operation="Execute connector",
            component="TestConnector",
            reraise=True,
        )
        def failing_function():
            raise ValueError("Operation failed")

        with pytest.raises(ContextualException):
            failing_function()


class TestLogExceptionWithContext:
    """Test log_exception_with_context function."""

    def test_log_with_context(self, caplog):
        """Test logging exception with context."""
        logger = logging.getLogger(__name__)

        error = RuntimeError("Test error")
        with caplog.at_level(logging.ERROR):
            log_exception_with_context(
                logger=logger,
                context=ErrorContext.RUNTIME_EXECUTION,
                operation="Test operation",
                exc=error,
                component="TestComponent",
                details={"key": "value"},
            )

        # Should have logged
        assert caplog.records
        assert any(record.levelno == logging.ERROR for record in caplog.records)


class TestExtractExceptionInfo:
    """Test extract_exception_info function."""

    def test_extract_simple_exception(self):
        """Test extracting info from simple exception."""
        try:
            raise ValueError("Test error")
        except Exception as e:
            info = extract_exception_info(e)

            assert info["type"] == "ValueError"
            assert "Test error" in info["message"]
            assert "traceback" in info

    def test_extract_chained_exception(self):
        """Test extracting info from chained exception."""
        try:
            try:
                raise ValueError("Inner")
            except ValueError as inner:
                raise RuntimeError("Outer") from inner
        except Exception as e:
            info = extract_exception_info(e)

            assert info["type"] == "RuntimeError"
            assert "Outer" in info["message"]
            assert info["cause"] is not None


class TestErrorContextEnums:
    """Test ErrorContext enumeration."""

    def test_all_contexts_present(self):
        """Test that all expected contexts are defined."""
        assert ErrorContext.COMPONENT_INITIALIZATION
        assert ErrorContext.CONFIG_LOADING
        assert ErrorContext.CONFIG_VALIDATION
        assert ErrorContext.RUNTIME_STARTUP
        assert ErrorContext.RUNTIME_EXECUTION
        assert ErrorContext.RUNTIME_SHUTDOWN
        assert ErrorContext.CONNECTOR_EXECUTION
        assert ErrorContext.ORCHESTRATOR_OPERATION
        assert ErrorContext.LLM_INFERENCE
        assert ErrorContext.INPUT_PROCESSING
        assert ErrorContext.OUTPUT_EXECUTION
        assert ErrorContext.PLUGIN_LOADING
        assert ErrorContext.NETWORK_COMMUNICATION
        assert ErrorContext.FILE_OPERATION
        assert ErrorContext.ASYNC_TASK

    def test_context_values_are_strings(self):
        """Test that contexts have string values."""
        for context in ErrorContext:
            assert isinstance(context.value, str)
            assert len(context.value) > 0


class TestIntegration:
    """Integration tests for error handling."""

    def test_full_error_flow(self, caplog):
        """Test full error handling flow."""
        logger = logging.getLogger(__name__)

        with caplog.at_level(logging.ERROR):
            try:
                with handle_exception_context(
                    logger=logger,
                    context=ErrorContext.COMPONENT_INITIALIZATION,
                    operation="Initialize component",
                    component="TestComponent",
                    details={"version": "1.0"},
                    reraise=True,
                ):
                    raise ValueError("Initialization failed")
            except ContextualException as e:
                assert isinstance(e, Exception)
                assert e.context.component == "TestComponent"
                assert e.cause is not None

        assert caplog.records
