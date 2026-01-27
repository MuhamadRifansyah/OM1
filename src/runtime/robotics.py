import logging
from .error_context import (
    ErrorContext,
    log_exception_with_context,
    ContextualException,
    ContextInfo,
)

logger = logging.getLogger(__name__)


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
    ContextualException
        If initialization of the Unitree Ethernet channel fails.

    """
    if unitree_ethernet is not None:
        logger.info(
            f"Using {unitree_ethernet} as the Unitree Network Ethernet Adapter"
        )

        from unitree.unitree_sdk2py.core.channel import ChannelFactoryInitialize

        try:
            ChannelFactoryInitialize(0, unitree_ethernet)
        except Exception as e:
            log_exception_with_context(
                logger=logger,
                context=ErrorContext.NETWORK_COMMUNICATION,
                operation="Initialize Unitree Ethernet channel",
                exc=e,
                component="Unitree",
                details={"adapter": unitree_ethernet},
            )
            context_info = ContextInfo(
                error_context=ErrorContext.NETWORK_COMMUNICATION,
                operation="Initialize Unitree Ethernet channel",
                component="Unitree",
                details={"adapter": unitree_ethernet},
                parent_exception=e,
            )
            raise ContextualException(
                context=context_info,
                message=f"Failed to initialize Unitree on adapter {unitree_ethernet}",
                cause=e,
            ) from e
        logger.info("Booting Unitree and CycloneDDS")
