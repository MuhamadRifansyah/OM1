"""Unit tests for ROS2PublisherProvider."""

from __future__ import annotations

import importlib.util
import logging
import sys
import time
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch


def _build_ros2_stubs() -> dict[str, Any]:
    """Build fake ROS2 modules required for provider import."""

    class FakeNode:
        """Minimal Node substitute for provider tests."""

        def __init__(self, _node_name: str):
            self._publisher = MagicMock()

        def create_publisher(
            self, _msg_type: Any, _topic: str, _qos_profile: int
        ) -> MagicMock:
            """Return a mock publisher instance."""
            return self._publisher

        def destroy_node(self) -> None:
            """No-op destroy hook used by Node interface."""
            return None

    def fake_string(data: str = "") -> Any:
        """Create a minimal std_msgs.msg.String-like object."""
        return SimpleNamespace(data=data)

    rclpy_module = MagicMock()
    rclpy_module.ok.return_value = True
    rclpy_module.init.return_value = None

    rclpy_node_module = ModuleType("rclpy.node")
    setattr(rclpy_node_module, "Node", FakeNode)

    std_msgs_module = ModuleType("std_msgs")
    std_msgs_msg_module = ModuleType("std_msgs.msg")
    setattr(std_msgs_msg_module, "String", fake_string)

    return {
        "rclpy": rclpy_module,
        "rclpy.node": rclpy_node_module,
        "std_msgs": std_msgs_module,
        "std_msgs.msg": std_msgs_msg_module,
    }


def _load_provider_module() -> Any:
    """Load provider module directly from file path for isolated tests."""
    module_path = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "providers"
        / "ros2_publisher_provider.py"
    )
    spec = importlib.util.spec_from_file_location(
        "ros2_publisher_provider_under_test",
        module_path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to create ros2_publisher_provider module spec")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _create_provider() -> Any:
    """Create a provider instance with ROS2 dependencies stubbed."""
    with patch.dict(sys.modules, _build_ros2_stubs()):
        provider_module = _load_provider_module()
        return provider_module.ROS2PublisherProvider("test_topic")


def _wait_until_published(publisher: MagicMock, timeout_sec: float = 1.0) -> bool:
    """Wait until a publish call is observed or timeout expires."""
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        if publisher.publish.call_count > 0:
            return True
        time.sleep(0.01)
    return False


def test_initialization() -> None:
    """Provider should initialize with stopped state."""
    provider = _create_provider()
    provider.stop()

    assert provider is not None
    assert provider.running is False


def test_add_pending_message_publishes() -> None:
    """Queued messages should be published by the worker thread."""
    provider = _create_provider()
    provider.start()

    try:
        provider.add_pending_message("Hello")
        published = _wait_until_published(provider.publisher_)
    finally:
        provider.stop()

    assert published is True


def test_start_sets_running_and_stop_clears_it() -> None:
    """Start should enable running state and stop should clear it."""
    provider = _create_provider()
    provider.start()
    provider.stop()

    assert provider.running is False


def test_start_is_idempotent_when_already_running() -> None:
    """Calling start twice should keep provider running without errors."""
    provider = _create_provider()
    provider.start()
    provider.start()
    provider.stop()

    assert provider.running is False


def test_stop_calls_close_when_available() -> None:
    """Stop should call publisher Close when cleanup contract is available."""
    provider = _create_provider()
    mock_publisher = MagicMock()
    provider.publisher_ = mock_publisher

    provider.stop()

    mock_publisher.Close.assert_called_once_with()


def test_stop_logs_when_close_not_available(caplog: Any) -> None:
    """Stop should log a warning when publisher has no Close method."""
    provider = _create_provider()
    provider.publisher_ = object()

    with caplog.at_level(logging.WARNING):
        provider.stop()

    assert "does not implement Close()" in caplog.text
