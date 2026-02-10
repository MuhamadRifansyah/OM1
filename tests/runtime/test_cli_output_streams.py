from unittest.mock import MagicMock, patch

from cli import app
from typer.testing import CliRunner

runner = CliRunner(mix_stderr=False)


def test_validate_config_separates_stdout_stderr():
    """
    Test that validate_config writes diagnostics to stderr and the final
    success message to stdout.
    """
    # Mock configuration data
    mock_config = {
        "name": "test_config",
        "hertz": 10,
        "agent_inputs": [],
        "agent_actions": [],
    }

    # We need to mock several things to bypass file I/O and validation logic
    with patch(
        "cli._resolve_config_path", return_value="/abs/path/to/test.json5"
    ), patch("builtins.open", new_callable=MagicMock), patch(
        "cli.json5.load", return_value=mock_config
    ), patch(
        "cli.json.load", return_value={}
    ), patch(
        "cli.validate"
    ), patch(
        "cli._validate_components"
    ), patch(
        "cli._check_api_key"
    ):

        # Run the command with verbose flag to ensure we get diagnostic output
        result = runner.invoke(app, ["validate-config", "test", "--verbose"])

        # Assert the command succeeded
        assert (
            result.exit_code == 0
        ), f"Command failed with output: {result.stdout} {result.stderr}"

        # STDOUT assertions
        # The final success message should be on stdout
        assert "Configuration is valid!" in result.stdout
        # Diagnostics should NOT be on stdout
        assert "Validating:" not in result.stdout
        assert "JSON5 syntax valid" not in result.stdout

        # STDERR assertions
        # Diagnostics should be on stderr
        assert "Validating: /abs/path/to/test.json5" in result.stderr
        assert "JSON5 syntax valid" in result.stderr
        assert "Schema validation passed" in result.stderr
        assert "Detected single-mode configuration" in result.stderr

        assert "=" * 50 in result.stderr
        assert "=" * 50 not in result.stdout


def test_validate_config_error_output():
    """
    Test that validation errors are printed to stderr.
    """
    with patch(
        "cli._resolve_config_path", return_value="/abs/path/to/test.json5"
    ), patch("builtins.open", new_callable=MagicMock), patch(
        "cli.json5.load", side_effect=ValueError("Test JSON Error")
    ):

        result = runner.invoke(app, ["validate-config", "test"])

        assert result.exit_code == 1

        # Error details should be in stderr
        assert "Error: Invalid JSON5 syntax" in result.stderr
        assert "Test JSON Error" in result.stderr

        # Stdout should be empty or minimal (definitely not success message)
        assert "Configuration is valid!" not in result.stdout