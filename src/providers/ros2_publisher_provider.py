#!/usr/bin/env python3
"""ROS 2 publisher provider for queued asynchronous string messages."""

import importlib
import logging
import threading
import time
from queue import Empty, Queue
from typing import Any, Optional

rclpy: Any = importlib.import_module("rclpy")
Node: Any = importlib.import_module("rclpy.node").Node
String: Any = importlib.import_module("std_msgs.msg").String

rclpy.init()


class ROS2PublisherProvider(Node):
    """
    Publisher provider for ROS 2.

    This class extends ROS 2 Node to provide a publisher that queues and
    publishes messages asynchronously in a separate thread. Messages are
    added to a queue and processed sequentially by a background thread.
    """

    def __init__(self, topic: str = "speak_topic"):
        """
        Initialize the ROS 2 Publisher Provider.

        Parameters
        ----------
        topic : str, optional
            The ROS 2 topic name to publish messages to. Defaults to
            "speak_topic". The publisher uses a queue size of 10.
        """
        try:
            super().__init__("ROS2_publisher_provider")
        except (AttributeError, RuntimeError, TypeError, ValueError) as exc:
            logging.error("Node initialization error: %s", exc)

        # Initialize the publisher.
        try:
            self.publisher_ = self.create_publisher(String, topic, 10)
            logging.info("Initialized ROS 2 publisher on topic '%s'", topic)
        except (AttributeError, RuntimeError, TypeError, ValueError) as exc:
            logging.exception("Failed to create publisher on topic '%s': %s", topic, exc)

        # Pending message queue and threading constructs
        self._pending_messages = Queue()
        self.running: bool = False
        self._thread: Optional[threading.Thread] = None

    def add_pending_message(self, text: str):
        """
        Queue a message to be published.

        Parameters
        ----------
        text : str
            The text message to publish.
        """
        try:
            msg = String()
            # Append a timestamp to the message text.
            msg.data = f"{text} - {time.time()}"
            logging.info("Queueing message: %s", msg.data)
            self._pending_messages.put(msg)
        except (AttributeError, RuntimeError, TypeError, ValueError) as exc:
            logging.exception("Error adding pending message: %s", exc)

    def _publish_message(self, msg: Any):
        """
        Publish a single message and log the result.

        Parameters
        ----------
        msg : Any
            The ROS 2 String message to publish.
        """
        try:
            self.publisher_.publish(msg)
            logging.info("Published message: %s", msg.data)
        except (AttributeError, RuntimeError, TypeError, ValueError) as exc:
            logging.exception("Error publishing message: %s", exc)

    def start(self):
        """
        Start the publisher provider by launching the processing thread.
        """
        if self.running:
            return

        self.running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logging.info("ROS2 Publisher Provider started")

    def _run(self):
        """
        Internal loop that processes and publishes pending messages.
        """
        while self.running:
            try:
                # Wait up to 0.5 seconds for a message.
                msg = self._pending_messages.get(timeout=0.5)
                self._publish_message(msg)
            except Empty:
                continue
            except (AttributeError, RuntimeError, TypeError, ValueError) as exc:
                logging.exception("Exception in publisher thread: %s", exc)

    def stop(self):
        """
        Stop the publisher provider and clean up resources.
        """
        self.running = False

        if self._thread:
            self._thread.join(timeout=5)

        publisher = getattr(self, "publisher_", None)
        close_method = getattr(publisher, "Close", None)
        if callable(close_method):
            close_method()
        else:
            logging.warning(
                "Publisher does not implement Close(); skipping publisher cleanup."
            )

        logging.info("ROS2 Publisher Provider stopped")
