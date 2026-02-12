"""Zenoh-backed provider for runtime configuration requests."""

import json
import logging
import os
from uuid import uuid4

import json5  # type: ignore[import-not-found]  # pylint: disable=import-error
import zenoh  # type: ignore[import-not-found]  # pylint: disable=import-error

from zenoh_msgs import (
    ConfigRequest,
    ConfigResponse,
    String,
    open_zenoh_session,
    prepare_header,
)

from .singleton import singleton


@singleton
class ConfigProvider:  # pylint: disable=too-few-public-methods
    """
    Singleton provider for runtime configuration broadcasting via Zenoh.
    """

    def __init__(self):
        """
        Initialize the ConfigProvider.
        """
        self.session = None
        self.config_response_publisher = None
        self.config_request_subscriber = None
        self.running = False

        self.config_path = self._get_runtime_config_path()

        self._initialize_zenoh()

    def _initialize_zenoh(self):
        """
        Initialize Zenoh session, publishers, and subscriber.
        """
        try:
            self.session = open_zenoh_session()

            # Publisher for config responses
            self.config_response_publisher = self.session.declare_publisher(
                "om/config/response"
            )

            # Subscriber for config requests
            self.config_request_subscriber = self.session.declare_subscriber(
                "om/config/request", self._handle_config_request
            )

            self.running = True
            logging.info("ConfigProvider initialized with Zenoh")
        except Exception as e:  # pylint: disable=broad-exception-caught
            logging.error("Failed to initialize ConfigProvider Zenoh session: %s", e)

    def _get_runtime_config_path(self) -> str:
        """
        Get the path to the runtime config file in memory folder.

        Returns
        -------
        str
            Path to config/memory/.runtime.json5
        """
        memory_folder_path = os.path.join(
            os.path.dirname(__file__), "../../config", "memory"
        )
        return os.path.abspath(os.path.join(memory_folder_path, ".runtime.json5"))

    def _handle_config_request(self, sample: zenoh.Sample):
        """
        Handle incoming config requests from Zenoh subscriber.

        Responds with current runtime configuration.

        Parameters
        ----------
        sample : zenoh.Sample
            The Zenoh sample containing the serialized ConfigRequest message.
        """
        try:
            request = ConfigRequest.deserialize(sample.payload.to_bytes())
            logging.debug("Received config request: %s", request.request_id)

            if request.config and request.config.data:
                # This is a set_config request
                self._handle_set_config(request.request_id, request.config.data)
            else:
                # This is a get_config request
                self._send_config_response(request.request_id)

        except Exception as e:  # pylint: disable=broad-exception-caught
            logging.error("Error handling config request: %s", e)

    def _handle_set_config(self, request_id: String, config_str: str):
        """
        Handle request to update runtime configuration.
        """
        try:
            new_config = json5.loads(config_str)

            temp_path = self.config_path + f".tmp.{uuid4()}"
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(new_config, f, indent=2)

            os.rename(temp_path, self.config_path)

            logging.info("Updated runtime config file: %s", self.config_path)

            self._send_config_response(request_id)

        except Exception as e:  # pylint: disable=broad-exception-caught
            logging.error("Failed to update config: %s", e)
            self._send_error_response(request_id, f"Failed to update config: {e}")

    def _send_config_response(self, request_id: String):
        """
        Send current runtime configuration as response.
        """
        try:
            # Get current config
            config_snapshot, error_message = self._get_config_snapshot()
            if error_message:
                self._send_error_response(request_id, error_message)
                return

            config_json_str = json.dumps(config_snapshot, indent=2)

            response = ConfigResponse(
                header=prepare_header(str(uuid4())),
                request_id=request_id,
                config=String(config_json_str),
                message=String("Configuration retrieved successfully"),
            )

            if self.config_response_publisher:
                self.config_response_publisher.put(response.serialize())
                logging.info("ConfigProvider sent config response")

        except Exception as e:  # pylint: disable=broad-exception-caught
            logging.error("Failed to send config response: %s", e)
            self._send_error_response(request_id, str(e))

    def _send_error_response(self, request_id: String, error_message: str):
        """
        Send error response.
        """
        try:
            response = ConfigResponse(
                header=prepare_header(str(uuid4())),
                request_id=request_id,
                config=String(""),
                message=String(error_message),
            )

            if self.config_response_publisher:
                self.config_response_publisher.put(response.serialize())
                logging.warning("ConfigProvider sent error response: %s", error_message)

        except Exception as e:  # pylint: disable=broad-exception-caught
            logging.error("Failed to send error response: %s", e)

    def _get_config_snapshot(self) -> tuple[dict, str | None]:
        """
        Get a snapshot of the current runtime configuration.

        Returns
        -------
        tuple[dict, str | None]
            A tuple of (config snapshot, error message). Error message is None on success.
        """
        if not os.path.exists(self.config_path):
            message = f"ConfigProvider: Config file not found: {self.config_path}"
            logging.warning(message)
            return {}, message

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json5.load(f), None

        except Exception as e:  # pylint: disable=broad-exception-caught
            message = f"Failed to read config file {self.config_path}: {e}"
            logging.error(message)
            return {}, message

    def stop(self):
        """
        Stop the ConfigProvider and cleanup Zenoh session.
        """
        if not self.running:
            logging.info("ConfigProvider is not running")
            return

        self.running = False

        if self.config_request_subscriber:
            self.config_request_subscriber.undeclare()
            self.config_request_subscriber = None

        if self.config_response_publisher:
            self.config_response_publisher.undeclare()
            self.config_response_publisher = None

        if self.session:
            self.session.close()

        logging.info("ConfigProvider stopped and Zenoh session closed")
