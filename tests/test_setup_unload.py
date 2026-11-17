"""Load/unload the actual integration inside an isolated Home Assistant core."""

from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.gocoax.const import DOMAIN

from .conftest import MOCK_MAC


async def test_setup_registers_entities_and_unload_closes_sessions(
    hass, mock_config_entry_data, mock_coordinator_client, mocked_http_sessions
):
    entry = MockConfigEntry(
        domain=DOMAIN, data=mock_config_entry_data, unique_id=MOCK_MAC
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id(
        "sensor", DOMAIN, f"{MOCK_MAC}_moca_version"
    )
    assert entity_id is not None and hass.states.get(entity_id).state == "2.5"
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    mock_coordinator_client.close.assert_awaited()
    assert mocked_http_sessions
    for session in mocked_http_sessions:
        session.close.assert_awaited()
