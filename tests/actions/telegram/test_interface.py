import pytest

from actions.telegram.interface import Telegram, TelegramInput


@pytest.fixture
def default_input():
    """Create a default TelegramInput instance for tests."""
    return TelegramInput()


class TestTelegramInput:
    """Tests for the TelegramInput dataclass."""

    def test_default_action(self):
        """Test that action defaults to empty string."""
        value = TelegramInput()
        assert value.action == ""

    def test_custom_action(self):
        """Test creating TelegramInput with custom text."""
        value = TelegramInput(action="send report")
        assert value.action == "send report"


class TestTelegram:
    """Tests for the Telegram interface dataclass."""

    def test_telegram_creation(self, default_input):
        """Test Telegram can be created with matching input and output."""
        action = Telegram(input=default_input, output=default_input)
        assert action.input == default_input
        assert action.output == default_input
