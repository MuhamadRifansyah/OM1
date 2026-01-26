"""
Registry and validation utilities for OM1 components.

Provides discovery and validation of available inputs, actions, simulators,
backgrounds, and LLM providers in the codebase.
"""

import importlib
import inspect
import logging
import os
import re
import typing as T

from actions.base import AgentAction
from backgrounds.base import Background
from inputs.base import Sensor
from llm import LLM
from simulators.base import Simulator


def _get_plugins_directory(component_type: str) -> str:
    """
    Get the plugins directory for a component type.

    Parameters
    ----------
    component_type : str
        Type of component: 'inputs', 'actions', 'simulators', 'backgrounds', or 'llm'

    Returns
    -------
    str
        Path to the plugins directory
    """
    src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if component_type == "actions":
        return os.path.join(src_dir, "actions")
    elif component_type == "llm":
        return os.path.join(src_dir, "llm", "plugins")
    else:
        return os.path.join(src_dir, component_type, "plugins")


def discover_available_inputs() -> T.Dict[str, str]:
    """
    Discover all available input sensor classes.

    Returns
    -------
    Dict[str, str]
        Mapping of class name to module file name
    """
    plugins_dir = _get_plugins_directory("inputs")
    available = {}

    if not os.path.exists(plugins_dir):
        return available

    for plugin_file in os.listdir(plugins_dir):
        if not plugin_file.endswith(".py") or plugin_file.startswith("_"):
            continue

        file_path = os.path.join(plugins_dir, plugin_file)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Find FuserInput or Sensor classes
            pattern = r"^class\s+(\w+)\s*\([^)]*(?:FuserInput|Sensor)[^)]*\)\s*:"
            matches = re.findall(pattern, content, re.MULTILINE)

            for class_name in matches:
                if class_name not in ["FuserInput", "Sensor"]:
                    available[class_name] = plugin_file[:-3]

        except Exception as e:
            logging.debug(f"Could not scan {plugin_file}: {e}")

    return available


def discover_available_actions() -> T.Dict[str, str]:
    """
    Discover all available action directories.

    Returns
    -------
    Dict[str, str]
        Mapping of action name to directory path
    """
    actions_dir = _get_plugins_directory("actions")
    available = {}

    if not os.path.exists(actions_dir):
        return available

    for item in os.listdir(actions_dir):
        item_path = os.path.join(actions_dir, item)
        if os.path.isdir(item_path) and not item.startswith("_"):
            # Check if interface.py exists
            interface_path = os.path.join(item_path, "interface.py")
            if os.path.exists(interface_path):
                available[item] = item_path

    return available


def discover_available_simulators() -> T.Dict[str, str]:
    """
    Discover all available simulator classes.

    Returns
    -------
    Dict[str, str]
        Mapping of class name to module file name
    """
    plugins_dir = _get_plugins_directory("simulators")
    available = {}

    if not os.path.exists(plugins_dir):
        return available

    for plugin_file in os.listdir(plugins_dir):
        if not plugin_file.endswith(".py") or plugin_file.startswith("_"):
            continue

        file_path = os.path.join(plugins_dir, plugin_file)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            pattern = r"^class\s+(\w+)\s*\([^)]*Simulator[^)]*\)\s*:"
            matches = re.findall(pattern, content, re.MULTILINE)

            for class_name in matches:
                if class_name != "Simulator":
                    available[class_name] = plugin_file[:-3]

        except Exception as e:
            logging.debug(f"Could not scan {plugin_file}: {e}")

    return available


def discover_available_backgrounds() -> T.Dict[str, str]:
    """
    Discover all available background classes.

    Returns
    -------
    Dict[str, str]
        Mapping of class name to module file name
    """
    plugins_dir = _get_plugins_directory("backgrounds")
    available = {}

    if not os.path.exists(plugins_dir):
        return available

    for plugin_file in os.listdir(plugins_dir):
        if not plugin_file.endswith(".py") or plugin_file.startswith("_"):
            continue

        file_path = os.path.join(plugins_dir, plugin_file)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            pattern = r"^class\s+(\w+)\s*\([^)]*Background[^)]*\)\s*:"
            matches = re.findall(pattern, content, re.MULTILINE)

            for class_name in matches:
                if class_name != "Background":
                    available[class_name] = plugin_file[:-3]

        except Exception as e:
            logging.debug(f"Could not scan {plugin_file}: {e}")

    return available


def discover_available_llms() -> T.Dict[str, str]:
    """
    Discover all available LLM provider classes.

    Returns
    -------
    Dict[str, str]
        Mapping of LLM class name to module file name
    """
    plugins_dir = _get_plugins_directory("llm")
    available = {}

    if not os.path.exists(plugins_dir):
        return available

    for plugin_file in os.listdir(plugins_dir):
        if not plugin_file.endswith(".py") or plugin_file.startswith("_"):
            continue

        file_path = os.path.join(plugins_dir, plugin_file)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            pattern = r"^class\s+(\w+)\s*\([^)]*LLM[^)]*\)\s*:"
            matches = re.findall(pattern, content, re.MULTILINE)

            for class_name in matches:
                if class_name != "LLM":
                    available[class_name] = plugin_file[:-3]

        except Exception as e:
            logging.debug(f"Could not scan {plugin_file}: {e}")

    return available


def validate_input_type(input_type: str) -> None:
    """
    Validate that an input type exists.

    Parameters
    ----------
    input_type : str
        The input type (usually a class name)

    Raises
    ------
    ValueError
        If the input type is not found
    """
    available = discover_available_inputs()
    if input_type not in available:
        available_list = sorted(available.keys())
        raise ValueError(
            f"Input type '{input_type}' not found.\n"
            f"Available input types: {', '.join(available_list)}"
        )


def validate_action_name(action_name: str) -> None:
    """
    Validate that an action exists.

    Parameters
    ----------
    action_name : str
        The action name (directory name)

    Raises
    ------
    ValueError
        If the action is not found
    """
    available = discover_available_actions()
    if action_name not in available:
        available_list = sorted(available.keys())
        raise ValueError(
            f"Action '{action_name}' not found.\n"
            f"Available actions: {', '.join(available_list)}"
        )


def validate_action_connector(action_name: str, connector_name: str) -> None:
    """
    Validate that an action connector exists.

    Parameters
    ----------
    action_name : str
        The action name (directory name)
    connector_name : str
        The connector module name

    Raises
    ------
    ValueError
        If the connector is not found
    """
    action_path = os.path.join(_get_plugins_directory("actions"), action_name)
    connector_path = os.path.join(action_path, "connector", f"{connector_name}.py")

    if not os.path.exists(connector_path):
        # List available connectors
        connector_dir = os.path.join(action_path, "connector")
        available_connectors = []
        if os.path.exists(connector_dir):
            available_connectors = [
                f[:-3]
                for f in os.listdir(connector_dir)
                if f.endswith(".py") and not f.startswith("_")
            ]

        raise ValueError(
            f"Connector '{connector_name}' not found for action '{action_name}'.\n"
            f"Available connectors: {', '.join(available_connectors) if available_connectors else 'none'}"
        )


def validate_simulator_type(simulator_type: str) -> None:
    """
    Validate that a simulator type exists.

    Parameters
    ----------
    simulator_type : str
        The simulator type (usually a class name)

    Raises
    ------
    ValueError
        If the simulator type is not found
    """
    available = discover_available_simulators()
    if simulator_type not in available:
        available_list = sorted(available.keys())
        raise ValueError(
            f"Simulator type '{simulator_type}' not found.\n"
            f"Available simulator types: {', '.join(available_list)}"
        )


def validate_background_type(background_type: str) -> None:
    """
    Validate that a background type exists.

    Parameters
    ----------
    background_type : str
        The background type (usually a class name)

    Raises
    ------
    ValueError
        If the background type is not found
    """
    available = discover_available_backgrounds()
    if background_type not in available:
        available_list = sorted(available.keys())
        raise ValueError(
            f"Background type '{background_type}' not found.\n"
            f"Available background types: {', '.join(available_list)}"
        )


def validate_llm_type(llm_type: str) -> None:
    """
    Validate that an LLM type exists.

    Parameters
    ----------
    llm_type : str
        The LLM type (usually a class name)

    Raises
    ------
    ValueError
        If the LLM type is not found
    """
    available = discover_available_llms()
    if llm_type not in available:
        available_list = sorted(available.keys())
        raise ValueError(
            f"LLM type '{llm_type}' not found.\n"
            f"Available LLM types: {', '.join(available_list)}"
        )
