"""Command-line tools for listing, inspecting, and validating OM1 configs."""

import ast
import importlib
import importlib.util
import json
import logging
import multiprocessing as mp
import os
import traceback
from dataclasses import dataclass, field
from typing import Callable

import dotenv
import typer
from jsonschema import ValidationError, validate

from runtime.config import load_mode_config
from runtime.converter import convert_to_multi_mode

json5 = (
    importlib.import_module("json5")
    if importlib.util.find_spec("json5")
    else json
)

app = typer.Typer()


def _get_mode_item_count(mode: object, loaded_attr: str, raw_attr_name: str) -> int:
    """Get mode component count while avoiding direct protected-attribute access."""
    loaded_items = getattr(mode, loaded_attr, None)
    if loaded_items:
        return len(loaded_items)

    raw_items = getattr(mode, raw_attr_name, None)
    return len(raw_items) if isinstance(raw_items, list) else 0


@app.command()
def modes(config_name: str) -> None:
    """
    Show detailed information about available modes, transition rules,
    and settings within a specified mode-aware configuration file.

    This command is crucial for debugging and understanding the current
    state of the multi-mode system configuration.

    Parameters
    ----------
    config_name : str
        The name of the configuration file (e.g., 'example' for 'example.json5')
        located in the '../config' directory.

    Raises
    ------
    typer.Exit(1)
        If the configuration file is not found or fails to load.
    """
    try:
        mode_config = load_mode_config(config_name)

        print("-" * 32)
        print(f"Mode System: {mode_config.name}")
        print(f"Default Mode: {mode_config.default_mode}")
        print(
            f"Manual Switching: {'Enabled' if mode_config.allow_manual_switching else 'Disabled'}"
        )
        print(
            f"Mode Memory: {'Enabled' if mode_config.mode_memory_enabled else 'Disabled'}"
        )

        if mode_config.global_lifecycle_hooks:
            print(f"Global Lifecycle Hooks: {len(mode_config.global_lifecycle_hooks)}")
        print()

        print("Available Modes:")
        print("-" * 50)
        for name, mode in mode_config.modes.items():
            is_default = " (DEFAULT)" if name == mode_config.default_mode else ""
            print(f"• {mode.display_name}{is_default}")
            print(f"  Name: {name}")
            print(f"  Description: {mode.description}")
            print(f"  Frequency: {mode.hertz} Hz")
            if mode.timeout_seconds:
                print(f"  Timeout: {mode.timeout_seconds} seconds")
            print(
                f"  Inputs: {_get_mode_item_count(mode, 'agent_inputs', '_raw_inputs')}"
            )
            print(
                f"  Actions: {_get_mode_item_count(mode, 'agent_actions', '_raw_actions')}"
            )
            if mode.lifecycle_hooks:
                print(f"  Lifecycle Hooks: {len(mode.lifecycle_hooks)}")
            print()

        print("Transition Rules:")
        print("-" * 50)
        for rule in mode_config.transition_rules:
            from_display = (
                mode_config.modes[rule.from_mode].display_name
                if rule.from_mode != "*"
                else "Any Mode"
            )
            to_display = mode_config.modes[rule.to_mode].display_name
            print(f"• {from_display} → {to_display}")
            print(f"  Type: {rule.transition_type.value}")
            if rule.trigger_keywords:
                print(f"  Keywords: {', '.join(rule.trigger_keywords)}")
            print(f"  Priority: {rule.priority}")
            if rule.cooldown_seconds > 0:
                print(f"  Cooldown: {rule.cooldown_seconds}s")
            print()

    except FileNotFoundError as exc:
        logging.error("Configuration file not found: %s.json5", config_name)
        raise typer.Exit(1) from exc
    except Exception as e:
        logging.error("Error loading mode configuration: %s", e)
        raise typer.Exit(1)


@app.command()
def list_configs() -> None:
    """
    List all available configuration files found in the '../config' directory.

    """
    config_dir = os.path.join(os.path.dirname(__file__), "../config")

    if not os.path.exists(config_dir):
        print("Configuration directory not found")
        return

    configs = []

    for filename in os.listdir(config_dir):
        if filename.endswith(".json5"):
            config_name = filename[:-6]
            config_path = os.path.join(config_dir, filename)

            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    raw_config = json5.load(f)

                display_name = raw_config.get("name", config_name)
                configs.append((config_name, display_name))
            except (OSError, ValueError, TypeError, UnicodeError):
                configs.append((config_name, "Invalid config"))

    print("-" * 32)
    print("Configurations:")
    print("-" * 32)
    for config_name, display_name in sorted(configs):
        print(f"• {config_name} - {display_name}")


@app.command()
def validate_config(
    config_name: str = typer.Argument(
        ...,
        help="Configuration file name or path (e.g., 'test' or 'config/test.json5')",
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show detailed validation information"
    ),
    check_components: bool = typer.Option(
        True,
        "--check-components",
        help=(
            "Verify that all components (inputs, LLMs, actions) exist in "
            "codebase (slower but thorough)"
        ),
    ),
    skip_inputs: bool = typer.Option(
        False,
        "--skip-inputs",
        help="Skip input validation (useful for debugging)",
    ),
    allow_missing: bool = typer.Option(
        False,
        "--allow-missing",
        help="Allow missing components (only warn, don't fail)",
    ),
) -> None:
    """
    Validate an OM1 configuration file.

    Checks for:
    - Valid JSON5 syntax
    - Schema compliance (required fields, correct types)
    - API key configuration (warning only)
    - Component existence (with --check-components flag)

    Parameters
    ----------
    config_name : str
        Configuration file name or path (e.g., 'test' or 'config/test.json5').
    verbose : bool
        Show detailed validation information.
    check_components : bool
        Verify that all components (inputs, LLMs, actions) exist in codebase.
    skip_inputs : bool
        Skip input validation (useful for debugging).
    allow_missing : bool
        Allow missing components (only warn, don't fail).

    Examples
    --------
        uv run src/cli.py validate-config test
        uv run src/cli.py validate-config config/my_robot.json5
        uv run src/cli.py validate-config test --verbose
        uv run src/cli.py validate-config test --check-components
        uv run src/cli.py validate-config test --check-components --skip-inputs
        uv run src/cli.py validate-config test --check-components --allow-missing
    """
    try:
        config_path = _resolve_config_path(config_name)
        _print_validation_header(config_path, verbose)
        raw_config = _load_raw_config(config_path)
        raw_config = _validate_schema_and_convert(raw_config, verbose)
        _validate_requested_components(
            raw_config=raw_config,
            verbose=verbose,
            check_components=check_components,
            skip_inputs=skip_inputs,
            allow_missing=allow_missing,
        )
        _check_api_key(raw_config, verbose)
        _print_validation_success(raw_config, verbose)
    except FileNotFoundError as exc:
        print("Error: Configuration file not found")
        print(f"   {exc}")
        raise typer.Exit(1) from exc
    except ValidationError as exc:
        _print_schema_validation_error(exc, verbose)
        raise typer.Exit(1) from exc
    except ValueError as exc:
        _print_value_validation_error(exc, verbose)
        raise typer.Exit(1) from exc
    except (OSError, TypeError, RuntimeError) as exc:
        _print_unexpected_validation_error(exc, verbose)
        raise typer.Exit(1) from exc


def _print_validation_header(config_path: str, verbose: bool) -> None:
    """Print validation header output for verbose mode."""
    if not verbose:
        return
    print(f"Validating: {config_path}")
    print("-" * 50)


def _load_raw_config(config_path: str) -> dict:
    """
    Load and parse a configuration file as JSON5.

    Raises
    ------
    ValueError
        If JSON5 syntax is invalid.
    """
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json5.load(f)
    except ValueError as exc:
        raise ValueError(f"Invalid JSON5 syntax: {exc}") from exc


def _validate_schema_and_convert(raw_config: dict, verbose: bool) -> dict:
    """Validate config schema and convert to multi-mode representation."""
    if verbose:
        print("JSON5 syntax valid")

    is_multi_mode = "modes" in raw_config and "default_mode" in raw_config
    schema_file = "multi_mode_schema.json" if is_multi_mode else "single_mode_schema.json"
    schema_path = os.path.join(os.path.dirname(__file__), "../config/schema", schema_file)

    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)

    validate(instance=raw_config, schema=schema)
    converted_config = convert_to_multi_mode(raw_config)

    if verbose:
        print("Schema validation passed")

    return converted_config


def _validate_requested_components(
    raw_config: dict,
    verbose: bool,
    check_components: bool,
    skip_inputs: bool,
    allow_missing: bool,
) -> None:
    """Run component checks if requested by CLI flags."""
    if not check_components:
        return

    if not verbose:
        print("Validating components (this may take a moment)...", end="", flush=True)
    _validate_components(raw_config, verbose, skip_inputs, allow_missing)
    if not verbose:
        print("\rAll components validated successfully!           ")


def _print_validation_success(raw_config: dict, verbose: bool) -> None:
    """Print success output after validation completes."""
    print()
    print("=" * 50)
    print("Configuration is valid!")
    print("=" * 50)

    if verbose:
        _print_config_summary(raw_config)


def _print_schema_validation_error(error: ValidationError, verbose: bool) -> None:
    """Print schema-validation error details."""
    print("Error: Schema validation failed")
    field_path = ".".join(str(p) for p in error.path) if error.path else "root"
    print(f"   Field: {field_path}")
    print(f"   Issue: {error.message}")
    if verbose and error.schema:
        print("\n   Schema requirement:")
        print(f"   {error.schema}")


def _print_value_validation_error(error: ValueError, verbose: bool) -> None:
    """Print value-based validation errors with targeted messaging."""
    error_message = str(error)

    if error_message.startswith("Component validation"):
        return

    if error_message.startswith("Invalid JSON5 syntax:"):
        print("Error: Invalid JSON5 syntax")
        print(f"   {error_message.removeprefix('Invalid JSON5 syntax: ').strip()}")
        return

    _print_unexpected_validation_error(error, verbose)


def _print_unexpected_validation_error(error: Exception, verbose: bool) -> None:
    """Print fallback error output for unexpected validation failures."""
    print("Error: Unexpected validation error")
    print(f"   {error}")
    if verbose:
        traceback.print_exc()


def _resolve_config_path(config_name: str) -> str:
    """
    Resolve configuration path from name or path.

    Parameters
    ----------
    config_name : str
        Configuration name or path

    Returns
    -------
    str
        Absolute path to configuration file

    Raises
    ------
    FileNotFoundError
        If configuration file cannot be found
    """
    if os.path.exists(config_name):
        return os.path.abspath(config_name)

    if os.path.exists(config_name + ".json5"):
        return os.path.abspath(config_name + ".json5")

    config_dir = os.path.join(os.path.dirname(__file__), "../config")
    config_path = os.path.join(config_dir, config_name)

    if os.path.exists(config_path):
        return os.path.abspath(config_path)

    if os.path.exists(config_path + ".json5"):
        return os.path.abspath(config_path + ".json5")

    raise FileNotFoundError(
        f"Configuration '{config_name}' not found. "
        f"Tried: {config_name}, {config_name}.json5, {config_path}, {config_path}.json5"
    )


def _validate_components(
    raw_config: dict,
    verbose: bool,
    skip_inputs: bool = False,
    allow_missing: bool = False,
):
    """
    Validate that all component types exist in codebase.

    Parameters
    ----------
    raw_config : dict
        Configuration dictionary
    verbose : bool
        Whether to print verbose output
    skip_inputs : bool
        Whether to skip input validation
    allow_missing : bool
        Whether to allow missing components (warnings only)

    Raises
    ------
    ValueError
        If component validation fails and allow_missing is False
    """
    sink = _IssueSink(allow_missing=allow_missing)

    if verbose:
        print("Checking component existence...")

    try:
        _validate_global_llm(raw_config, verbose, sink)
        _validate_modes(
            raw_config,
            verbose,
            skip_inputs,
            sink,
        )
    except (AttributeError, KeyError, TypeError, ValueError, RuntimeError) as exc:
        error_msg = f"Component validation error: {exc}"
        sink.add(error_msg)
        if verbose:
            traceback.print_exc()

    if sink.warnings:
        print("Component validation warnings:")
        for warning in sink.warnings:
            print(f"   - {warning}")

    if sink.errors:
        print("Component validation failed:")
        for error in sink.errors:
            print(f"   - {error}")
        raise ValueError("Component validation failed")

    if verbose:
        print("All components exist")


@dataclass
class _IssueSink:
    """Collect validation issues in either warning or error buckets."""

    allow_missing: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def add(self, message: str) -> None:
        """Append a message to warnings or errors based on allow-missing policy."""
        if self.allow_missing:
            self.warnings.append(message)
            return
        self.errors.append(message)


@dataclass
class _ModeValidationContext:
    """Context shared across mode component validation helpers."""

    mode_name: str
    verbose: bool
    sink: _IssueSink


@dataclass(frozen=True)
class _ComponentSpec:
    """Specification for validating one mode component collection."""

    config_key: str
    group_label: str
    value_key: str
    display_label: str
    missing_label: str
    checker: Callable[..., bool]
    supports_scan_errors: bool


def _validate_global_llm(
    raw_config: dict,
    verbose: bool,
    sink: _IssueSink,
) -> None:
    """Validate global LLM declaration."""
    if "cortex_llm" not in raw_config:
        return

    llm_type = raw_config["cortex_llm"].get("type")
    if not llm_type:
        return

    if verbose:
        print(f"  Checking global LLM: {llm_type}")

    llm_scan_errors: list[str] = []
    if _check_llm_exists(llm_type, scan_errors=llm_scan_errors):
        return

    message = f"Global LLM type '{llm_type}' not found"
    message += _format_scan_error_context(llm_scan_errors)
    sink.add(message)


def _validate_modes(
    raw_config: dict,
    verbose: bool,
    skip_inputs: bool,
    sink: _IssueSink,
) -> None:
    """Validate mode-specific components."""
    for mode_name, mode_data in raw_config.get("modes", {}).items():
        if verbose:
            print(f"  Validating mode: {mode_name}")
        mode_errors, mode_warnings = _validate_mode_components(
            mode_name, mode_data, verbose, skip_inputs, sink.allow_missing
        )
        sink.errors.extend(mode_errors)
        sink.warnings.extend(mode_warnings)


def _validate_component_item(
    context: _ModeValidationContext,
    component_name: str,
    spec: _ComponentSpec,
    line_prefix: str = "      ",
) -> None:
    """Validate a single component entry and append diagnostics on failure."""
    if context.verbose:
        print(f"{line_prefix}{spec.display_label}: {component_name}", end=" ")

    scan_errors: list[str] = []
    if spec.supports_scan_errors:
        exists = spec.checker(component_name, scan_errors=scan_errors)
    else:
        exists = spec.checker(component_name)

    if exists:
        if context.verbose:
            print("OK")
        return

    message = (
        f"[{context.mode_name}] {spec.missing_label} '{component_name}' not found"
    )
    message += _format_scan_error_context(scan_errors)
    context.sink.add(message)

    if context.verbose:
        print("(warning)" if context.sink.allow_missing else "(not found)")


def _validate_component_group(
    context: _ModeValidationContext,
    mode_data: dict,
    spec: _ComponentSpec,
) -> None:
    """Validate a list of components under a mode config key."""
    items = mode_data.get(spec.config_key, [])
    if context.verbose and items:
        print(f"    Checking {len(items)} {spec.group_label}...")

    for item in items:
        component_name = item.get(spec.value_key)
        if component_name:
            _validate_component_item(
                context=context,
                component_name=component_name,
                spec=spec,
            )


def _validate_mode_components(
    mode_name: str,
    mode_data: dict,
    verbose: bool,
    skip_inputs: bool = False,
    allow_missing: bool = False,
) -> tuple:
    """
    Validate components for a single mode.

    Parameters
    ----------
    mode_name : str
        Name of the mode being validated
    mode_data : dict
        Mode configuration data
    verbose : bool
        Whether to print verbose output
    skip_inputs : bool
        Whether to skip input validation
    allow_missing : bool
        Whether to allow missing components

    Returns
    -------
    tuple
        (errors, warnings) lists
    """
    sink = _IssueSink(allow_missing=allow_missing)
    context = _ModeValidationContext(mode_name=mode_name, verbose=verbose, sink=sink)

    try:
        if skip_inputs:
            if verbose:
                print("    Skipping input validation")
        else:
            _validate_component_group(
                context=context,
                mode_data=mode_data,
                spec=_ComponentSpec(
                    config_key="agent_inputs",
                    group_label="inputs",
                    value_key="type",
                    display_label="Input",
                    missing_label="Input type",
                    checker=_check_input_exists,
                    supports_scan_errors=True,
                ),
            )

        if "cortex_llm" in mode_data:
            llm_type = mode_data["cortex_llm"].get("type")
            if llm_type:
                _validate_component_item(
                    context=context,
                    component_name=llm_type,
                    spec=_ComponentSpec(
                        config_key="cortex_llm",
                        group_label="llm",
                        value_key="type",
                        display_label="LLM",
                        missing_label="LLM type",
                        checker=_check_llm_exists,
                        supports_scan_errors=True,
                    ),
                    line_prefix="    ",
                )

        component_specs = [
            _ComponentSpec(
                config_key="simulators",
                group_label="simulators",
                value_key="type",
                display_label="Simulator",
                missing_label="Simulator type",
                checker=_check_simulator_exists,
                supports_scan_errors=True,
            ),
            _ComponentSpec(
                config_key="agent_actions",
                group_label="actions",
                value_key="name",
                display_label="Action",
                missing_label="Action",
                checker=_check_action_exists,
                supports_scan_errors=False,
            ),
            _ComponentSpec(
                config_key="backgrounds",
                group_label="backgrounds",
                value_key="type",
                display_label="Background",
                missing_label="Background type",
                checker=_check_background_exists,
                supports_scan_errors=True,
            ),
        ]
        for spec in component_specs:
            _validate_component_group(context=context, mode_data=mode_data, spec=spec)
    except (AttributeError, KeyError, TypeError, ValueError, RuntimeError) as exc:
        message = f"[{mode_name}] Error during validation: {exc}"
        sink.add(message)
        if verbose:
            print(f"    Error: {exc}")

    return sink.errors, sink.warnings


def _format_scan_error_context(scan_errors: list[str]) -> str:
    """
    Format scan errors into a concise diagnostic suffix.

    Parameters
    ----------
    scan_errors : list[str]
        Collected file scanning errors

    Returns
    -------
    str
        Human-readable diagnostic suffix, or empty string if no scan errors
    """
    if not scan_errors:
        return ""

    extra_count = len(scan_errors) - 1
    if extra_count > 0:
        return f" (scan errors in plugin files: {scan_errors[0]} +{extra_count} more)"

    return f" (scan errors in plugin files: {scan_errors[0]})"


def _check_class_in_dir(
    directory: str, class_name: str, scan_errors: list[str] | None = None
) -> bool:
    """
    Check if a class exists in any .py file in the given directory using AST.

    Parameters
    ----------
    directory : str
        Directory to search in
    class_name : str
        Name of the class to find

    Returns
    -------
    bool
        True if class exists, False otherwise
    """
    if not os.path.exists(directory):
        return False

    for filename in os.listdir(directory):
        if filename.endswith(".py") and filename != "__init__.py":
            filepath = os.path.join(directory, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    tree = ast.parse(f.read())
                    for node in tree.body:
                        if isinstance(node, ast.ClassDef) and node.name == class_name:
                            return True
            except (OSError, UnicodeError, SyntaxError, ValueError) as e:
                if scan_errors is not None:
                    scan_errors.append(f"{filename}: {type(e).__name__}: {e}")
                continue
    return False


def _check_input_exists(input_type: str, scan_errors: list[str] | None = None) -> bool:
    """
    Check if input type exists by searching for class definition in plugin files.

    Parameters
    ----------
    input_type : str
        Input type name to check

    Returns
    -------
    bool
        True if input type exists, False otherwise
    """
    src_dir = os.path.dirname(__file__)
    plugins_dir = os.path.join(src_dir, "inputs", "plugins")

    return _check_class_in_dir(plugins_dir, input_type, scan_errors=scan_errors)


def _check_llm_exists(llm_type: str, scan_errors: list[str] | None = None) -> bool:
    """
    Check if LLM type exists by searching for class definition in plugin files.

    Parameters
    ----------
    llm_type : str
        LLM type name to check

    Returns
    -------
    bool
        True if LLM type exists, False otherwise
    """
    src_dir = os.path.dirname(__file__)
    plugins_dir = os.path.join(src_dir, "llm", "plugins")

    return _check_class_in_dir(plugins_dir, llm_type, scan_errors=scan_errors)


def _check_simulator_exists(
    sim_type: str, scan_errors: list[str] | None = None
) -> bool:
    """
    Check if simulator type exists by searching for class definition in plugin files.

    Parameters
    ----------
    sim_type : str
        Simulator type name to check

    Returns
    -------
    bool
        True if simulator type exists, False otherwise
    """
    src_dir = os.path.dirname(__file__)
    plugins_dir = os.path.join(src_dir, "simulators", "plugins")

    return _check_class_in_dir(plugins_dir, sim_type, scan_errors=scan_errors)


def _check_action_exists(action_name: str) -> bool:
    """
    Check if action exists by verifying interface file presence.

    Parameters
    ----------
    action_name : str
        Action name to check

    Returns
    -------
    bool
        True if action exists, False otherwise
    """
    src_dir = os.path.dirname(__file__)
    interface_file = os.path.join(src_dir, "actions", action_name, "interface.py")
    return os.path.exists(interface_file)


def _check_background_exists(
    bg_type: str, scan_errors: list[str] | None = None
) -> bool:
    """
    Check if background type exists by searching for class definition in plugin files.

    Parameters
    ----------
    bg_type : str
        Background type name to check

    Returns
    -------
    bool
        True if background type exists, False otherwise
    """
    src_dir = os.path.dirname(__file__)
    plugins_dir = os.path.join(src_dir, "backgrounds", "plugins")

    return _check_class_in_dir(plugins_dir, bg_type, scan_errors=scan_errors)


def _check_api_key(raw_config: dict, verbose: bool):
    """
    Check API key configuration (warning only).

    Parameters
    ----------
    raw_config : dict
        Raw configuration dictionary
    verbose : bool
        Whether to print verbose output
    """
    api_key = raw_config.get("api_key", "")
    env_api_key = os.environ.get("OM_API_KEY", "")

    if (not api_key or api_key == "openmind_free") and not env_api_key:
        print()
        print("Warning: No API key configured")
        print("   Get a free key at: https://portal.openmind.org")
        print("   Or set OM_API_KEY in your .env file")
    elif verbose:
        if env_api_key:
            print("API key configured (from environment)")
        else:
            print("API key configured")


def _print_config_summary(raw_config: dict):
    """
    Print configuration summary.

    Parameters
    ----------
    raw_config : dict
        Configuration dictionary
    """
    print()
    print("Configuration Summary:")
    print("-" * 50)
    print(f"   Name: {raw_config.get('name', 'N/A')}")
    print(f"   Default Mode: {raw_config.get('default_mode')}")
    print(f"   Modes: {len(raw_config.get('modes', {}))}")
    print(f"   Transition Rules: {len(raw_config.get('transition_rules', []))}")


if __name__ == "__main__":
    # Fix for Linux multiprocessing
    if mp.get_start_method(allow_none=True) != "spawn":
        mp.set_start_method("spawn")

    dotenv.load_dotenv()
    app()
