import pytest

from actions.tesla_dimo.interface import DIMOTesla, TeslaAction, TeslaInput


@pytest.fixture
def default_input():
    """Create a default TeslaInput instance for tests."""
    return TeslaInput(action=TeslaAction.IDLE)


class TestTeslaAction:
    """Tests for the TeslaAction enum."""

    def test_tesla_action_values(self):
        """Test that TeslaAction enum has the expected values."""
        assert TeslaAction.IDLE.value == "idle"
        assert TeslaAction.LOCK_DOORS.value == "lock doors"
        assert TeslaAction.UNLOCK_DOORS.value == "unlock doors"
        assert TeslaAction.OPEN_FRUNK.value == "open frunk"
        assert TeslaAction.OPEN_TRUNK.value == "open trunk"

    def test_tesla_action_count(self):
        """Test that TeslaAction has the expected number of actions."""
        assert len(TeslaAction) == 5


class TestTeslaInput:
    """Tests for the TeslaInput dataclass."""

    def test_tesla_input_accepts_all_actions(self):
        """Test TeslaInput can be created with each enum action."""
        for action in TeslaAction:
            value = TeslaInput(action=action)
            assert value.action == action


class TestDIMOTesla:
    """Tests for the DIMOTesla interface dataclass."""

    def test_dimo_tesla_creation(self, default_input):
        """Test DIMOTesla can be created with matching input and output."""
        action = DIMOTesla(input=default_input, output=default_input)
        assert action.input == default_input
        assert action.output == default_input
