"""Test the actual entities, rather than a duplicate of the ID-generation code."""

from unittest.mock import MagicMock

import pytest

from custom_components.gocoax.binary_sensor import (
    BINARY_SENSOR_DESCRIPTIONS,
    GoCoaxBinarySensor,
)
from custom_components.gocoax.sensor import (
    SENSOR_DESCRIPTIONS,
    GoCoaxPhyRateSensor,
    GoCoaxSensor,
)

from .conftest import MOCK_HOST, MOCK_MAC


@pytest.fixture
def coordinator(mock_adapter_status):
    result = MagicMock()
    result.data = mock_adapter_status
    result.mac_address = MOCK_MAC
    result.host = MOCK_HOST
    result.last_update_success = True
    return result


def test_standard_entities_preserve_upstream_ids(coordinator):
    for description in SENSOR_DESCRIPTIONS:
        entity = GoCoaxSensor(coordinator, description)
        assert entity.unique_id == f"{MOCK_MAC}_{description.key}"
    for description in BINARY_SENSOR_DESCRIPTIONS:
        entity = GoCoaxBinarySensor(coordinator, description)
        assert entity.unique_id == f"{MOCK_MAC}_{description.key}"


def test_phy_entity_preserves_upstream_id(coordinator):
    entity = GoCoaxPhyRateSensor(
        coordinator, SENSOR_DESCRIPTIONS[0], "02:00:00:11:22:33", "tx"
    )
    assert entity.unique_id == f"{MOCK_MAC}_phy_tx_112233"
