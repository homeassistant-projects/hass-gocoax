"""Peer entity association and discovery across topology updates."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from custom_components.gocoax.pygocoax import PhyRate
from custom_components.gocoax.sensor import GoCoaxPhyRateSensor, async_setup_entry

from .conftest import MOCK_HOST, MOCK_MAC


async def test_peer_reordering_discovery_and_departure(hass, mock_adapter_status):
    first = PhyRate(MOCK_MAC, "02:00:00:00:00:02", 1100, 1200)
    second = PhyRate(MOCK_MAC, "02:00:00:00:00:03", 2100, 2200)
    mock_adapter_status.phy_rates = [first]
    coordinator = MagicMock()
    coordinator.data = mock_adapter_status
    coordinator.mac_address = MOCK_MAC
    coordinator.host = MOCK_HOST
    coordinator.last_update_success = True
    callbacks, added, cleanup = [], [], []

    def listen(callback):
        callbacks.append(callback)
        return lambda: None

    coordinator.async_add_listener.side_effect = listen
    entry = SimpleNamespace(runtime_data=coordinator, async_on_unload=cleanup.append)
    await async_setup_entry(hass, entry, added.extend)
    tx = next(
        entity
        for entity in added
        if isinstance(entity, GoCoaxPhyRateSensor) and entity._direction == "tx"
    )
    assert tx.native_value == 1100 and tx.available
    mock_adapter_status.phy_rates = [second, first]
    callbacks[0]()
    assert tx.native_value == 1100  # Association is by MAC, not list index.
    assert (
        len([entity for entity in added if isinstance(entity, GoCoaxPhyRateSensor)])
        == 4
    )
    callbacks[0]()
    assert (
        len([entity for entity in added if isinstance(entity, GoCoaxPhyRateSensor)])
        == 4
    )
    mock_adapter_status.phy_rates = [second]
    assert tx.native_value is None and not tx.available
    assert len(cleanup) == 1
