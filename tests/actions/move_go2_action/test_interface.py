import pytest

from actions.move_go2_action.interface import Action, ActionInput, Move


@pytest.fixture
def default_input():
    """Create a default ActionInput instance for tests."""
    return ActionInput(action=Action.STAND_STILL)


class TestAction:
    """Tests for the Action enum."""

    def test_action_values(self):
        """Test that Action enum has the expected values."""
        assert Action.SHAKE_PAW.value == "shake paw"
        assert Action.DANCE.value == "dance"
        assert Action.STRETCH.value == "stretch"
        assert Action.STAND_STILL.value == "stand still"
        assert Action.DO_NOTHING.value == "stand still"

    def test_action_count(self):
        """Test that Action has the expected number of unique actions."""
        assert len(Action) == 4


class TestActionInput:
    """Tests for the ActionInput dataclass."""

    def test_action_input_accepts_all_actions(self):
        """Test ActionInput can be created with each enum action."""
        for action in Action:
            value = ActionInput(action=action)
            assert value.action == action


class TestMove:
    """Tests for the Move interface dataclass."""

    def test_move_creation(self, default_input):
        """Test Move can be created with matching input and output."""
        move = Move(input=default_input, output=default_input)
        assert move.input == default_input
        assert move.output == default_input
