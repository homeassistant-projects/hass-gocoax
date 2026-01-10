"""Data models for goCoax MoCA adapter responses."""

from dataclasses import dataclass, field


@dataclass
class PacketStats:
    """Packet statistics for tx/rx."""

    ok: int = 0
    bad: int = 0
    dropped: int = 0


@dataclass
class EthernetPackets:
    """Ethernet packet statistics."""

    tx: PacketStats = field(default_factory=PacketStats)
    rx: PacketStats = field(default_factory=PacketStats)


@dataclass
class NetworkPeer:
    """Information about a peer on the MoCA network."""

    node_id: int
    mac_address: str
    moca_version: str
    tx_phy_rate: int = 0  # Mbps
    rx_phy_rate: int = 0  # Mbps


@dataclass
class PhyRate:
    """PHY rate between two adapters."""

    source_mac: str
    target_mac: str
    tx_rate: int  # Mbps
    rx_rate: int  # Mbps


@dataclass
class SignalQuality:
    """Signal quality metrics for MoCA connection."""

    snr: float | None = None  # Signal-to-noise ratio in dB
    tx_power: float | None = None  # TX power in dBm
    rx_power: float | None = None  # RX power in dBm
    bit_loading: int | None = None  # bits per symbol


@dataclass
class AdapterStatus:
    """Complete status of a goCoax MoCA adapter."""

    mac_address: str
    ip_address: str
    moca_version: str
    link_status: bool  # True = up, False = down
    adapter_name: str | None = None
    firmware_version: str | None = None
    model: str | None = None
    packets: EthernetPackets = field(default_factory=EthernetPackets)
    network_peers: list[NetworkPeer] = field(default_factory=list)
    phy_rates: list[PhyRate] = field(default_factory=list)
    node_id: int = 0
    network_controller: bool = False  # True if this node is the NC
    # new fields for enhanced monitoring
    frequency_band: str | None = None  # e.g., "D-Low", "D-High", "Extended-D"
    lof: int | None = None  # Lowest Operating Frequency in MHz
    encryption_enabled: bool | None = None  # MoCA privacy/encryption status
    signal_quality: SignalQuality = field(default_factory=SignalQuality)
    channel_count: int | None = None  # number of bonded channels
    nc_node_id: int | None = None  # network controller node ID

    @property
    def peer_count(self) -> int:
        """Return count of network peers."""
        return len(self.network_peers)

    def to_dict(self) -> dict:
        """Convert to dictionary for diagnostics."""
        return {
            "mac_address": self.mac_address,
            "ip_address": self.ip_address,
            "moca_version": self.moca_version,
            "link_status": "up" if self.link_status else "down",
            "adapter_name": self.adapter_name,
            "firmware_version": self.firmware_version,
            "model": self.model,
            "node_id": self.node_id,
            "nc_node_id": self.nc_node_id,
            "network_controller": self.network_controller,
            "frequency_band": self.frequency_band,
            "lof": self.lof,
            "channel_count": self.channel_count,
            "encryption_enabled": self.encryption_enabled,
            "signal_quality": {
                "snr": self.signal_quality.snr,
                "tx_power": self.signal_quality.tx_power,
                "rx_power": self.signal_quality.rx_power,
                "bit_loading": self.signal_quality.bit_loading,
            },
            "packets": {
                "tx": {
                    "ok": self.packets.tx.ok,
                    "bad": self.packets.tx.bad,
                    "dropped": self.packets.tx.dropped,
                },
                "rx": {
                    "ok": self.packets.rx.ok,
                    "bad": self.packets.rx.bad,
                    "dropped": self.packets.rx.dropped,
                },
            },
            "network_peers": [
                {
                    "node_id": peer.node_id,
                    "mac_address": peer.mac_address,
                    "moca_version": peer.moca_version,
                    "tx_phy_rate": peer.tx_phy_rate,
                    "rx_phy_rate": peer.rx_phy_rate,
                }
                for peer in self.network_peers
            ],
            "phy_rates": [
                {
                    "source_mac": rate.source_mac,
                    "target_mac": rate.target_mac,
                    "tx_rate": rate.tx_rate,
                    "rx_rate": rate.rx_rate,
                }
                for rate in self.phy_rates
            ],
        }
