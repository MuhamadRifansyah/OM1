"""Focused pylint-friendly tests for UnitreeGo2LocationsProvider."""

import time
from unittest.mock import MagicMock, patch

from providers.unitree_go2_locations_provider import UnitreeGo2LocationsProvider


def test_custom_constructor_values_are_exposed() -> None:
    """Custom constructor arguments should be reflected by provider fields."""
    setattr(UnitreeGo2LocationsProvider, "_singleton_instance", None)
    provider = UnitreeGo2LocationsProvider(
        base_url="http://localhost:5000/custom-go2",
        timeout=9,
        refresh_interval=2,
    )
    try:
        assert provider.base_url == "http://localhost:5000/custom-go2"
        assert provider.timeout == 9
        assert provider.refresh_interval == 2
    finally:
        provider.stop()
        setattr(UnitreeGo2LocationsProvider, "_singleton_instance", None)


def test_go2_http_failure_sets_freshness_error() -> None:
    """HTTP failures should increment failure count and preserve empty cache."""
    response = MagicMock()
    response.status_code = 503
    response.text = "Service Unavailable"

    with patch("providers.locations_provider_base.requests.get", return_value=response):
        setattr(UnitreeGo2LocationsProvider, "_singleton_instance", None)
        provider = UnitreeGo2LocationsProvider(refresh_interval=1)
        try:
            provider.start()
            time.sleep(0.04)
        finally:
            provider.stop()
            setattr(UnitreeGo2LocationsProvider, "_singleton_instance", None)

    freshness = provider.get_cache_freshness()
    assert freshness["has_cache"] is False
    assert freshness["consecutive_fetch_failures"] >= 1
    assert freshness["last_fetch_error"] == "HTTP 503"
