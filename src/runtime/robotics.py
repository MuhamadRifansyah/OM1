import logging
from typing import Optional


def load_unitree(unitree_ethernet: Optional[str]) -> None:
    """
    Initialize the Unitree robot's network communication channel.

    This function sets up the Ethernet connection for a Unitree robot based on
    the provided configuration or environment variables. It can operate in either
    real hardware or simulation mode.

    Parameters
    ----------
    unitree_ethernet : Optional[str]
        The Unitree Ethernet adapter string, such as "eth0".

    Returns
    -------
    None
    """
    if not unitree_ethernet:
        return

    logging.info("Using %s as the Unitree Network Ethernet Adapter", unitree_ethernet)

    from unitree.unitree_sdk2py.core.channel import ChannelFactoryInitialize

    try:
        ChannelFactoryInitialize(0, unitree_ethernet)
    except Exception:
        logging.exception(
            "Failed to initialize Unitree Ethernet channel for adapter %s",
            unitree_ethernet,
        )
        logging.warning("Continuing without Unitree DDS initialization")
        return

    logging.info("Booting Unitree and CycloneDDS")
