"""Tests for the Go2 autonomy idle connector."""

import asyncio
import importlib
from pathlib import Path
import sys
from unittest.mock import MagicMock, patch

import pytest


def _ensure_src_on_path() -> None:
    """Ensure src is importable when running linters directly."""
    src_path = Path(__file__).resolve().parents[4] / "src"
    src_path_str = str(src_path)
    if src_path_str not in sys.path:
        sys.path.insert(0, src_path_str)


@pytest.fixture(name="idle_context")
def fixture_idle_context(monkeypatch):
    """Import required modules after dependency mocking."""
    monkeypatch.setitem(sys.modules, "om1_speech", MagicMock())
    _ensure_src_on_path()
    sys.modules.pop("actions.base", None)
    sys.modules.pop("actions.move_go2_autonomy.interface", None)
    sys.modules.pop("actions.move_go2_autonomy.connector.idle", None)
    base_module = importlib.import_module("actions.base")
    interface_module = importlib.import_module("actions.move_go2_autonomy.interface")
    idle_module = importlib.import_module("actions.move_go2_autonomy.connector.idle")
    return {
        "idle_module": idle_module,
        "action_config_cls": base_module.ActionConfig,
        "move_input_cls": interface_module.MoveInput,
        "movement_action_cls": interface_module.MovementAction,
    }


def test_idle_connector_initialization(idle_context):
    """Test connector initialization with provided config."""
    config = idle_context["action_config_cls"]()

    connector = idle_context["idle_module"].IDLEConnector(config)

    assert connector.config is config


@pytest.mark.parametrize(
    "action_name",
    [
        "STAND_STILL",
        "MOVE_FORWARDS",
        "TURN_LEFT",
    ],
)
def test_connect_logs_and_returns_none(idle_context, action_name):
    """Test connect logs the idle message and returns None."""
    connector = idle_context["idle_module"].IDLEConnector(
        idle_context["action_config_cls"]()
    )
    action = getattr(idle_context["movement_action_cls"], action_name)
    output_interface = idle_context["move_input_cls"](action=action)

    with patch("actions.move_go2_autonomy.connector.idle.logging.info") as mock_info:
        result = asyncio.run(connector.connect(output_interface))

    assert result is None
    mock_info.assert_called_once_with("IDLE connector called, doing nothing.")
