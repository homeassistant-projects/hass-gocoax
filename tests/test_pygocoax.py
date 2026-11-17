"""Tests for pygocoax client library."""

from __future__ import annotations

import pytest

from custom_components.gocoax.pygocoax import (
    AdapterStatus,
    EthernetPackets,
    PacketStats,
)
from custom_components.gocoax.pygocoax.exceptions import GoCoaxParseError
from custom_components.gocoax.pygocoax.protocol import (
    mac_address,
    packet_stats,
    version,
    word,
)


class TestGoCoaxClient:
    """Tests for GoCoaxClient."""

    def test_hex_to_mac(self) -> None:
        """Test hex to MAC address conversion."""
        # from decoded data: 0xa4817a49, 0xe3dd0000
        mac = mac_address([0xA4817A49, 0xE3DD0000])
        assert mac == "a4:81:7a:49:e3:dd"

    def test_parse_hex_value(self) -> None:
        """Test hex string parsing."""
        assert word("0x000683cf") == 426959
        assert word("0x0014c6cd") == 1361613
        with pytest.raises(GoCoaxParseError):
            word("invalid")
        with pytest.raises(GoCoaxParseError):
            word(None)

    def test_parse_64bit_value(self) -> None:
        """Test 64-bit value parsing from hex strings."""
        data = ["0x00000000"] * 108
        data[13] = "0x000683cf"
        result = packet_stats(data).tx.ok
        assert result == 426959

    def test_parse_moca_version(self) -> None:
        """Test MoCA version parsing."""
        assert version(0x25) == "2.5"
        assert version(0x20) == "2.0"
        assert version(0) == "unknown"


class TestAdapterStatus:
    """Tests for AdapterStatus model."""

    def test_to_dict(self) -> None:
        """Test AdapterStatus to_dict conversion."""
        status = AdapterStatus(
            mac_address="a4:81:7a:49:e3:dd",
            ip_address="192.168.1.1",
            moca_version="2.5",
            link_status=True,
            packets=EthernetPackets(
                tx=PacketStats(ok=1000, bad=0, dropped=0),
                rx=PacketStats(ok=2000, bad=1, dropped=2),
            ),
        )

        result = status.to_dict()

        assert result["mac_address"] == "a4:81:7a:49:e3:dd"
        assert result["link_status"] == "up"
        assert result["packets"]["tx"]["ok"] == 1000
        assert result["packets"]["rx"]["bad"] == 1

    def test_peer_count(self) -> None:
        """Test peer count property."""
        status = AdapterStatus(
            mac_address="a4:81:7a:49:e3:dd",
            ip_address="192.168.1.1",
            moca_version="2.5",
            link_status=True,
            network_peers=[],
        )
        assert status.peer_count == 0
