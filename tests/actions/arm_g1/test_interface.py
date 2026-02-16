import pytest

from actions.arm_g1.interface import Arm, ArmAction, ArmInput


@pytest.fixture
def default_input():
    """Create a default ArmInput instance for tests."""
    return ArmInput(action=ArmAction.IDLE)


class TestArmAction:
    """Tests for the ArmAction enum."""

    def test_arm_action_values(self):
        """Test that ArmAction enum has the expected values."""
        assert ArmAction.IDLE.value == "idle"
        assert ArmAction.LEFT_KISS.value == "left kiss"
        assert ArmAction.RIGHT_KISS.value == "right kiss"
        assert ArmAction.CLAP.value == "clap"
        assert ArmAction.HIGH_FIVE.value == "high five"
        assert ArmAction.SHAKE_HAND.value == "shake hand"
        assert ArmAction.HEART.value == "heart"
        assert ArmAction.HIGH_WAVE.value == "high wave"

    def test_arm_action_count(self):
        """Test that ArmAction has the expected number of actions."""
        assert len(ArmAction) == 8


class TestArmInput:
    """Tests for the ArmInput dataclass."""

    def test_arm_input_accepts_all_actions(self):
        """Test ArmInput can be created with each enum action."""
        for action in ArmAction:
            value = ArmInput(action=action)
            assert value.action == action


class TestArm:
    """Tests for the Arm interface dataclass."""

    def test_arm_creation(self, default_input):
        """Test Arm can be created with matching input and output."""
        action = Arm(input=default_input, output=default_input)
        assert action.input == default_input
        assert action.output == default_input
