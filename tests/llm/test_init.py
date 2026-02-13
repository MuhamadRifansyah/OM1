"""Unit tests for LLM plugin loading and configuration helpers."""

import types
from unittest.mock import mock_open, patch

import pytest
from pydantic import BaseModel

from llm import LLM, LLMConfig, find_module_with_class, load_llm
from providers.io_provider import IOProvider
from runtime.config import _MetaDefaults, add_meta


class MockLLM(LLM[BaseModel]):
    """Minimal concrete LLM subclass for test coverage."""

    async def ask(self, prompt: str, messages=None) -> BaseModel:
        """Raise by default to validate abstract contract behavior."""
        raise NotImplementedError

    def ping(self) -> str:
        """Provide a second public method for pylint design checks."""
        return "ok"


@pytest.fixture(name="llm_config")
def fixture_llm_config():
    """Build a minimal LLM config fixture."""
    return LLMConfig(base_url="test_url", api_key="test_key", model="test_model")


@pytest.fixture(name="base_llm")
def fixture_base_llm(llm_config):
    """Create a concrete test LLM instance."""
    return MockLLM(llm_config, available_actions=None)


def test_llm_init(base_llm, llm_config):
    """Verify basic LLM object initialization."""
    assert getattr(base_llm, "_config") == llm_config
    assert isinstance(base_llm.io_provider, type(IOProvider()))


@pytest.mark.asyncio
async def test_llm_ask_not_implemented(base_llm):
    """Ensure default mock ask implementation raises NotImplementedError."""
    with pytest.raises(NotImplementedError):
        await base_llm.ask("test prompt")


def test_llm_config():
    """Validate metadata merge behavior for ad-hoc LLM config fields."""
    llm_config = LLMConfig(
        **add_meta(  # type: ignore
            {
                "config_key": "config_value",
            },
            _MetaDefaults(
                api_key=None,
                unitree_ethernet=None,
                urid=None,
                robot_ip=None,
            ),
        )
    )
    assert llm_config.config_key == "config_value"  # type: ignore
    with pytest.raises(
        AttributeError, match="'LLMConfig' object has no attribute 'invalid_key'"
    ):
        getattr(llm_config, "invalid_key")


def test_load_llm_mock_implementation():
    """Verify load_llm returns a plugin instance for a valid plugin module."""
    with (
        patch("llm.find_module_with_class") as mock_find_module,
        patch("llm.importlib.import_module") as mock_import,
    ):
        mock_find_module.return_value = "mock_llm"
        mock_module = types.ModuleType("mock_llm")
        setattr(mock_module, "MockLLM", MockLLM)
        mock_import.return_value = mock_module

        result = load_llm({"type": "MockLLM"})

        mock_find_module.assert_called_once_with("MockLLM")
        mock_import.assert_called_once_with("llm.plugins.mock_llm")
        assert isinstance(result, LLM)


def test_load_llm_not_found():
    """Verify missing LLM plugin names raise a clear ValueError."""
    with patch("llm.find_module_with_class") as mock_find_module:
        mock_find_module.return_value = None

        with pytest.raises(
            ValueError,
            match="Class 'NonexistentLLM' not found in .*LLM plugin module",
        ):
            load_llm({"type": "NonexistentLLM"})


def test_load_llm_invalid_type():
    """Verify non-LLM classes discovered in plugins raise ValueError."""
    with (
        patch("llm.find_module_with_class") as mock_find_module,
        patch("llm.importlib.import_module") as mock_import,
    ):
        mock_find_module.return_value = "invalid_llm"
        mock_module = types.ModuleType("invalid_llm")
        setattr(mock_module, "InvalidLLM", str)
        mock_import.return_value = mock_module

        with pytest.raises(
            ValueError, match="'InvalidLLM' is not a valid LLM subclass"
        ):
            load_llm({"type": "InvalidLLM"})


def test_find_module_with_class_success():
    """Verify class scanner returns module name when class exists."""
    with (
        patch("os.path.join") as mock_join,
        patch("os.path.exists") as mock_exists,
        patch("os.listdir") as mock_listdir,
        patch("builtins.open", mock_open(read_data="class TestLLM(LLM):\n    pass\n")),
    ):
        mock_join.side_effect = lambda *args: "/".join(args)
        mock_exists.return_value = True
        mock_listdir.return_value = ["test_llm.py"]

        result = find_module_with_class("TestLLM")

        assert result == "test_llm"


def test_find_module_with_class_not_found():
    """Verify class scanner returns None when class is absent."""
    with (
        patch("os.path.join") as mock_join,
        patch("os.path.exists") as mock_exists,
        patch("os.listdir") as mock_listdir,
        patch("builtins.open", mock_open(read_data="class OtherClass:\n    pass\n")),
    ):
        mock_join.side_effect = lambda *args: "/".join(args)
        mock_exists.return_value = True
        mock_listdir.return_value = ["other_file.py"]

        result = find_module_with_class("TestLLM")

        assert result is None


def test_find_module_with_class_no_plugins_dir():
    """Verify class scanner returns None when plugin directory is missing."""
    with patch("os.path.exists") as mock_exists:
        mock_exists.return_value = False

        result = find_module_with_class("TestLLM")

        assert result is None
