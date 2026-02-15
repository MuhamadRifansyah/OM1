"""Unitree G1 periodic locations provider."""

from .locations_provider_base import LocationsProviderBase
from .singleton import singleton


@singleton
class UnitreeG1LocationsProvider(LocationsProviderBase):
    """Fetch and cache navigation locations for Unitree G1."""

    def __init__(
        self,
        base_url: str = "http://localhost:5000/maps/locations/list",
        timeout: int = 5,
        refresh_interval: int = 30,
    ) -> None:
        super().__init__(
            base_url=base_url,
            timeout=timeout,
            refresh_interval=refresh_interval,
            provider_name="UnitreeG1LocationsProvider",
        )
