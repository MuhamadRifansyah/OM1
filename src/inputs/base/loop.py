import asyncio
import logging
import typing as T

from inputs.base import Sensor, SensorConfig

R = T.TypeVar("R")
ConfigType = T.TypeVar("ConfigType", bound="SensorConfig")

logger = logging.getLogger(__name__)


class FuserInput(Sensor[ConfigType, R]):
    """
    Input polling implementation using a continuous asynchronous loop.

    Repeatedly polls for input events in an async loop, yielding results
    as they become available.
    """

    def __init__(self, config: ConfigType):
        """
        Initialize FuserInput instance.

        Parameters
        ----------
        config : ConfigType
            Configuration settings for the FuserInput.
        """
        super().__init__(config)

    async def _listen_loop(self) -> T.AsyncIterator[R]:
        """
        Main polling loop that continuously yields input events.

        Yields
        ------
        R
            Raw input events from polling
        """
        while True:
            try:
                yield await self._poll()
            except Exception:
                logger.exception(f"Error in input polling loop for {self.__class__.__name__}")
                await asyncio.sleep(1.0)

    async def _poll(self) -> R:
        """
        Poll for next input event.

        Returns
        -------
        R
            Raw input event

        Raises
        ------
        NotImplementedError
            Must be implemented by subclasses
        """
        raise NotImplementedError
