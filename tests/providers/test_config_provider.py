"""Tests for ConfigProvider."""

import os
from unittest.mock import MagicMock, patch

import pytest

from providers.config_provider import ConfigProvider  # pylint: disable=import-error
from zenoh_msgs import String  # pylint: disable=import-error


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset singleton instances between tests."""
    ConfigProvider.reset()  # type: ignore[attr-defined]  # pylint: disable=no-member
    yield

    try:
        provider = ConfigProvider()
        provider.stop()
    except Exception:  # pylint: disable=broad-exception-caught
        pass

    ConfigProvider.reset()  # type: ignore[attr-defined]  # pylint: disable=no-member


@pytest.fixture(name="zenoh_mocks")
def _zenoh_mocks():
    """Provide mocked Zenoh session, publisher, and subscriber."""
    with patch("providers.config_provider.open_zenoh_session") as mock_session:
        mock_session_instance = MagicMock()
        mock_publisher = MagicMock()
        mock_subscriber = MagicMock()
        mock_session_instance.declare_publisher.return_value = mock_publisher
        mock_session_instance.declare_subscriber.return_value = mock_subscriber
        mock_session.return_value = mock_session_instance
        yield mock_session, mock_session_instance, mock_publisher, mock_subscriber


def test_initialization(zenoh_mocks):
    """Ensure ConfigProvider initializes Zenoh components."""
    _, mock_session_instance, mock_publisher, mock_subscriber = zenoh_mocks
    provider = ConfigProvider()

    assert provider.running
    assert provider.session == mock_session_instance
    assert provider.config_response_publisher == mock_publisher
    assert provider.config_request_subscriber == mock_subscriber

    mock_session_instance.declare_publisher.assert_called_once_with(
        "om/config/response"
    )
    mock_session_instance.declare_subscriber.assert_called_once()


def test_singleton_pattern():
    """Ensure ConfigProvider is a singleton."""
    provider1 = ConfigProvider()
    provider2 = ConfigProvider()
    assert provider1 is provider2


@pytest.mark.usefixtures("zenoh_mocks")
def test_get_runtime_config_path():
    """Ensure runtime config path points to memory .runtime.json5."""
    provider = ConfigProvider()
    config_path = provider._get_runtime_config_path()  # pylint: disable=protected-access

    assert config_path.endswith(".runtime.json5")
    assert "config/memory" in config_path


def test_initialization_failure():
    """Ensure initialization failure results in a non-running provider."""
    with patch("providers.config_provider.open_zenoh_session") as mock_session:
        mock_session.side_effect = Exception("Connection failed")
        provider = ConfigProvider()

        assert not provider.running
        assert provider.session is None


def test_stop(zenoh_mocks):
    """Ensure provider stop closes the Zenoh session."""
    _, mock_session_instance, _, _ = zenoh_mocks
    provider = ConfigProvider()

    provider.stop()

    assert not provider.running
    mock_session_instance.close.assert_called_once()


def test_handle_config_request(zenoh_mocks):
    """Test that config request handler is registered correctly."""
    _, mock_session_instance, _, _ = zenoh_mocks
    ConfigProvider()

    call_args = mock_session_instance.declare_subscriber.call_args
    assert call_args[0][0] == "om/config/request"
    assert callable(call_args[0][1])


@pytest.mark.usefixtures("zenoh_mocks")
def test_set_config_uses_unique_temp_file(tmp_path):
    """Test that _handle_set_config uses unique temp file names to prevent race condition."""
    provider = ConfigProvider()
    provider.config_path = str(tmp_path / ".runtime.json5")

    temp_paths_used = []
    original_rename = os.rename

    def track_rename(src, dst):
        temp_paths_used.append(src)
        return original_rename(src, dst)

    with patch("os.rename", side_effect=track_rename):
        with patch.object(provider, "_send_config_response"):
            provider._handle_set_config(  # pylint: disable=protected-access
                String("req1"), '{"key": "value1"}'
            )
            provider._handle_set_config(  # pylint: disable=protected-access
                String("req2"), '{"key": "value2"}'
            )

    assert len(temp_paths_used) == 2
    assert temp_paths_used[0] != temp_paths_used[1], (
        "Temp files should have unique names"
    )
    assert ".tmp." in temp_paths_used[0], "Temp file should contain .tmp. prefix"
    assert ".tmp." in temp_paths_used[1], "Temp file should contain .tmp. prefix"
