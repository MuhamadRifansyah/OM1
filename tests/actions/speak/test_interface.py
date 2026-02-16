import pytest

from actions.speak.interface import Speak, SpeakInput


@pytest.fixture
def default_input():
    """Create a default SpeakInput instance for tests."""
    return SpeakInput(action="hello world")


class TestSpeakInput:
    """Tests for the SpeakInput dataclass."""

    def test_speak_input_creation(self):
        """Test creating SpeakInput with text."""
        value = SpeakInput(action="testing speech")
        assert value.action == "testing speech"


class TestSpeak:
    """Tests for the Speak interface dataclass."""

    def test_speak_creation(self, default_input):
        """Test Speak can be created with matching input and output."""
        action = Speak(input=default_input, output=default_input)
        assert action.input == default_input
        assert action.output == default_input

    def test_speak_creation_with_different_output(self):
        """Test Speak can be created with different input/output values."""
        input_value = SpeakInput(action="input text")
        output_value = SpeakInput(action="output text")
        action = Speak(input=input_value, output=output_value)
        assert action.input.action == "input text"
        assert action.output.action == "output text"
