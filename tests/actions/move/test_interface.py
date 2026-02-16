import pytest

from actions.move.interface import Move, MoveInput, MovementAction


@pytest.fixture
def default_input():
    """Create a default MoveInput instance for tests."""
    return MoveInput(action=MovementAction.STAND_STILL)


class TestMovementAction:
    """Tests for the MovementAction enum."""

    def test_movement_action_values(self):
        """Test that MovementAction enum has the expected values."""
        assert MovementAction.STAND_STILL.value == "stand still"
        assert MovementAction.SIT.value == "sit"
        assert MovementAction.DANCE.value == "dance"
        assert MovementAction.SHAKE_PAW.value == "shake paw"
        assert MovementAction.WALK.value == "walk"
        assert MovementAction.WALK_BACK.value == "walk back"
        assert MovementAction.RUN.value == "run"
        assert MovementAction.JUMP.value == "jump"
        assert MovementAction.WAG_TAIL.value == "wag tail"

    def test_movement_action_count(self):
        """Test that MovementAction has the expected number of actions."""
        assert len(MovementAction) == 9


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
