"""DataUpdateCoordinator for goCoax MoCA integration."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_SCAN_INTERVAL,
    DEFAULT_PASSWORD,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_USERNAME,
    DOMAIN,
)
from .pygocoax import AdapterStatus, GoCoaxClient
from .pygocoax.exceptions import (
    GoCoaxAuthError,
    GoCoaxConnectionError,
    GoCoaxTimeoutError,
)

if TYPE_CHECKING:
    pass

LOG = logging.getLogger(__name__)


class GoCoaxCoordinator(DataUpdateCoordinator[AdapterStatus]):
    """Coordinator for goCoax MoCA adapter data."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self._host = entry.data[CONF_HOST]
        self._username = entry.data.get(CONF_USERNAME, DEFAULT_USERNAME)
        self._password = entry.data.get(CONF_PASSWORD, DEFAULT_PASSWORD)
        self._entry = entry

        # get scan interval from options or use default
        scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

        super().__init__(
            hass,
            LOG,
            name=f"{DOMAIN}_{self._host}",
            update_interval=timedelta(seconds=scan_interval),
            config_entry=entry,
        )

        # create client with shared session
        session = async_get_clientsession(hass)
        self._client = GoCoaxClient(
            host=self._host,
            username=self._username,
            password=self._password,
            session=session,
        )

        self._consecutive_errors = 0
        self._max_consecutive_errors = 5

    @property
    def host(self) -> str:
        """Return the host address."""
        return self._host

    @property
    def mac_address(self) -> str | None:
        """Return the MAC address if available."""
        if self.data:
            return self.data.mac_address
        return None

    async def _async_update_data(self) -> AdapterStatus:
        """Fetch data from goCoax adapter."""
        try:
            status = await self._client.get_status()
            self._consecutive_errors = 0
            LOG.debug(
                f"Updated goCoax data: mac={status.mac_address}, "
                f"link={status.link_status}, moca={status.moca_version}"
            )
            return status

        except GoCoaxAuthError as err:
            self._consecutive_errors += 1
            LOG.error(f"Authentication failed for goCoax at {self._host}")
            raise ConfigEntryAuthFailed(
                f"Authentication failed for goCoax adapter at {self._host}"
            ) from err

        except GoCoaxTimeoutError as err:
            self._consecutive_errors += 1
            LOG.warning(
                f"Timeout communicating with goCoax at {self._host} "
                f"(error {self._consecutive_errors}/{self._max_consecutive_errors})"
            )
            if self._consecutive_errors >= self._max_consecutive_errors:
                raise UpdateFailed(
                    f"Too many consecutive timeouts for goCoax at {self._host}"
                ) from err
            # return stale data if available
            if self.data:
                return self.data
            raise UpdateFailed(f"Timeout connecting to goCoax at {self._host}") from err

        except GoCoaxConnectionError as err:
            self._consecutive_errors += 1
            LOG.warning(
                f"Connection error to goCoax at {self._host}: {err} "
                f"(error {self._consecutive_errors}/{self._max_consecutive_errors})"
            )
            if self._consecutive_errors >= self._max_consecutive_errors:
                raise UpdateFailed(
                    f"Too many consecutive errors for goCoax at {self._host}"
                ) from err
            # return stale data if available
            if self.data:
                return self.data
            raise UpdateFailed(f"Cannot connect to goCoax at {self._host}") from err

        except Exception as err:
            self._consecutive_errors += 1
            LOG.exception(f"Unexpected error fetching goCoax data from {self._host}")
            raise UpdateFailed(f"Unexpected error: {err}") from err

    async def async_shutdown(self) -> None:
        """Shutdown the coordinator."""
        await super().async_shutdown()
        # client uses shared session, don't close it
