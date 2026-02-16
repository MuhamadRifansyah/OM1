import pytest

from actions.move_ub.interface import Move, MoveInput, MovementAction


@pytest.fixture
def default_input():
    """Create a default MoveInput instance for tests."""
    return MoveInput(action=MovementAction.STAND_STILL)


class TestMovementAction:
    """Tests for the MovementAction enum."""

    def test_movement_action_values(self):
        """Test that key MovementAction enum values match expected strings."""
        assert MovementAction.WAVE.value == "wave"
        assert MovementAction.BOW.value == "bow"
        assert MovementAction.CROUCH.value == "crouch"
        assert MovementAction.COME.value == "come on"
        assert MovementAction.STAND_STILL.value == "reset"
        assert MovementAction.DO_NOTHING.value == "reset"
        assert MovementAction.WAKAWAKA.value == "WakaWaka"
        assert MovementAction.HUG.value == "Hug"
        assert MovementAction.RAISE_RIGHT_HAND.value == "RaiseRightHand"
        assert MovementAction.PUSH_UP.value == "PushUp"

    def test_movement_action_count(self):
        """Test that MovementAction has the expected number of unique actions."""
        assert len(MovementAction) == 17


class TestMoveInput:
    """Tests for the MoveInput dataclass."""

    def test_move_input_accepts_all_actions(self):
        """Test MoveInput can be created with each enum action."""
        for action in MovementAction:
            value = MoveInput(action=action)
            assert value.action == action


class TestMove:
    """Tests for the Move interface dataclass."""

    def test_move_creation(self, default_input):
        """Test Move can be created with matching input and output."""
        move = Move(input=default_input, output=default_input)
        assert move.input == default_input
        assert move.output == default_input
