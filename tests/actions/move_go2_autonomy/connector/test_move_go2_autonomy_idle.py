import asyncio
from unittest.mock import patch

import pytest

from actions.base import ActionConfig
from actions.move_go2_autonomy.connector.idle import IDLEConnector
from actions.move_go2_autonomy.interface import MoveInput, MovementAction


@pytest.fixture
def config():
    """Create a default ActionConfig instance for tests."""
    return ActionConfig()


@pytest.fixture
def connector(config):
    """Create an IDLEConnector instance for tests."""
    return IDLEConnector(config)


@pytest.fixture
def move_input():
    """Create a default MoveInput instance for tests."""
    return MoveInput(action=MovementAction.STAND_STILL)


class TestIDLEConnector:
    """Tests for the IDLEConnector class."""

    def test_init_stores_config(self, connector, config):
        """Test that connector initialization stores the provided config."""
        assert connector.config == config

    def test_connect_logs_noop(self, connector, move_input):
        """Test connect logs no-op message and returns None."""
        with patch("actions.move_go2_autonomy.connector.idle.logging.info") as mock_log:
            result = asyncio.run(connector.connect(move_input))
            assert result is None
            mock_log.assert_called_once_with("IDLE connector called, doing nothing.")
