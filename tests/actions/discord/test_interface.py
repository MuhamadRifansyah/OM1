import pytest

from actions.discord.interface import Discord, DiscordInput


@pytest.fixture
def default_input():
    """Create a default DiscordInput instance for tests."""
    return DiscordInput()


class TestDiscordInput:
    """Tests for the DiscordInput dataclass."""

    def test_default_action(self):
        """Test that action defaults to empty string."""
        value = DiscordInput()
        assert value.action == ""

    def test_custom_action(self):
        """Test creating DiscordInput with custom text."""
        value = DiscordInput(action="status update")
        assert value.action == "status update"


class TestDiscord:
    """Tests for the Discord interface dataclass."""

    def test_discord_creation(self, default_input):
        """Test Discord can be created with matching input and output."""
        action = Discord(input=default_input, output=default_input)
        assert action.input == default_input
        assert action.output == default_input
