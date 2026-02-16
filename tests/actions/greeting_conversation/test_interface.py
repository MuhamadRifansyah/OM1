import pytest

from actions.greeting_conversation.interface import (
    ConversationState,
    GreetingConversation,
    GreetingConversationInput,
)


@pytest.fixture
def default_input():
    """Create a default GreetingConversationInput instance for tests."""
    return GreetingConversationInput(
        response="Hello there!",
        conversation_state=ConversationState.CONVERSING,
        confidence=0.9,
        speech_clarity=0.8,
    )


class TestConversationState:
    """Tests for the ConversationState enum."""

    def test_conversation_state_values(self):
        """Test that ConversationState enum has the expected values."""
        assert ConversationState.CONVERSING.value == "conversing"
        assert ConversationState.CONCLUDING.value == "concluding"
        assert ConversationState.FINISHED.value == "finished"

    def test_conversation_state_count(self):
        """Test that ConversationState has the expected number of states."""
        assert len(ConversationState) == 3


class TestGreetingConversationInput:
    """Tests for the GreetingConversationInput dataclass."""

    def test_greeting_conversation_input_creation(self):
        """Test creating GreetingConversationInput with explicit values."""
        value = GreetingConversationInput(
            response="Good morning",
            conversation_state=ConversationState.CONCLUDING,
            confidence=0.7,
            speech_clarity=0.6,
        )
        assert value.response == "Good morning"
        assert value.conversation_state == ConversationState.CONCLUDING
        assert value.confidence == 0.7
        assert value.speech_clarity == 0.6


class TestGreetingConversation:
    """Tests for the GreetingConversation interface dataclass."""

    def test_greeting_conversation_creation(self, default_input):
        """Test GreetingConversation can be created with matching input and output."""
        action = GreetingConversation(input=default_input, output=default_input)
        assert action.input == default_input
        assert action.output == default_input
