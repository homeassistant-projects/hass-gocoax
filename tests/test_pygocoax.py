"""Tests for pygocoax client library."""

from __future__ import annotations

from custom_components.gocoax.pygocoax import (
    AdapterStatus,
    EthernetPackets,
    GoCoaxClient,
    PacketStats,
)


class TestGoCoaxClient:
    """Tests for GoCoaxClient."""

    def test_hex_to_mac(self) -> None:
        """Test hex to MAC address conversion."""
        client = GoCoaxClient("192.168.1.1")
        # from decoded data: 0xa4817a49, 0xe3dd0000
        mac = client._hex_to_mac(0xA4817A49, 0xE3DD0000)
        assert mac == "a4:81:7a:49:e3:dd"

    def test_parse_hex_value(self) -> None:
        """Test hex string parsing."""
        client = GoCoaxClient("192.168.1.1")
        assert client._parse_hex_value("0x000683cf") == 426959
        assert client._parse_hex_value("0x0014c6cd") == 1361613
        assert client._parse_hex_value("invalid") == 0
        assert client._parse_hex_value(None) == 0

    def test_parse_64bit_value(self) -> None:
        """Test 64-bit value parsing from hex strings."""
        client = GoCoaxClient("192.168.1.1")
        data = ["0x00000000", "0x000683cf"]
        result = client._parse_64bit_value(data, 0)
        assert result == 426959

    def test_parse_moca_version(self) -> None:
        """Test MoCA version parsing."""
        client = GoCoaxClient("192.168.1.1")
        assert client._parse_moca_version(0x25) == "2.5"
        assert client._parse_moca_version(0x20) == "2.0"
        assert client._parse_moca_version(0) == "unknown"

    def test_parse_phy_rates_html(self) -> None:
        """Test PHY rates HTML parsing."""
        client = GoCoaxClient("192.168.1.1")
        html = """
        <table>
            <tr><th>MAC</th><th>TX</th><th>RX</th></tr>
            <tr><td>a4:81:7a:49:e3:dd</td><td>2500 Mbps</td><td>2400 Mbps</td></tr>
        </table>
        """
        rates = client._parse_phy_rates_html(html)
        assert len(rates) == 1
        assert rates[0].target_mac == "a4:81:7a:49:e3:dd"
        assert rates[0].tx_rate == 2500
        assert rates[0].rx_rate == 2400

    def test_parse_phy_rates_html_no_table(self) -> None:
        """Test PHY rates parsing with no table."""
        client = GoCoaxClient("192.168.1.1")
        rates = client._parse_phy_rates_html("<html></html>")
        assert rates == []


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
