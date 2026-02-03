import json
import os
from unittest.mock import Mock, patch

import pytest

import providers.config_provider as config_provider


@pytest.fixture(autouse=True)
def reset_singleton():
    config_provider.ConfigProvider.reset()
    yield
    config_provider.ConfigProvider.reset()


def _make_provider(tmp_path):
    dummy_session = Mock()
    dummy_session.declare_publisher.return_value = Mock(put=Mock())
    dummy_session.declare_subscriber.return_value = Mock(undeclare=Mock())

    with (
        patch("providers.config_provider.open_zenoh_session", return_value=dummy_session),
        patch.object(
            config_provider.ConfigProvider._singleton_class,
            "_get_runtime_config_path",
            return_value=str(tmp_path / ".runtime.json5"),
        ),
    ):
        provider = config_provider.ConfigProvider()

    return provider


def test_handle_set_config_uses_os_replace(tmp_path):
    provider = _make_provider(tmp_path)

    config_path = provider.config_path
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, "w") as f:
        f.write('{"old": true}')

    provider._send_config_response = Mock()

    real_replace = os.replace
    with patch("providers.config_provider.os.replace") as mock_replace:
        mock_replace.side_effect = real_replace
        provider._handle_set_config(request_id=Mock(), config_str='{"new": true}')
        mock_replace.assert_called_once()

    with open(config_path, "r") as f:
        updated = json.load(f)
    assert updated == {"new": True}


def test_send_config_response_sends_error_when_config_missing(tmp_path):
    provider = _make_provider(tmp_path)

    provider.config_response_publisher = Mock(put=Mock())
    provider._send_error_response = Mock()

    provider._send_config_response(request_id=Mock())

    provider._send_error_response.assert_called_once()
