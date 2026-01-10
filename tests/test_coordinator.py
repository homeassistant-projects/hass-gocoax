"""Tests for goCoax MoCA coordinator."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.gocoax.const import DEFAULT_SCAN_INTERVAL, DOMAIN
from custom_components.gocoax.coordinator import GoCoaxCoordinator
from custom_components.gocoax.pygocoax import AdapterStatus
from custom_components.gocoax.pygocoax.exceptions import (
    GoCoaxAuthError,
    GoCoaxConnectionError,
    GoCoaxTimeoutError,
)

from .conftest import MOCK_HOST, MOCK_MAC, MOCK_PASSWORD, MOCK_USERNAME


@pytest.fixture
def mock_entry(hass: HomeAssistant):
    """Create mock config entry."""
    from homeassistant import config_entries

    entry = config_entries.ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title=f"goCoax ({MOCK_HOST})",
        data={
            CONF_HOST: MOCK_HOST,
            CONF_USERNAME: MOCK_USERNAME,
            CONF_PASSWORD: MOCK_PASSWORD,
        },
        source=config_entries.SOURCE_USER,
        unique_id=MOCK_MAC,
    )
    entry.add_to_hass(hass)
    return entry


async def test_coordinator_update_success(
    hass: HomeAssistant,
    mock_entry,
    mock_adapter_status: AdapterStatus,  # noqa: ARG001
    mock_coordinator_client,  # noqa: ARG001
) -> None:
    """Test successful coordinator update."""
    coordinator = GoCoaxCoordinator(hass, mock_entry)

    await coordinator.async_config_entry_first_refresh()

    assert coordinator.data is not None
    assert coordinator.data.mac_address == MOCK_MAC
    assert coordinator.data.link_status is True
    assert coordinator.data.moca_version == "2.5"


async def test_coordinator_auth_error(
    hass: HomeAssistant,
    mock_entry,
) -> None:
    """Test coordinator handles auth error."""
    with patch(
        "custom_components.gocoax.coordinator.GoCoaxClient"
    ) as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.get_status = AsyncMock(side_effect=GoCoaxAuthError("Auth failed"))

        coordinator = GoCoaxCoordinator(hass, mock_entry)

        with pytest.raises(ConfigEntryAuthFailed):
            await coordinator.async_config_entry_first_refresh()


async def test_coordinator_connection_error(
    hass: HomeAssistant,
    mock_entry,
) -> None:
    """Test coordinator handles connection error."""
    with patch(
        "custom_components.gocoax.coordinator.GoCoaxClient"
    ) as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.get_status = AsyncMock(
            side_effect=GoCoaxConnectionError("Connection failed")
        )

        coordinator = GoCoaxCoordinator(hass, mock_entry)

        with pytest.raises(UpdateFailed):
            await coordinator.async_config_entry_first_refresh()


async def test_coordinator_timeout_with_stale_data(
    hass: HomeAssistant,
    mock_entry,
    mock_adapter_status: AdapterStatus,
) -> None:
    """Test coordinator returns stale data on timeout."""
    with patch(
        "custom_components.gocoax.coordinator.GoCoaxClient"
    ) as mock_client_class:
        mock_client = mock_client_class.return_value
        # first call succeeds, subsequent calls timeout
        mock_client.get_status = AsyncMock(
            side_effect=[
                mock_adapter_status,
                GoCoaxTimeoutError("Timeout"),
            ]
        )

        coordinator = GoCoaxCoordinator(hass, mock_entry)

        # first update succeeds
        await coordinator.async_config_entry_first_refresh()
        assert coordinator.data is not None
        assert coordinator.data.mac_address == MOCK_MAC

        # second update returns stale data
        await coordinator.async_refresh()
        # should still have data (stale)
        assert coordinator.data is not None


async def test_coordinator_update_interval(
    hass: HomeAssistant,
    mock_entry,
    mock_coordinator_client,  # noqa: ARG001
) -> None:
    """Test coordinator uses correct update interval."""
    coordinator = GoCoaxCoordinator(hass, mock_entry)

    assert coordinator.update_interval == timedelta(seconds=DEFAULT_SCAN_INTERVAL)
