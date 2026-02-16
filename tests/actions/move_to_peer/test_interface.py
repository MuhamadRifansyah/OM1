import pytest

from actions.move_to_peer.interface import MoveToPeer, MoveToPeerAction, MoveToPeerInput


@pytest.fixture
def idle_input():
    """Create a default MoveToPeerInput instance for tests."""
    return MoveToPeerInput(action=MoveToPeerAction.IDLE)


class TestMoveToPeerAction:
    """Tests for the MoveToPeerAction enum."""

    def test_move_to_peer_action_values(self):
        """Test that MoveToPeerAction enum has the expected values."""
        assert MoveToPeerAction.IDLE.value == "idle"
        assert MoveToPeerAction.NAVIGATE.value == "navigate"

    def test_move_to_peer_action_count(self):
        """Test that MoveToPeerAction has the expected number of actions."""
        assert len(MoveToPeerAction) == 2


class TestMoveToPeerInput:
    """Tests for the MoveToPeerInput dataclass."""

    def test_move_to_peer_input_accepts_all_actions(self):
        """Test MoveToPeerInput can be created with each enum action."""
        for action in MoveToPeerAction:
            value = MoveToPeerInput(action=action)
            assert value.action == action


class TestMoveToPeer:
    """Tests for the MoveToPeer interface dataclass."""

    def test_move_to_peer_creation(self, idle_input):
        """Test MoveToPeer can be created with matching input and output."""
        action = MoveToPeer(input=idle_input, output=idle_input)
        assert action.input == idle_input
        assert action.output == idle_input
