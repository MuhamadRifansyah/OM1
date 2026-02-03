import logging
import sys
from types import ModuleType
from typing import Any

import pytest

from runtime.robotics import load_unitree


def _install_fake_unitree_channel(
    monkeypatch: Any, channel_factory_initialize: Any
) -> None:
    unitree = ModuleType("unitree")
    unitree.__path__ = []  # type: ignore
    unitree_sdk2py = ModuleType("unitree.unitree_sdk2py")
    unitree_sdk2py.__path__ = []  # type: ignore
    core = ModuleType("unitree.unitree_sdk2py.core")
    core.__path__ = []  # type: ignore
    channel = ModuleType("unitree.unitree_sdk2py.core.channel")
    channel.ChannelFactoryInitialize = channel_factory_initialize

    monkeypatch.setitem(sys.modules, "unitree", unitree)
    monkeypatch.setitem(sys.modules, "unitree.unitree_sdk2py", unitree_sdk2py)
    monkeypatch.setitem(sys.modules, "unitree.unitree_sdk2py.core", core)
    monkeypatch.setitem(sys.modules, "unitree.unitree_sdk2py.core.channel", channel)


def test_load_unitree_returns_early_when_none() -> None:
    load_unitree(None)


def test_load_unitree_logs_boot_message_on_success(
    monkeypatch: Any, caplog: Any
) -> None:
    called = {"value": False}

    def channel_factory_initialize(_domain_id: int, adapter: str) -> None:
        assert adapter == "eth0"
        called["value"] = True

    _install_fake_unitree_channel(monkeypatch, channel_factory_initialize)

    with caplog.at_level(logging.INFO):
        load_unitree("eth0")

    assert called["value"] is True
    assert "Using eth0 as the Unitree Network Ethernet Adapter" in caplog.text
    assert "Booting Unitree and CycloneDDS" in caplog.text
    assert "Continuing without Unitree DDS initialization" not in caplog.text


def test_load_unitree_does_not_log_boot_message_on_failure(
    monkeypatch: Any, caplog: Any
) -> None:
    def channel_factory_initialize(_domain_id: int, _adapter: str) -> None:
        raise RuntimeError("boom")

    _install_fake_unitree_channel(monkeypatch, channel_factory_initialize)

    with caplog.at_level(logging.INFO):
        load_unitree("eth0")

    assert (
        "Failed to initialize Unitree Ethernet channel for adapter eth0" in caplog.text
    )
    assert "Continuing without Unitree DDS initialization" in caplog.text
    assert "Booting Unitree and CycloneDDS" not in caplog.text
