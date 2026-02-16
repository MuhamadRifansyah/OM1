import pytest

from actions.move_serial_arduino.interface import Move, MoveInput, MovementAction


@pytest.fixture
def default_input():
    """Create a default MoveInput instance for tests."""
    return MoveInput(action=MovementAction.BE_STILL)


class TestMovementAction:
    """Tests for the MovementAction enum."""

    def test_movement_action_values(self):
        """Test that MovementAction enum has the expected values."""
        assert MovementAction.BE_STILL.value == "be still"
        assert MovementAction.JUMP_SMALL.value == "small jump"
        assert MovementAction.JUMP_MEDIUM.value == "medium jump"
        assert MovementAction.JUMP_BIG.value == "big jump"

    def test_movement_action_count(self):
        """Test that MovementAction has the expected number of actions."""
        assert len(MovementAction) == 4


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
