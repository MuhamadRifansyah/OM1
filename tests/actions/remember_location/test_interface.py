import pytest

from actions.remember_location.interface import RememberLocation, RememberLocationInput


@pytest.fixture
def default_input():
    """Create a default RememberLocationInput instance for tests."""
    return RememberLocationInput(action="kitchen")


class TestRememberLocationInput:
    """Tests for the RememberLocationInput dataclass."""

    def test_default_description(self):
        """Test that description defaults to an empty string."""
        value = RememberLocationInput(action="office")
        assert value.action == "office"
        assert value.description == ""

    def test_custom_description(self):
        """Test creating RememberLocationInput with a custom description."""
        value = RememberLocationInput(action="garage", description="near charger")
        assert value.action == "garage"
        assert value.description == "near charger"


class TestRememberLocation:
    """Tests for the RememberLocation interface dataclass."""

    def test_creation(self, default_input):
        """Test RememberLocation can be created with matching input and output."""
        action = RememberLocation(input=default_input, output=default_input)
        assert action.input == default_input
        assert action.output == default_input
