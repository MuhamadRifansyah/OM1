"""Tests for UnitreeG1LocationsProvider."""

import time
from contextlib import contextmanager
from typing import Iterator
from unittest.mock import MagicMock, patch

from providers.unitree_g1_locations_provider import UnitreeG1LocationsProvider


def _reset_provider_singleton() -> None:
    """Reset singleton state when reset API is available."""
    setattr(UnitreeG1LocationsProvider, "_singleton_instance", None)


@contextmanager
def managed_provider(**kwargs) -> Iterator[UnitreeG1LocationsProvider]:
    """Create and dispose a provider instance with clean singleton state."""
    _reset_provider_singleton()
    provider = UnitreeG1LocationsProvider(**kwargs)
    try:
        yield provider
    finally:
        provider.stop()
        _reset_provider_singleton()


def test_initial_freshness_state_is_empty() -> None:
    """Fresh provider reports empty cache and no previous success."""
    with managed_provider() as provider:
        freshness = provider.get_cache_freshness()

        assert provider.base_url == "http://localhost:5000/maps/locations/list"
        assert provider.timeout == 5
        assert provider.refresh_interval == 30
        assert not provider.get_all_locations()
        assert freshness["has_cache"] is False
        assert freshness["last_success_age_sec"] is None
        assert freshness["consecutive_fetch_failures"] == 0
        assert freshness["last_fetch_error"] is None


def test_lookup_is_case_insensitive_after_successful_refresh() -> None:
    """Location lookup normalizes labels after cache refresh."""
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "Kitchen": {"name": "Kitchen", "pose": {"x": 3.0, "y": 4.0}},
    }

    with patch("providers.locations_provider_base.requests.get", return_value=response):
        with managed_provider(refresh_interval=1) as provider:
            provider.start()
            time.sleep(0.05)

            location = provider.get_location("kItChEn")
            assert location is not None
            assert location["name"] == "Kitchen"

            freshness = provider.get_cache_freshness()
            assert freshness["has_cache"] is True
            assert freshness["consecutive_fetch_failures"] == 0


def test_failure_does_not_clear_existing_cache_and_marks_stale() -> None:
    """Cache remains available while freshness reports failure streaks."""
    success_response = MagicMock()
    success_response.status_code = 200
    success_response.json.return_value = {
        "home": {"name": "Home", "pose": {"x": 0.0, "y": 0.0}},
    }

    failure_response = MagicMock()
    failure_response.status_code = 500
    failure_response.text = "Internal Server Error"

    call_counter = {"value": 0}

    def request_side_effect(*_args, **_kwargs):
        call_counter["value"] += 1
        if call_counter["value"] == 1:
            return success_response
        return failure_response

    with patch(
        "providers.locations_provider_base.requests.get",
        side_effect=request_side_effect,
    ):
        with managed_provider(refresh_interval=0.01) as provider:
            provider.start()
            time.sleep(0.07)

            cached = provider.get_all_locations()
            assert "home" in cached

            freshness = provider.get_cache_freshness()
            assert freshness["has_cache"] is True
            assert freshness["last_success_age_sec"] is not None
            assert freshness["consecutive_fetch_failures"] >= 1
            assert freshness["last_fetch_error"] == "HTTP 500"


def test_empty_base_url_skips_http_fetch() -> None:
    """Provider should not issue HTTP requests when base URL is empty."""
    with patch("providers.locations_provider_base.requests.get") as mock_get:
        with managed_provider(base_url="", refresh_interval=1) as provider:
            provider.start()
            time.sleep(0.03)

        assert mock_get.call_count == 0
