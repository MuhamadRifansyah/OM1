from unittest.mock import Mock, patch

import numpy as np
import pytest

from inputs.base import Message
from inputs.plugins.environment_ocr_input import (
    EnvironmentOCRInput,
    EnvironmentOCRInputConfig,
)


@pytest.fixture
def mock_check_webcam():
    with patch("inputs.plugins.environment_ocr_input._check_webcam", return_value=True):
        yield


@pytest.fixture
def mock_cv2_video_capture():
    with patch("inputs.plugins.environment_ocr_input.cv2.VideoCapture") as mock:
        mock_instance = Mock()
        dummy_frame = np.zeros((200, 300, 3), dtype=np.uint8)
        mock_instance.read.return_value = (True, dummy_frame)
        mock_instance.get.side_effect = lambda x: {3: 300, 4: 200}[x]
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_easyocr_reader():
    with patch("inputs.plugins.environment_ocr_input.easyocr.Reader") as mock:
        mock_instance = Mock()
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_io_provider():
    with patch("inputs.plugins.environment_ocr_input.IOProvider") as mock_class:
        mock_instance = Mock()
        mock_class.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def ocr_input(
    mock_check_webcam, mock_cv2_video_capture, mock_easyocr_reader, mock_io_provider
):
    config = EnvironmentOCRInputConfig(
        camera_index=0,
        languages=("en",),
        min_confidence=0.5,
        max_detections=5,
        poll_interval_s=0.0,
        gpu=False,
    )
    return EnvironmentOCRInput(config=config)


def test_format_detections_single(ocr_input):
    result = ocr_input._format_detections([("EXIT", "on your left", 0.9)])
    assert result == 'You see text "EXIT" on your left.'


def test_format_detections_multiple(ocr_input):
    result = ocr_input._format_detections(
        [("EXIT", "on your left", 0.9), ("Room 101", "in front of you", 0.8)]
    )
    assert result == (
        'You see text "EXIT" on your left. You also see text "Room 101" in front of you.'
    )


def test_ocr_frame_filters_and_adds_direction(ocr_input, mock_easyocr_reader):
    # width=300 => cam_third=100
    ocr_input.cam_third = 100
    mock_easyocr_reader.readtext.return_value = [
        # Left side
        ([[0, 0], [10, 0], [10, 10], [0, 10]], "EXIT", 0.91),
        # Center
        ([[140, 0], [160, 0], [160, 10], [140, 10]], "Room 101", 0.80),
        # Below threshold
        ([[250, 0], [290, 0], [290, 10], [250, 10]], "LOW", 0.10),
    ]

    frame = np.zeros((200, 300, 3), dtype=np.uint8)
    detections = ocr_input._ocr_frame(frame)

    assert detections == [
        ("EXIT", "on your left", 0.91),
        ("Room 101", "in front of you", 0.8),
    ]


@pytest.mark.asyncio
async def test_raw_to_text_returns_message(ocr_input, mock_easyocr_reader):
    mock_easyocr_reader.readtext.return_value = [
        ([[0, 0], [10, 0], [10, 10], [0, 10]], "EXIT", 0.91),
    ]
    frame = np.zeros((200, 300, 3), dtype=np.uint8)
    msg = await ocr_input._raw_to_text(frame)
    assert msg is not None
    assert msg.message == 'You see text "EXIT" on your left.'


def test_formatted_latest_buffer_records_input(ocr_input, mock_io_provider):
    ocr_input.messages = []
    ocr_input.messages.append(
        Message(timestamp=1.0, message='You see text "EXIT" on your left.')
    )

    buf = ocr_input.formatted_latest_buffer()
    assert buf is not None
    assert 'You see text "EXIT" on your left.' in buf
    mock_io_provider.add_input.assert_called_once()
    assert ocr_input.messages == []


def test_formatted_latest_buffer_empty(ocr_input):
    ocr_input.messages = []
    assert ocr_input.formatted_latest_buffer() is None
