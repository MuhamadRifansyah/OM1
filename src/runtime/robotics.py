"""Runtime helpers for robotics channel initialization."""

import importlib
import logging


def load_unitree(unitree_ethernet: str):
    """
    Initialize the Unitree robot's network communication channel.

    This function sets up the Ethernet connection for a Unitree robot based on
    the provided configuration or environment variables. It can operate in either
    real hardware or simulation mode.

    Parameters
    ----------
    unitree_ethernet : str
        Configuration object containing the Unitree Ethernet adapter string, such as "eth0"

    Returns
    -------
    None

    Raises
    ------
    RuntimeError
        If initialization of the Unitree Ethernet channel fails.

    """
    if unitree_ethernet is not None:
        logging.info(
            "Using %s as the Unitree Network Ethernet Adapter", unitree_ethernet
        )

        try:
            channel_module = importlib.import_module(
                "unitree.unitree_sdk2py.core.channel"
            )
            channel_factory_initialize = getattr(
                channel_module, "ChannelFactoryInitialize"
            )
            channel_factory_initialize(0, unitree_ethernet)
        except Exception as exc:
            logging.exception(
                "Failed to initialize Unitree Ethernet channel for adapter '%s'",
                unitree_ethernet,
            )
            raise RuntimeError(
                f"Failed to initialize Unitree Ethernet channel '{unitree_ethernet}'"
            ) from exc
        logging.info("Booting Unitree and CycloneDDS")
