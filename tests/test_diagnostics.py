"""Tests for goCoax MoCA diagnostics."""

from __future__ import annotations

import pytest
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from custom_components.gocoax.const import DOMAIN
from custom_components.gocoax.diagnostics import async_get_config_entry_diagnostics
from custom_components.gocoax.pygocoax import AdapterStatus

from .conftest import MOCK_HOST, MOCK_MAC, MOCK_PASSWORD, MOCK_USERNAME


@pytest.fixture
def mock_entry_with_coordinator(
    hass: HomeAssistant, mock_adapter_status: AdapterStatus
):
    """Create mock config entry with coordinator."""
    from datetime import timedelta
    from unittest.mock import MagicMock

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

    # mock coordinator
    coordinator = MagicMock()
    coordinator.data = mock_adapter_status
    coordinator.last_update_success = True
    coordinator.update_interval = timedelta(seconds=30)

    entry.runtime_data = coordinator

    return entry


async def test_diagnostics_redacts_sensitive_data(
    hass: HomeAssistant,
    mock_entry_with_coordinator,
) -> None:
    """Test diagnostics redacts sensitive data."""
    diagnostics = await async_get_config_entry_diagnostics(
        hass, mock_entry_with_coordinator
    )

    # check password is redacted
    assert diagnostics["config_entry"]["data"][CONF_PASSWORD] == "**REDACTED**"

    # check mac address is redacted in adapter data
    if "adapter" in diagnostics:
        assert diagnostics["adapter"]["mac_address"] == "**REDACTED**"


async def test_diagnostics_includes_adapter_data(
    hass: HomeAssistant,
    mock_entry_with_coordinator,
) -> None:
    """Test diagnostics includes adapter data."""
    diagnostics = await async_get_config_entry_diagnostics(
        hass, mock_entry_with_coordinator
    )

    assert "adapter" in diagnostics
    assert diagnostics["adapter"]["moca_version"] == "2.5"
    assert diagnostics["adapter"]["link_status"] == "up"


async def test_diagnostics_includes_coordinator_info(
    hass: HomeAssistant,
    mock_entry_with_coordinator,
) -> None:
    """Test diagnostics includes coordinator info."""
    diagnostics = await async_get_config_entry_diagnostics(
        hass, mock_entry_with_coordinator
    )

    assert "coordinator" in diagnostics
    assert diagnostics["coordinator"]["last_update_success"] is True
    assert diagnostics["coordinator"]["host"] == MOCK_HOST
