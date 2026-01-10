"""Sensor platform for goCoax MoCA integration."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, UnitOfDataRate
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import GoCoaxConfigEntry
from .const import (
    ATTR_RX_BAD,
    ATTR_RX_DROPPED,
    ATTR_RX_OK,
    ATTR_TX_BAD,
    ATTR_TX_DROPPED,
    ATTR_TX_OK,
    DOMAIN,
    MANUFACTURER_GOCOAX,
)
from .coordinator import GoCoaxCoordinator
from .pygocoax import AdapterStatus

LOG = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class GoCoaxSensorEntityDescription(SensorEntityDescription):
    """Describes a goCoax sensor entity."""

    value_fn: Callable[[AdapterStatus], Any]
    extra_attrs_fn: Callable[[AdapterStatus], dict[str, Any]] | None = None


SENSOR_DESCRIPTIONS: tuple[GoCoaxSensorEntityDescription, ...] = (
    GoCoaxSensorEntityDescription(
        key="moca_version",
        translation_key="moca_version",
        icon="mdi:chip",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.moca_version,
    ),
    GoCoaxSensorEntityDescription(
        key="mac_address",
        translation_key="mac_address",
        icon="mdi:ethernet",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.mac_address,
    ),
    GoCoaxSensorEntityDescription(
        key="node_id",
        translation_key="node_id",
        icon="mdi:identifier",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.node_id,
    ),
    GoCoaxSensorEntityDescription(
        key="tx_packets",
        translation_key="tx_packets",
        icon="mdi:upload-network",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data.packets.tx.ok,
        extra_attrs_fn=lambda data: {
            ATTR_TX_OK: data.packets.tx.ok,
            ATTR_TX_BAD: data.packets.tx.bad,
            ATTR_TX_DROPPED: data.packets.tx.dropped,
        },
    ),
    GoCoaxSensorEntityDescription(
        key="rx_packets",
        translation_key="rx_packets",
        icon="mdi:download-network",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data.packets.rx.ok,
        extra_attrs_fn=lambda data: {
            ATTR_RX_OK: data.packets.rx.ok,
            ATTR_RX_BAD: data.packets.rx.bad,
            ATTR_RX_DROPPED: data.packets.rx.dropped,
        },
    ),
    GoCoaxSensorEntityDescription(
        key="peer_count",
        translation_key="peer_count",
        icon="mdi:lan",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.peer_count,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: GoCoaxConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up goCoax sensor entities."""
    coordinator = entry.runtime_data

    entities: list[GoCoaxSensor] = []

    # add standard sensors
    for description in SENSOR_DESCRIPTIONS:
        entities.append(GoCoaxSensor(coordinator, description))

    # add PHY rate sensors for each peer
    if coordinator.data and coordinator.data.phy_rates:
        for idx, phy_rate in enumerate(coordinator.data.phy_rates):
            # tx rate sensor
            entities.append(
                GoCoaxPhyRateSensor(
                    coordinator,
                    GoCoaxSensorEntityDescription(
                        key=f"phy_tx_rate_{idx}",
                        translation_key="phy_tx_rate",
                        icon="mdi:speedometer",
                        device_class=SensorDeviceClass.DATA_RATE,
                        native_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND,
                        state_class=SensorStateClass.MEASUREMENT,
                        value_fn=lambda data, i=idx: (
                            data.phy_rates[i].tx_rate
                            if i < len(data.phy_rates)
                            else None
                        ),
                    ),
                    phy_rate.target_mac,
                    "tx",
                )
            )
            # rx rate sensor
            entities.append(
                GoCoaxPhyRateSensor(
                    coordinator,
                    GoCoaxSensorEntityDescription(
                        key=f"phy_rx_rate_{idx}",
                        translation_key="phy_rx_rate",
                        icon="mdi:speedometer",
                        device_class=SensorDeviceClass.DATA_RATE,
                        native_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND,
                        state_class=SensorStateClass.MEASUREMENT,
                        value_fn=lambda data, i=idx: (
                            data.phy_rates[i].rx_rate
                            if i < len(data.phy_rates)
                            else None
                        ),
                    ),
                    phy_rate.target_mac,
                    "rx",
                )
            )

    async_add_entities(entities)


class GoCoaxSensor(CoordinatorEntity[GoCoaxCoordinator], SensorEntity):
    """Sensor entity for goCoax MoCA adapter."""

    entity_description: GoCoaxSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: GoCoaxCoordinator,
        description: GoCoaxSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.mac_address}_{description.key}"
        self._attr_device_info = self._build_device_info()

    def _build_device_info(self) -> DeviceInfo:
        """Build device info for this sensor."""
        data = self.coordinator.data
        return DeviceInfo(
            identifiers={
                (DOMAIN, self.coordinator.mac_address or self.coordinator.host)
            },
            connections={(CONNECTION_NETWORK_MAC, data.mac_address)} if data else set(),
            name=f"goCoax {self.coordinator.host}",
            manufacturer=MANUFACTURER_GOCOAX,
            model=data.model if data else None,
            sw_version=data.firmware_version if data else None,
            configuration_url=f"http://{self.coordinator.host}",
        )

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        if not self.coordinator.data:
            return None
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra state attributes."""
        if not self.coordinator.data or not self.entity_description.extra_attrs_fn:
            return None
        return self.entity_description.extra_attrs_fn(self.coordinator.data)


class GoCoaxPhyRateSensor(GoCoaxSensor):
    """PHY rate sensor for peer connections."""

    def __init__(
        self,
        coordinator: GoCoaxCoordinator,
        description: GoCoaxSensorEntityDescription,
        target_mac: str,
        direction: str,
    ) -> None:
        """Initialize the PHY rate sensor."""
        super().__init__(coordinator, description)
        self._target_mac = target_mac
        self._direction = direction
        # update unique_id to include target mac
        short_mac = target_mac.replace(":", "")[-6:]
        self._attr_unique_id = f"{coordinator.mac_address}_phy_{direction}_{short_mac}"

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        short_mac = self._target_mac.replace(":", "")[-6:]
        direction_label = "TX" if self._direction == "tx" else "RX"
        return f"PHY {direction_label} Rate ({short_mac})"
