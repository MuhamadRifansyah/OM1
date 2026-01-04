"""Utilities for configuration loading and environment variable handling."""

import logging
import os
from typing import Dict


def apply_env_variable_fallbacks(config: Dict) -> Dict:
    """
    Apply environment variable fallbacks for key configuration fields.

    Checks for environment variables and applies them as fallbacks when config
    values are missing, empty, or have default values. This preserves the original
    behavior across single-mode and multi-mode configurations.

    Supported fallbacks:
    - ROBOT_IP: Used when config robot_ip is None, empty, or "192.168.0.241"
    - OM_API_KEY: Used when config api_key is None, empty, or "openmind_free"
    - URID: Used when config URID is "default"

    Parameters
    ----------
    config : Dict
        Configuration dictionary to update with environment variable fallbacks

    Returns
    -------
    Dict
        The updated configuration dictionary with env variable fallbacks applied

    Notes
    -----
    This function modifies the input dictionary in-place and also returns it.
    Logging is performed at INFO level on success and WARNING level on missing values.
    """
    # Handle robot_ip fallback
    g_robot_ip = config.get("robot_ip", None)
    if g_robot_ip is None or g_robot_ip == "" or g_robot_ip == "192.168.0.241":
        logging.warning("No robot ip found in the configuration. Checking .env file.")
        backup_key = os.environ.get("ROBOT_IP")
        if backup_key:
            config["robot_ip"] = backup_key
            g_robot_ip = backup_key
            logging.info("Found ROBOT_IP in .env file.")
        else:
            logging.warning(
                "Could not find robot ip address. Please find your robot IP address and add it to the configuration or .env file."
            )

    # Handle api_key fallback
    g_api_key = config.get("api_key", None)
    if g_api_key is None or g_api_key == "" or g_api_key == "openmind_free":
        logging.warning("No API key found in the configuration. Checking .env file.")
        backup_key = os.environ.get("OM_API_KEY")
        if backup_key:
            config["api_key"] = backup_key
            g_api_key = backup_key
            logging.info("Found OM_API_KEY in .env file. Success.")
        else:
            logging.warning(
                "Could not find any API keys. Please get a free key at portal.openmind.org."
            )

    # Handle URID fallback
    g_URID = config.get("URID", None)
    if g_URID is None or g_URID == "":
        logging.warning(
            "No URID found in the configuration. Multirobot deployments will conflict."
        )

    if g_URID == "default":
        logging.info("Checking for backup URID in .env file.")
        backup_URID = os.environ.get("URID")
        if backup_URID:
            config["URID"] = backup_URID
            g_URID = backup_URID
            logging.info("Found URID in .env file.")
        else:
            logging.warning(
                "Could not find backup URID in .env file. Using 'default'. Multirobot deployments will conflict."
            )

    return config
