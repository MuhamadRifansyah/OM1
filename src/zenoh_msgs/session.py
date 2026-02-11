"""Zenoh session helpers for local or discovery-based connections."""

import logging

# pylint: disable=import-error
import zenoh  # type: ignore[import-not-found]
# pylint: enable=import-error


def create_zenoh_config(network_discovery: bool = True) -> zenoh.Config:
    """
    Create a Zenoh configuration for a client connecting to a local server.

    Parameters
    ----------
    network_discovery : bool, optional
        Whether to enable network discovery (default is True).

    Returns
    -------
    zenoh.Config
        The Zenoh configuration object.
    """
    config = zenoh.Config()
    if not network_discovery:
        config.insert_json5("mode", '"client"')
        config.insert_json5("connect/endpoints", '["tcp/127.0.0.1:7447"]')

    return config


def open_zenoh_session() -> zenoh.Session:
    """
    Open a Zenoh session with a local connection first, then fall back to network discovery.

    Returns
    -------
    zenoh.Session
        The opened Zenoh session.

    Raises
    ------
    Exception
        If unable to open a Zenoh session.
    """
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO)

    local_config = create_zenoh_config(network_discovery=False)
    try:
        session = zenoh.open(local_config)
        logging.info("Zenoh client opened without network discovery")
        return session
    except Exception:  # pylint: disable=broad-exception-caught
        logging.info("Falling back to network discovery...")

    config = create_zenoh_config()
    try:
        session = zenoh.open(config)
        logging.info("Zenoh client opened with network discovery")
        return session
    except Exception as e:  # pylint: disable=broad-exception-caught
        logging.error("Error opening Zenoh client: %s", e)
        # pylint: disable=broad-exception-raised
        raise Exception("Failed to open Zenoh session") from e
        # pylint: enable=broad-exception-raised


if __name__ == "__main__":
    zenoh_session = open_zenoh_session()
    if zenoh_session:
        logging.info("Session opened successfully")
        zenoh_session.close()
    else:
        logging.error("Failed to open Zenoh session")
