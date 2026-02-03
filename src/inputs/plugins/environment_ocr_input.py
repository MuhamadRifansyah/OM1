import asyncio
import logging
import time
from typing import Optional, Sequence

import cv2
import easyocr
import numpy as np
from pydantic import Field

from inputs.base import Message, SensorConfig
from inputs.base.loop import FuserInput
from providers.io_provider import IOProvider


class EnvironmentOCRInputConfig(SensorConfig):
    """
    Configuration for Environment OCR Input.

    Parameters
    ----------
    camera_index : int
        Index of the camera device.
    languages : Sequence[str]
        EasyOCR language codes to load. Defaults to English ("en").
    min_confidence : float
        Minimum confidence threshold for including detections (0.0 - 1.0).
    max_detections : int
        Maximum number of text detections to report per frame.
    poll_interval_s : float
        Poll interval in seconds.
    gpu : bool
        Whether to enable GPU usage for OCR.
    """

    camera_index: int = Field(default=0, description="Index of the camera device")
    languages: Sequence[str] = Field(
        default_factory=lambda: ("en",),
        description="OCR languages (EasyOCR language codes)",
    )
    min_confidence: float = Field(
        default=0.5, description="Minimum OCR confidence threshold"
    )
    max_detections: int = Field(
        default=5, description="Maximum number of text detections per poll"
    )
    poll_interval_s: float = Field(
        default=0.5, description="Polling interval (seconds)"
    )
    gpu: bool = Field(default=False, description="Enable GPU for OCR")


def _check_webcam(index_to_check: int) -> bool:
    cap = cv2.VideoCapture(index_to_check)
    if not cap.isOpened():
        logging.info("OCR did not find cam: %s", index_to_check)
        return False
    logging.info("OCR found cam: %s", index_to_check)
    return True


class EnvironmentOCRInput(FuserInput[EnvironmentOCRInputConfig, Optional[np.ndarray]]):
    """
    Reads text in the robot's environment using OCR over camera frames.
    """

    def __init__(self, config: EnvironmentOCRInputConfig):
        super().__init__(config)

        self.io_provider = IOProvider()
        self.messages: list[Message] = []

        self.descriptor_for_LLM = "Text Reader"

        self.have_cam = _check_webcam(self.config.camera_index)
        self.cap: Optional[cv2.VideoCapture] = None
        self.width = 0
        self.height = 0
        self.cam_third = 0
        if self.have_cam:
            self.cap = cv2.VideoCapture(self.config.camera_index)
            self.width = int(self.cap.get(3))
            self.height = int(self.cap.get(4))
            self.cam_third = int(self.width / 3) if self.width > 0 else 0
            logging.info("OCR webcam dimensions: %s, %s", self.width, self.height)

        self._reader = easyocr.Reader(list(self.config.languages), gpu=self.config.gpu)

    async def _poll(self) -> Optional[np.ndarray]:
        await asyncio.sleep(self.config.poll_interval_s)

        if self.have_cam and self.cap is not None:
            _ret, frame = self.cap.read()
            return frame
        return None

    @staticmethod
    def _direction_for_bbox_center_x(center_x: float, cam_third: int) -> str:
        if cam_third <= 0:
            return "in front of you"
        if center_x < cam_third:
            return "on your left"
        if center_x > 2 * cam_third:
            return "on your right"
        return "in front of you"

    def _ocr_frame(self, frame_bgr: np.ndarray) -> list[tuple[str, str, float]]:
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        results = self._reader.readtext(frame_rgb, detail=1)

        filtered: list[tuple[str, str, float]] = []
        for bbox, text, confidence in results:
            if not isinstance(text, str) or text.strip() == "":
                continue
            try:
                conf = float(confidence)
            except Exception:
                continue
            if conf < float(self.config.min_confidence):
                continue

            try:
                xs = [float(p[0]) for p in bbox]
            except Exception:
                continue
            if not xs:
                continue
            center_x = (min(xs) + max(xs)) / 2.0
            direction = self._direction_for_bbox_center_x(center_x, self.cam_third)

            filtered.append((text.strip(), direction, conf))

        filtered.sort(key=lambda x: x[2], reverse=True)
        return filtered[: max(0, int(self.config.max_detections))]

    def _format_detections(
        self, detections: list[tuple[str, str, float]]
    ) -> Optional[str]:
        if not detections:
            return None

        sentences: list[str] = []
        for i, (text, direction, _confidence) in enumerate(detections):
            prefix = "You see text" if i == 0 else "You also see text"
            sentences.append(f'{prefix} "{text}" {direction}.')

        return " ".join(sentences)

    async def _raw_to_text(self, raw_input: Optional[np.ndarray]) -> Optional[Message]:
        if raw_input is None:
            return None

        try:
            detections = self._ocr_frame(raw_input)
            sentence = self._format_detections(detections)
        except Exception:
            logging.exception("Error running OCR on camera frame")
            return None

        if sentence is None:
            return None
        return Message(timestamp=time.time(), message=sentence)

    async def raw_to_text(self, raw_input: Optional[np.ndarray]):
        pending_message = await self._raw_to_text(raw_input)
        if pending_message is not None:
            self.messages.append(pending_message)

    def formatted_latest_buffer(self) -> Optional[str]:
        if len(self.messages) == 0:
            return None

        latest_message = self.messages[-1]
        self.io_provider.add_input(
            self.descriptor_for_LLM, latest_message.message, latest_message.timestamp
        )
        self.messages = []

        return f"""
{self.descriptor_for_LLM} INPUT
// START
{latest_message.message}
// END
"""
