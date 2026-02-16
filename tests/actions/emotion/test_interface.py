import pytest

from actions.emotion.interface import Emotion, EmotionAction, EmotionInput


@pytest.fixture
def default_input():
    """Create a default EmotionInput instance for tests."""
    return EmotionInput(action=EmotionAction.HAPPY)


class TestEmotionAction:
    """Tests for the EmotionAction enum."""

    def test_emotion_action_values(self):
        """Test that EmotionAction enum has the expected values."""
        assert EmotionAction.HAPPY.value == "happy"
        assert EmotionAction.SAD.value == "sad"
        assert EmotionAction.MAD.value == "mad"
        assert EmotionAction.CURIOUS.value == "curious"

    def test_emotion_action_count(self):
        """Test that EmotionAction has the expected number of actions."""
        assert len(EmotionAction) == 4


class TestEmotionInput:
    """Tests for the EmotionInput dataclass."""

    def test_emotion_input_accepts_all_actions(self):
        """Test EmotionInput can be created with each enum action."""
        for action in EmotionAction:
            value = EmotionInput(action=action)
            assert value.action == action


class TestEmotion:
    """Tests for the Emotion interface dataclass."""

    def test_emotion_creation(self, default_input):
        """Test Emotion can be created with matching input and output."""
        action = Emotion(input=default_input, output=default_input)
        assert action.input == default_input
        assert action.output == default_input
