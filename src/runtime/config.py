"""Mode-runtime configuration models, loaders, and serialization helpers."""

import importlib
import importlib.util
import json
import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from jsonschema import ValidationError, validate

from actions import load_action
from actions.base import AgentAction
from backgrounds import load_background
from backgrounds.base import Background
from inputs import load_input
from inputs.base import Sensor
from llm import LLM, load_llm
from runtime.converter import convert_to_multi_mode
from runtime.hook import (
    LifecycleHook,
    LifecycleHookType,
    execute_lifecycle_hooks,
    parse_lifecycle_hooks,
)
from runtime.robotics import load_unitree
from runtime.version import verify_runtime_version
from simulators import load_simulator
from simulators.base import Simulator

json5 = importlib.import_module("json5") if importlib.util.find_spec("json5") else json


def _load_schema(schema_file: str) -> dict:
    """
    Load and cache schema files.

    Parameters
    ----------
    schema_file : str
        Name of the schema file to load.

    Returns
    -------
    dict
        The loaded schema dictionary.

    Raises
    ------
    FileNotFoundError
        If the schema file does not exist.
    """
    schema_path = Path(__file__).parent / "../../config/schema" / schema_file

    if not schema_path.exists():
        raise FileNotFoundError(
            f"Schema file not found: {schema_path}. Cannot validate configuration."
        )

    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_config_schema(raw_config: dict) -> None:
    """
    Validate the configuration against the appropriate schema.

    Parameters
    ----------
    raw_config : dict
        The raw configuration dictionary to validate.
    """
    schema_file = (
        "multi_mode_schema.json"
        if "modes" in raw_config and "default_mode" in raw_config
        else "single_mode_schema.json"
    )

    try:
        schema = _load_schema(schema_file)
        validate(instance=raw_config, schema=schema)

    except FileNotFoundError as e:
        logging.error(str(e))
        raise
    except ValidationError as e:
        field_path = ".".join(str(p) for p in e.path) if e.path else "root"
        logging.error(
            "Schema validation failed at field '%s': %s",
            field_path,
            e.message,
        )
        raise


@dataclass
class RuntimeConfig:
    """
    Runtime configuration for the agent.

    Parameters
    ----------
    version : str
        Configuration version.
    hertz : float
        Execution frequency.
    name : str
        Config name.
    system_prompt_base : str
        Base system prompt.
    system_governance : str
        Governance rules for the system.
    system_prompt_examples : str
        Example prompts for the system.
    agent_inputs : List[Sensor]
        List of agent input sensors.
    cortex_llm : LLM
        The main LLM for the agent.
    simulators : List[Simulator]
        List of simulators.
    agent_actions : List[AgentAction]
        List of agent actions.
    backgrounds : List[Background]
        List of background processes.
    mode : Optional[str]
        Optional mode setting.
    api_key : Optional[str]
        Optional API key.
    robot_ip : Optional[str]
        Optional robot IP address.
    URID : Optional[str]
        Optional unique robot identifier.
    unitree_ethernet : Optional[str]
        Optional Unitree ethernet port.
    action_execution_mode : Optional[str]
        Optional action execution mode (for example, "concurrent", "sequential",
        or "dependencies"). Defaults to "concurrent".
    action_dependencies : Optional[Dict[str, List[str]]]
        Optional mapping of action dependencies.
    """

    version: str
    hertz: float
    name: str
    system_prompt_base: str
    system_governance: str
    system_prompt_examples: str

    agent_inputs: List[Sensor]
    cortex_llm: LLM
    simulators: List[Simulator]
    agent_actions: List[AgentAction]
    backgrounds: List[Background]

    mode: Optional[str] = None
    api_key: Optional[str] = None
    robot_ip: Optional[str] = None
    URID: Optional[str] = None
    unitree_ethernet: Optional[str] = None
    action_execution_mode: Optional[str] = None
    action_dependencies: Optional[Dict[str, List[str]]] = None


@dataclass(frozen=True)
class _MetaDefaults:
    """Metadata defaults injected into component config payloads."""

    api_key: Optional[str]
    unitree_ethernet: Optional[str]
    urid: Optional[str]
    robot_ip: Optional[str]
    mode: Optional[str] = None


def add_meta(
    config: Dict,
    defaults: _MetaDefaults,
) -> dict[str, Any]:
    """
    Add an API key and Robot configuration to a runtime configuration.

    Parameters
    ----------
    config : dict
        The runtime configuration to update.
    defaults : _MetaDefaults
        Default metadata values to inject when missing.

    Returns
    -------
    dict
        The updated runtime configuration.
    """
    # logging.info(f"config before {config}")
    if "api_key" not in config and defaults.api_key is not None:
        config["api_key"] = defaults.api_key
    if "unitree_ethernet" not in config and defaults.unitree_ethernet is not None:
        config["unitree_ethernet"] = defaults.unitree_ethernet
    if "URID" not in config and defaults.urid is not None:
        config["URID"] = defaults.urid
    if "robot_ip" not in config and defaults.robot_ip is not None:
        config["robot_ip"] = defaults.robot_ip
    if "mode" not in config and defaults.mode is not None:
        config["mode"] = defaults.mode
    return config


class TransitionType(Enum):
    """
    Types of mode transitions.

    - INPUT_TRIGGERED: Switch based on specific input keywords or phrases.
    - TIME_BASED: Switch after a certain time period or at specific times.
    - CONTEXT_AWARE: Switch based on contextual cues or environment
    - MANUAL: Switch only when manually triggered by the user.
    """

    INPUT_TRIGGERED = "input_triggered"
    TIME_BASED = "time_based"
    CONTEXT_AWARE = "context_aware"
    MANUAL = "manual"


@dataclass
class TransitionRule:
    """
    Defines a rule for transitioning between modes.

    Parameters
    ----------
    from_mode : str
        Name of the mode to transition from.
    to_mode : str
        Name of the mode to transition to.
    transition_type : TransitionType
        The type of transition (e.g., input-triggered, time-based).
    trigger_keywords : List[str], optional
        Keywords or phrases that can trigger the transition (for input-triggered).
    priority : int, optional
        Priority of the rule when multiple rules could apply.
        Higher numbers = higher priority. Defaults to 1.
    cooldown_seconds : float, optional
        Minimum time in seconds before this rule can trigger again. Defaults to 0.0.
    timeout_seconds : Optional[float], optional
        For time-based transitions, the time in seconds after which to switch
        modes. Defaults to None.
    context_conditions : Dict, optional
        Conditions based on context that must be met for the transition. Defaults to empty dict.
    """

    from_mode: str
    to_mode: str
    transition_type: TransitionType
    trigger_keywords: List[str] = field(default_factory=list)
    priority: int = 1
    cooldown_seconds: float = 0.0
    timeout_seconds: Optional[float] = None
    context_conditions: Dict = field(default_factory=dict)


@dataclass
class ModeConfig:
    """
    Configuration for a specific mode.

    Parameters
    ----------
    version : str
        Version of the mode configuration.
    name : str
        Unique name of the mode.
    display_name : str
        Human-readable name of the mode.
    description : str
        Description of the mode's purpose and behavior.
    system_prompt_base : str
        Base system prompt to use for the mode.
    hertz : float, optional
        Frequency in Hz at which the mode operates. Defaults to 1.0.
    timeout_seconds : Optional[float], optional
        Optional timeout in seconds for mode operations. Defaults to None.
    remember_locations : bool, optional
        Whether the mode should remember locations. Defaults to False.
    save_interactions : bool, optional
        Whether to save interactions in this mode. Defaults to False.
    lifecycle_hooks : List[LifecycleHook], optional
        List of lifecycle hooks associated with this mode. Defaults to empty list.
    agent_inputs : List[Sensor], optional
        List of input sensors for the mode. Defaults to empty list.
    cortex_llm : Optional[LLM], optional
        The LLM used for the mode. Defaults to None.
    simulators : List[Simulator], optional
        List of simulators used in the mode. Defaults to empty list.
    agent_actions : List[AgentAction], optional
        List of actions available to the agent in this mode. Defaults to empty list.
    backgrounds : List[Background], optional
        List of background processes for the mode. Defaults to empty list.
    action_execution_mode : Optional[str], optional
        Execution mode for actions (for example, "concurrent", "sequential",
        or "dependencies"). Defaults to concurrent.
    action_dependencies : Optional[Dict[str, List[str]]], optional
        Dependencies between actions for execution order. Defaults to None.
    _raw_inputs : List[Dict], optional
        Raw input configurations before loading. Defaults to empty list.
    _raw_llm : Optional[Dict], optional
        Raw LLM configuration before loading. Defaults to None.
    _raw_simulators : List[Dict], optional
        Raw simulator configurations before loading. Defaults to empty list.
    _raw_actions : List[Dict], optional
        Raw action configurations before loading. Defaults to empty list.
    _raw_backgrounds : List[Dict], optional
        Raw background configurations before loading. Defaults to empty list.
    """

    version: str

    name: str
    display_name: str
    description: str
    system_prompt_base: str
    hertz: float = 1.0

    timeout_seconds: Optional[float] = None
    remember_locations: bool = False
    save_interactions: bool = False

    lifecycle_hooks: List[LifecycleHook] = field(default_factory=list)
    _raw_lifecycle_hooks: List[Dict] = field(default_factory=list)

    agent_inputs: List[Sensor] = field(default_factory=list)
    cortex_llm: Optional[LLM] = None
    simulators: List[Simulator] = field(default_factory=list)
    agent_actions: List[AgentAction] = field(default_factory=list)
    backgrounds: List[Background] = field(default_factory=list)

    action_execution_mode: Optional[str] = None
    action_dependencies: Optional[Dict[str, List[str]]] = None

    _raw_inputs: List[Dict] = field(default_factory=list)
    _raw_llm: Optional[Dict] = None
    _raw_simulators: List[Dict] = field(default_factory=list)
    _raw_actions: List[Dict] = field(default_factory=list)
    _raw_backgrounds: List[Dict] = field(default_factory=list)

    def to_runtime_config(self, global_config: "ModeSystemConfig") -> RuntimeConfig:
        """
        Convert this mode config to a RuntimeConfig for the cortex.

        Parameters
        ----------
        global_config : ModeSystemConfig
            The global system configuration containing shared settings

        Returns
        -------
        RuntimeConfig
            The runtime configuration for this mode
        """
        if self.cortex_llm is None:
            raise ValueError(f"No LLM configured for mode {self.name}")

        return RuntimeConfig(
            version=self.version,
            hertz=self.hertz,
            mode=self.name,
            name=f"{global_config.name}_{self.name}",
            system_prompt_base=self.system_prompt_base,
            system_governance=global_config.system_governance,
            system_prompt_examples=global_config.system_prompt_examples,
            agent_inputs=self.agent_inputs,
            cortex_llm=self.cortex_llm,
            simulators=self.simulators,
            agent_actions=self.agent_actions,
            backgrounds=self.backgrounds,
            robot_ip=global_config.robot_ip,
            api_key=global_config.api_key,
            URID=global_config.URID,
            unitree_ethernet=global_config.unitree_ethernet,
            action_execution_mode=self.action_execution_mode,
            action_dependencies=self.action_dependencies,
        )

    def load_components(self, system_config: "ModeSystemConfig"):
        """
        Load the actual component instances for this mode.

        This method should be called when the mode is activated to ensure
        fresh instances and avoid singleton conflicts between modes.

        Parameters
        ----------
        system_config : ModeSystemConfig
            The global system configuration containing shared settings
        """
        logging.info("Loading components for mode: %s", self.name)
        _load_mode_components(self, system_config)
        logging.info("Components loaded successfully for mode: %s", self.name)

    async def execute_lifecycle_hooks(
        self, hook_type: LifecycleHookType, context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Execute all lifecycle hooks of the specified type for this mode.

        Parameters
        ----------
        hook_type : LifecycleHookType
            The type of lifecycle hooks to execute
        context : Optional[Dict[str, Any]]
            Context information to pass to the hooks

        Returns
        -------
        bool
            True if all hooks executed successfully, False if any failed
        """
        if context is None:
            context = {}

        context.update(
            {
                "mode_name": self.name,
                "mode_display_name": self.display_name,
                "mode_description": self.description,
            }
        )

        return await execute_lifecycle_hooks(self.lifecycle_hooks, hook_type, context)


@dataclass
class ModeSystemConfig:
    """
    Complete configuration for a mode-aware system.

    Parameters
    ----------
    version : str
        Version of the mode system configuration.
    name : str
        Name of the mode system.
    default_mode : str
        The default mode to start in.
    config_name : str
        Name of the configuration file.
    allow_manual_switching : bool
        Whether manual mode switching is allowed. Defaults to True.
    mode_memory_enabled : bool
        Whether mode memory is enabled. Defaults to True.
    api_key : Optional[str]
        Global API key for services.
    robot_ip : Optional[str]
        Global robot IP address.
    URID : Optional[str]
        Global URID robot identifier.
    unitree_ethernet : Optional[str]
        Global Unitree ethernet port.
    system_governance : str
        Global system governance prompt.
    system_prompt_examples : str
        Global system prompt examples.
    global_cortex_llm : Optional[Dict]
        Global default LLM configuration if mode doesn't override.
    global_lifecycle_hooks : List[LifecycleHook], optional
        List of global lifecycle hooks executed for all modes. Defaults to empty list.
    modes : Dict[str, ModeConfig], optional
        Mapping of mode names to their configurations. Defaults to empty dict.
    transition_rules : List[TransitionRule], optional
        List of rules for transitioning between modes. Defaults to empty list.
    """

    # Global settings
    version: str
    name: str
    default_mode: str
    config_name: str = ""
    allow_manual_switching: bool = True
    mode_memory_enabled: bool = True

    # Global parameters
    api_key: Optional[str] = None
    robot_ip: Optional[str] = None
    URID: Optional[str] = None
    unitree_ethernet: Optional[str] = None
    system_governance: str = ""
    system_prompt_examples: str = ""

    # Default LLM settings if mode doesn't override
    global_cortex_llm: Optional[Dict] = None

    # Global lifecycle hooks (executed for all modes)
    global_lifecycle_hooks: List[LifecycleHook] = field(default_factory=list)
    _raw_global_lifecycle_hooks: List[Dict] = field(default_factory=list)

    # Modes and transition rules
    modes: Dict[str, ModeConfig] = field(default_factory=dict)
    transition_rules: List[TransitionRule] = field(default_factory=list)

    async def execute_global_lifecycle_hooks(
        self, hook_type: LifecycleHookType, context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Execute all global lifecycle hooks of the specified type.

        Parameters
        ----------
        hook_type : LifecycleHookType
            The type of lifecycle hooks to execute
        context : Optional[Dict[str, Any]]
            Context information to pass to the hooks

        Returns
        -------
        bool
            True if all hooks executed successfully, False if any failed
        """
        if context is None:
            context = {}

        context.update({"system_name": self.name, "is_global_hook": True})

        return await execute_lifecycle_hooks(
            self.global_lifecycle_hooks, hook_type, context
        )


def load_mode_config(
    config_name: str, mode_source_path: Optional[str] = None
) -> ModeSystemConfig:
    """
    Load a mode-aware configuration from a JSON5 file.

    Parameters
    ----------
    config_name : str
        Name of the configuration file (without .json5 extension)
    mode_source_path : Optional[str]
        Optional path to the configuration file. If None, defaults to the config directory.
        The path is relative to the ../../../config directory.

    Returns
    -------
    ModeSystemConfig
        Parsed mode system configuration
    """
    config_path = (
        os.path.join(os.path.dirname(__file__), "../../config", config_name + ".json5")
        if mode_source_path is None
        else mode_source_path
    )

    with open(config_path, "r", encoding="utf-8") as f:
        try:
            raw_config = json5.load(f)
        except Exception as e:
            raise ValueError(
                f"Failed to parse configuration file '{config_path}': {e}"
            ) from e

    config_version = raw_config.get("version")
    verify_runtime_version(config_version, config_name)
    validate_config_schema(raw_config)
    raw_config = convert_to_multi_mode(raw_config)

    g_robot_ip = raw_config.get("robot_ip", None)
    if g_robot_ip is None or g_robot_ip == "" or g_robot_ip == "192.168.0.241":
        logging.warning("No robot ip found in mode config. Checking .env file.")
        backup_key = os.environ.get("ROBOT_IP")
        if backup_key:
            g_robot_ip = backup_key
            logging.info("Found ROBOT_IP in .env file.")

    g_api_key = raw_config.get("api_key", None)
    if g_api_key is None or g_api_key == "" or g_api_key == "openmind_free":
        logging.warning("No API key found in mode config. Checking .env file.")
        backup_key = os.environ.get("OM_API_KEY")
        if backup_key:
            g_api_key = backup_key
            logging.info("Found OM_API_KEY in .env file.")

    g_urid = raw_config.get("URID", "default")
    if g_urid == "default":
        backup_urid = os.environ.get("URID")
        if backup_urid:
            g_urid = backup_urid

    g_ut_eth = raw_config.get("unitree_ethernet", None)
    if g_ut_eth is None or g_ut_eth == "":
        logging.info("No robot hardware ethernet port provided.")
    else:
        try:
            load_unitree(g_ut_eth)
        except RuntimeError as exc:
            raise RuntimeError(
                f"Unitree initialization failed while loading config "
                f"'{config_name}' with unitree_ethernet '{g_ut_eth}'"
            ) from exc

    mode_system_config = ModeSystemConfig(
        version=config_version,
        name=raw_config.get("name", "mode_system"),
        default_mode=raw_config["default_mode"],
        config_name=config_name,
        allow_manual_switching=raw_config.get("allow_manual_switching", True),
        mode_memory_enabled=raw_config.get("mode_memory_enabled", True),
        api_key=g_api_key,
        robot_ip=g_robot_ip,
        URID=g_urid,
        unitree_ethernet=g_ut_eth,
        system_governance=raw_config.get("system_governance", ""),
        system_prompt_examples=raw_config.get("system_prompt_examples", ""),
        global_cortex_llm=raw_config.get("cortex_llm"),
        global_lifecycle_hooks=parse_lifecycle_hooks(
            raw_config.get("global_lifecycle_hooks", []), api_key=g_api_key
        ),
        _raw_global_lifecycle_hooks=raw_config.get("global_lifecycle_hooks", []),
    )

    for mode_name, mode_data in raw_config.get("modes", {}).items():
        mode_config = ModeConfig(
            version=mode_data.get("version", "1.0.1"),
            name=mode_name,
            display_name=mode_data.get("display_name", mode_name),
            description=mode_data.get("description", ""),
            system_prompt_base=mode_data["system_prompt_base"],
            hertz=mode_data.get("hertz", 1.0),
            lifecycle_hooks=parse_lifecycle_hooks(
                mode_data.get("lifecycle_hooks", []), api_key=g_api_key
            ),
            timeout_seconds=mode_data.get("timeout_seconds"),
            remember_locations=mode_data.get("remember_locations", False),
            save_interactions=mode_data.get("save_interactions", False),
            action_execution_mode=mode_data.get("action_execution_mode"),
            action_dependencies=mode_data.get("action_dependencies"),
            _raw_inputs=mode_data.get("agent_inputs", []),
            _raw_llm=mode_data.get("cortex_llm"),
            _raw_simulators=mode_data.get("simulators", []),
            _raw_actions=mode_data.get("agent_actions", []),
            _raw_backgrounds=mode_data.get("backgrounds", []),
            _raw_lifecycle_hooks=mode_data.get("lifecycle_hooks", []),
        )

        mode_system_config.modes[mode_name] = mode_config

    for rule_data in raw_config.get("transition_rules", []):
        rule = TransitionRule(
            from_mode=rule_data["from_mode"],
            to_mode=rule_data["to_mode"],
            transition_type=TransitionType(rule_data["transition_type"]),
            trigger_keywords=rule_data.get("trigger_keywords", []),
            priority=rule_data.get("priority", 1),
            cooldown_seconds=rule_data.get("cooldown_seconds", 0.0),
            timeout_seconds=rule_data.get("timeout_seconds"),
            context_conditions=rule_data.get("context_conditions", {}),
        )
        mode_system_config.transition_rules.append(rule)

    return mode_system_config


def _get_mode_raw_list(mode_config: ModeConfig, attr_name: str) -> List[Dict]:
    """
    Read a raw mode list field defensively through ``getattr``.

    Returns an empty list if the attribute is missing or not a list.
    """
    raw_value = getattr(mode_config, attr_name, [])
    return raw_value if isinstance(raw_value, list) else []


def _get_mode_raw_dict(mode_config: ModeConfig, attr_name: str) -> Optional[Dict]:
    """
    Read a raw mode mapping field defensively through ``getattr``.

    Returns None if the attribute is missing or not a dict.
    """
    raw_value = getattr(mode_config, attr_name, None)
    return raw_value if isinstance(raw_value, dict) else None


def _get_system_raw_global_lifecycle_hooks(config: ModeSystemConfig) -> List[Dict]:
    """Read global lifecycle-hook payloads without direct protected access."""
    raw_hooks = getattr(config, "_raw_global_lifecycle_hooks", [])
    return raw_hooks if isinstance(raw_hooks, list) else []


def _load_mode_components(mode_config: ModeConfig, system_config: ModeSystemConfig):
    """
    Load the actual component instances for a mode.

    Parameters
    ----------
    mode_config : ModeConfig
        The mode configuration to load components for.
    system_config : ModeSystemConfig
        The global system configuration containing shared settings
    """
    g_api_key = system_config.api_key
    g_ut_eth = system_config.unitree_ethernet
    g_urid = system_config.URID
    g_robot_ip = system_config.robot_ip
    g_mode = mode_config.name
    meta_defaults = _MetaDefaults(
        api_key=g_api_key,
        unitree_ethernet=g_ut_eth,
        urid=g_urid,
        robot_ip=g_robot_ip,
        mode=g_mode,
    )
    raw_inputs = _get_mode_raw_list(mode_config, "_raw_inputs")
    raw_simulators = _get_mode_raw_list(mode_config, "_raw_simulators")
    raw_actions = _get_mode_raw_list(mode_config, "_raw_actions")
    raw_backgrounds = _get_mode_raw_list(mode_config, "_raw_backgrounds")
    raw_llm = _get_mode_raw_dict(mode_config, "_raw_llm")

    # Load inputs
    mode_config.agent_inputs = [
        load_input(
            {
                **inp,
                "config": add_meta(
                    inp.get("config", {}),
                    meta_defaults,
                ),
            }
        )
        for inp in raw_inputs
    ]

    # Load simulators
    mode_config.simulators = [
        load_simulator(
            {
                **sim,
                "config": add_meta(
                    sim.get("config", {}),
                    meta_defaults,
                ),
            }
        )
        for sim in raw_simulators
    ]

    # Load actions
    mode_config.agent_actions = [
        load_action(
            {
                **action,
                "config": add_meta(
                    action.get("config", {}),
                    meta_defaults,
                ),
            }
        )
        for action in raw_actions
    ]

    # Load backgrounds
    mode_config.backgrounds = [
        load_background(
            {
                **bg,
                "config": add_meta(
                    bg.get("config", {}),
                    meta_defaults,
                ),
            }
        )
        for bg in raw_backgrounds
    ]

    # Load LLM
    llm_config = raw_llm or system_config.global_cortex_llm
    if llm_config:
        mode_config.cortex_llm = load_llm(
            {
                **llm_config,
                "config": add_meta(
                    llm_config.get("config", {}),
                    meta_defaults,
                ),
            },
            available_actions=mode_config.agent_actions,
        )
    else:
        raise ValueError(f"No LLM configuration found for mode {mode_config.name}")


def mode_config_to_dict(config: ModeSystemConfig) -> Dict[str, Any]:
    """
    Convert a ModeSystemConfig back to a dictionary for serialization.

    Parameters
    ----------
    config : ModeSystemConfig
        The mode system configuration to convert.

    Returns
    -------
    Dict[str, Any]
        The dictionary representation of the mode system configuration.
    """
    try:
        modes_dict = {}
        for mode_name, mode_config in config.modes.items():
            modes_dict[mode_name] = {
                "name": mode_config.name,
                "display_name": mode_config.display_name,
                "description": mode_config.description,
                "system_prompt_base": mode_config.system_prompt_base,
                "hertz": mode_config.hertz,
                "timeout_seconds": mode_config.timeout_seconds,
                "remember_locations": mode_config.remember_locations,
                "save_interactions": mode_config.save_interactions,
                "agent_inputs": _get_mode_raw_list(mode_config, "_raw_inputs"),
                "cortex_llm": _get_mode_raw_dict(mode_config, "_raw_llm"),
                "simulators": _get_mode_raw_list(mode_config, "_raw_simulators"),
                "agent_actions": _get_mode_raw_list(mode_config, "_raw_actions"),
                "backgrounds": _get_mode_raw_list(mode_config, "_raw_backgrounds"),
                "lifecycle_hooks": _get_mode_raw_list(
                    mode_config, "_raw_lifecycle_hooks"
                ),
            }

        transition_rules = []
        for rule in config.transition_rules:
            transition_rules.append(
                {
                    "from_mode": rule.from_mode,
                    "to_mode": rule.to_mode,
                    "transition_type": rule.transition_type.value,
                    "trigger_keywords": rule.trigger_keywords,
                    "priority": rule.priority,
                    "cooldown_seconds": rule.cooldown_seconds,
                    "timeout_seconds": rule.timeout_seconds,
                    "context_conditions": rule.context_conditions,
                }
            )

        return {
            "version": config.version,
            "name": config.name,
            "default_mode": config.default_mode,
            "allow_manual_switching": config.allow_manual_switching,
            "mode_memory_enabled": config.mode_memory_enabled,
            "api_key": config.api_key,
            "robot_ip": config.robot_ip,
            "URID": config.URID,
            "unitree_ethernet": config.unitree_ethernet,
            "system_governance": config.system_governance,
            "system_prompt_examples": config.system_prompt_examples,
            "cortex_llm": config.global_cortex_llm,
            "global_lifecycle_hooks": _get_system_raw_global_lifecycle_hooks(config),
            "modes": modes_dict,
            "transition_rules": transition_rules,
        }

    except (AttributeError, KeyError, TypeError, ValueError) as e:
        logging.error("Error converting config to dict: %s", e)
        return {}
