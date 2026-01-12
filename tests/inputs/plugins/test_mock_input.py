<<<<<<< HEAD
from queue import Queue
=======
import asyncio
import time
>>>>>>> 79d17ce5 (test(mock-input): move unit tests under tests/inputs/plugins)
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from inputs.base import Message
from inputs.plugins.mock_input import MockInput, MockSensorConfig


<<<<<<< HEAD
def test_initialization():
    """Test basic initialization."""
    with (
        patch("inputs.plugins.mock_input.IOProvider"),
        patch.object(MockInput, "_start_server_thread"),
    ):
        config = MockSensorConfig()
        sensor = MockInput(config=config)

        assert sensor.messages == []
        assert isinstance(sensor.message_buffer, Queue)
        assert sensor.host == "localhost"
        assert sensor.port == 8765


def test_initialization_with_custom_config():
    """Test initialization with custom configuration."""
    with (
        patch("inputs.plugins.mock_input.IOProvider"),
        patch.object(MockInput, "_start_server_thread"),
    ):
        config = MockSensorConfig(input_name="Custom Mock", host="0.0.0.0", port=9000)
        sensor = MockInput(config=config)

        assert sensor.descriptor_for_LLM == "Custom Mock"
        assert sensor.host == "0.0.0.0"
        assert sensor.port == 9000


@pytest.mark.asyncio
async def test_poll_with_message_in_buffer():
    """Test _poll when there's a message in buffer."""
    with (
        patch("inputs.plugins.mock_input.IOProvider"),
        patch.object(MockInput, "_start_server_thread"),
        patch("inputs.plugins.mock_input.asyncio.sleep", new=AsyncMock()),
    ):
        config = MockSensorConfig()
        sensor = MockInput(config=config)
        sensor.message_buffer.put("Test message")

        result = await sensor._poll()

        assert result == "Test message"


@pytest.mark.asyncio
async def test_poll_with_empty_buffer():
    """Test _poll when buffer is empty."""
    with (
        patch("inputs.plugins.mock_input.IOProvider"),
        patch.object(MockInput, "_start_server_thread"),
        patch("inputs.plugins.mock_input.asyncio.sleep", new=AsyncMock()),
    ):
        config = MockSensorConfig()
        sensor = MockInput(config=config)

        result = await sensor._poll()

        assert result is None


@pytest.mark.asyncio
async def test_raw_to_text_with_valid_input():
    """Test _raw_to_text with valid input."""
    with (
        patch("inputs.plugins.mock_input.IOProvider"),
        patch.object(MockInput, "_start_server_thread"),
        patch("inputs.plugins.mock_input.time.time", return_value=1234.0),
    ):
        config = MockSensorConfig()
        sensor = MockInput(config=config)

        result = await sensor._raw_to_text("Test message")

        assert result is not None
        assert result.timestamp == 1234.0
        assert result.message == "Test message"


@pytest.mark.asyncio
async def test_raw_to_text_with_none():
    """Test _raw_to_text with None input."""
    with (
        patch("inputs.plugins.mock_input.IOProvider"),
        patch.object(MockInput, "_start_server_thread"),
    ):
        config = MockSensorConfig()
        sensor = MockInput(config=config)

        result = await sensor._raw_to_text(None)
        assert result is None


def test_formatted_latest_buffer_with_messages():
    """Test formatted_latest_buffer with messages."""
    with (
        patch("inputs.plugins.mock_input.IOProvider"),
        patch.object(MockInput, "_start_server_thread"),
    ):
        config = MockSensorConfig()
        sensor = MockInput(config=config)
        sensor.io_provider = MagicMock()

        sensor.messages = [
            Message(timestamp=1000.0, message="Message 1"),
            Message(timestamp=1001.0, message="Message 2"),
        ]

        result = sensor.formatted_latest_buffer()

        assert result is not None
        assert "Message 1" in result or "Message 2" in result
        sensor.io_provider.add_input.assert_called()
        assert len(sensor.messages) == 0


def test_formatted_latest_buffer_empty():
    """Test formatted_latest_buffer with empty buffer."""
    with (
        patch("inputs.plugins.mock_input.IOProvider"),
        patch.object(MockInput, "_start_server_thread"),
    ):
        config = MockSensorConfig()
        sensor = MockInput(config=config)

        result = sensor.formatted_latest_buffer()
        assert result is None
=======
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
>>>>>>> 79d17ce5 (test(mock-input): move unit tests under tests/inputs/plugins)
