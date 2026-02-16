import pytest

from actions.tweet.interface import Tweet, TweetInput


@pytest.fixture
def default_input():
    """Create a default TweetInput instance for tests."""
    return TweetInput()


class TestTweetInput:
    """Tests for the TweetInput dataclass."""

    def test_default_action(self):
        """Test that action defaults to empty string."""
        value = TweetInput()
        assert value.action == ""

    def test_custom_action(self):
        """Test creating TweetInput with custom text."""
        value = TweetInput(action="Hello X")
        assert value.action == "Hello X"


class TestTweet:
    """Tests for the Tweet interface dataclass."""

    def test_tweet_creation(self, default_input):
        """Test Tweet can be created with matching input and output."""
        action = Tweet(input=default_input, output=default_input)
        assert action.input == default_input
        assert action.output == default_input
