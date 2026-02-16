import pytest

from actions.emergency_alert.interface import EmergencyAlert, EmergencyAlertInput


@pytest.fixture
def default_input():
    """Create a default EmergencyAlertInput instance for tests."""
    return EmergencyAlertInput(action="fire detected")


class TestEmergencyAlertInput:
    """Tests for the EmergencyAlertInput dataclass."""

    def test_emergency_alert_input_creation(self):
        """Test creating EmergencyAlertInput with a message."""
        value = EmergencyAlertInput(action="evacuate immediately")
        assert value.action == "evacuate immediately"


class TestEmergencyAlert:
    """Tests for the EmergencyAlert interface dataclass."""

    def test_emergency_alert_creation(self, default_input):
        """Test EmergencyAlert can be created with matching input and output."""
        action = EmergencyAlert(input=default_input, output=default_input)
        assert action.input == default_input
        assert action.output == default_input
