import pytest

from actions.selfie.interface import Selfie, SelfieInput


@pytest.fixture
def default_input():
    """Create a default SelfieInput instance for tests."""
    return SelfieInput(action="wendy")


class TestSelfieInput:
    """Tests for the SelfieInput dataclass."""

    def test_default_timeout(self):
        """Test that timeout_sec defaults to 5."""
        value = SelfieInput(action="alex")
        assert value.action == "alex"
        assert value.timeout_sec == 5

    def test_custom_timeout(self):
        """Test that timeout_sec can be overridden."""
        value = SelfieInput(action="alex", timeout_sec=12)
        assert value.timeout_sec == 12


class TestSelfie:
    """Tests for the Selfie interface dataclass."""

    def test_selfie_creation(self, default_input):
        """Test Selfie can be created with matching input and output."""
        action = Selfie(input=default_input, output=default_input)
        assert action.input == default_input
        assert action.output == default_input
