import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from inputs.base import Message
from inputs.plugins.mock_input import MockInput, MockSensorConfig


@pytest.fixture
def mock_config():
    return MockSensorConfig(input_name="Test Mock Input", host="localhost", port=8765)


@pytest.fixture
def mock_input_instance(mock_config):
    # Patch IOProvider to avoid external dependencies
    with patch("inputs.plugins.mock_input.IOProvider"):
        plugin = MockInput(mock_config)
        # Mock _start_server to prevent actual WebSocket server startup
        plugin._start_server = AsyncMock()
        return plugin


@pytest.mark.asyncio
async def test_poll_waits_on_queue_and_returns_immediately(mock_input_instance):
    """
    Test that _poll returns data immediately when available in the buffer,
    verifying removal of artificial latency.
    """
    # Setup: Simulate server is already running to bypass initialization check
    mock_input_instance.server = MagicMock()

    expected_message = "test_message_payload"

    # Act: Put message in buffer
    await mock_input_instance.message_buffer.put(expected_message)

    # Measure execution time
    start_time = time.time()
    result = await mock_input_instance._poll()
    duration = time.time() - start_time

    # Assert
    assert result == expected_message
    # Verify no significant delay (e.g., < 0.1s) occurred
    assert duration < 0.1


@pytest.mark.asyncio
async def test_poll_initializes_server_lazily(mock_input_instance):
    """
    Test that _poll initializes the server if it hasn't been started.
    """
    # Setup: Server is None initially
    mock_input_instance.server = None

    # Mock _start_server to set self.server, simulating successful start.
    # This avoids the fallback sleep(1) in _poll.
    async def mock_start_server_side_effect():
        mock_input_instance.server = MagicMock()

    mock_input_instance._start_server.side_effect = mock_start_server_side_effect

    # Pre-fill buffer so _poll returns after server start
    await mock_input_instance.message_buffer.put("data")

    # Act
    await mock_input_instance._poll()

    # Assert
    mock_input_instance._start_server.assert_awaited_once()


@pytest.mark.asyncio
async def test_raw_to_text_returns_valid_message(mock_input_instance):
    """
    Test that _raw_to_text correctly converts string input to a Message object.
    """
    input_text = "hello world"

    result = await mock_input_instance._raw_to_text(input_text)

    assert isinstance(result, Message)
    assert result.message == input_text
    assert isinstance(result.timestamp, float)
    assert result.timestamp > 0


@pytest.mark.asyncio
async def test_raw_to_text_appends_to_buffer(mock_input_instance):
    """
    Test that raw_to_text processes input and appends it to the internal messages list.
    """
    input_text = "buffered data"

    # Ensure buffer is empty initially
    mock_input_instance.messages = []

    await mock_input_instance.raw_to_text(input_text)

    assert len(mock_input_instance.messages) == 1
    assert mock_input_instance.messages[0].message == input_text