"""Pytest fixtures for goCoax MoCA integration tests."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME

from custom_components.gocoax.pygocoax import (
    AdapterStatus,
    EthernetPackets,
    PacketStats,
)

MOCK_HOST = "192.168.1.100"
MOCK_USERNAME = "admin"
MOCK_PASSWORD = "gocoax"
MOCK_MAC = "a4:81:7a:49:e3:dd"


@pytest.fixture
def mock_config_entry_data() -> dict:
    """Return mock config entry data."""
    return {
        CONF_HOST: MOCK_HOST,
        CONF_USERNAME: MOCK_USERNAME,
        CONF_PASSWORD: MOCK_PASSWORD,
    }


@pytest.fixture
def mock_adapter_status() -> AdapterStatus:
    """Return mock adapter status."""
    return AdapterStatus(
        mac_address=MOCK_MAC,
        ip_address=MOCK_HOST,
        moca_version="2.5",
        link_status=True,
        adapter_name=None,
        firmware_version="2.0.11",
        model="MA2500D",
        packets=EthernetPackets(
            tx=PacketStats(ok=426959, bad=0, dropped=0),
            rx=PacketStats(ok=1361613, bad=0, dropped=0),
        ),
        network_peers=[],
        phy_rates=[],
        node_id=0,
        network_controller=True,
    )


@pytest.fixture
def mock_gocoax_client(mock_adapter_status: AdapterStatus) -> Generator[MagicMock]:
    """Mock GoCoaxClient."""
    with patch(
        "custom_components.gocoax.config_flow.GoCoaxClient", autospec=True
    ) as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.get_mac_address = AsyncMock(return_value=MOCK_MAC)
        mock_client.get_status = AsyncMock(return_value=mock_adapter_status)
        mock_client.test_connection = AsyncMock(return_value=True)
        mock_client.close = AsyncMock()
        yield mock_client


@pytest.fixture
def mock_coordinator_client(
    mock_adapter_status: AdapterStatus,
) -> Generator[MagicMock]:
    """Mock GoCoaxClient for coordinator tests."""
    with patch(
        "custom_components.gocoax.coordinator.GoCoaxClient", autospec=True
    ) as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.get_mac_address = AsyncMock(return_value=MOCK_MAC)
        mock_client.get_status = AsyncMock(return_value=mock_adapter_status)
        mock_client.close = AsyncMock()
        yield mock_client
