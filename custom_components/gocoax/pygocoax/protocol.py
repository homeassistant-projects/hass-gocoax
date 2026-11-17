"""Pure monitoring decoders derived from MA2500D devStatus/phyRates UI logic."""

from __future__ import annotations

from .exceptions import GoCoaxParseError
from .models import AdapterStatus, EthernetPackets, NetworkPeer, PacketStats, PhyRate


def word(value: object) -> int:
    """Decode an unsigned protocol word; malformed values never become zero."""
    try:
        if isinstance(value, str) and len(value) <= 10:
            result = int(value, 16)
        elif type(value) is int:
            result = value
        else:
            raise ValueError
        if not 0 <= result <= 0xFFFFFFFF:
            raise ValueError
        return result
    except (ValueError, TypeError):
        raise GoCoaxParseError("Invalid protocol word") from None


def words(data: list, minimum: int = 1) -> list[int]:
    if not isinstance(data, list) or not minimum <= len(data) <= 2048:
        raise GoCoaxParseError("Unexpected response array length")
    return [word(value) for value in data]


def mac_address(data: list) -> str:
    high, low = words(data, 2)[:2]
    packed = high.to_bytes(4, "big") + (low >> 16).to_bytes(2, "big")
    if not any(packed) or packed == b"\xff" * 6:
        raise GoCoaxParseError("Adapter returned an invalid MAC address")
    return ":".join(f"{byte:02x}" for byte in packed)


def version(value: int) -> str:
    if value == 0:
        return "unknown"
    return f"{(value >> 4) & 0xF}.{value & 0xF}"


def local_nodes(data: list) -> tuple[int, int, list[int]]:
    local = words(data, 13)
    node, controller, mask = local[0], local[1] & 0xFF, local[12]
    if node >= 16 or controller >= 16 or mask > 0xFFFF:
        raise GoCoaxParseError("Invalid node identifiers or node mask")
    active = [n for n in range(16) if mask & (1 << n)]
    if local[5] and (node not in active or controller not in active):
        raise GoCoaxParseError("Active-node mask is inconsistent with link status")
    return node, controller, active


def packet_stats(data: list) -> EthernetPackets:
    values = words(data, 104)

    def count(index: int) -> int:
        return (values[index] << 32) | values[index + 1]

    return EthernetPackets(
        tx=PacketStats(count(12), count(30), count(48)),
        rx=PacketStats(count(66), count(84), count(102)),
    )


def phy_matrix(net: dict[int, list], fmr: dict[int, list], controller: int) -> dict:
    """Decode (NPER,VLPER) Mbps per (source,target), including inactive slots.

    FMR reserves packed space for all sixteen node IDs; sparse masks must not
    shift subsequent peers. Multicast/GCD diagonal entries are not peer rates.
    """
    if controller not in net:
        return {}
    node_words = {n: words(data, 5) for n, data in net.items()}
    nc_version = node_words[controller][4] & 0xFF
    matrix = {}
    for source, data in fmr.items():
        if source not in node_words:
            continue
        values = words(data, 34)
        source_version = node_words[source][4] & 0xFF
        if source_version not in (0x10, 0x11, 0x20, 0x25):
            continue
        index, aligned = 10, True
        for target in range(16):
            payload_version = source_version
            if target in node_words and nc_version < 0x20:
                payload_version = min(
                    source_version, nc_version, node_words[target][4] & 0xFF
                )
            if target not in node_words:
                index += (
                    (1 if aligned else 2)
                    if source_version >= 0x20
                    else (0 if aligned else 1)
                )
                aligned = not aligned
                continue
            if index + 1 >= len(values):
                raise GoCoaxParseError("Truncated PHY response")
            first, second = values[index : index + 2]
            if payload_version in (0x20, 0x25):
                if aligned:
                    gap_n, gap_v = (first >> 24) & 255, (first >> 16) & 255
                    bits_n, bits_v = first & 65535, (second >> 16) & 65535
                    index += 1
                else:
                    gap_n, gap_v = (first >> 8) & 255, first & 255
                    bits_n, bits_v = (second >> 16) & 65535, second & 65535
                    index += 2
            else:
                gap_v, bits_v = 0, 0
                gap_n = (first >> (27 if aligned else 11)) & 31
                bits_n = (first >> 16) & 2047 if aligned else first & 2047
                if not aligned:
                    index += 1
            aligned = not aligned
            vlper = 3900 * bits_v // ((512 + (gap_v + 10) * 2) * 46) if gap_v else 0
            if not gap_n:
                nper = 0
            elif not gap_v and payload_version == 0x20:
                nper = 1200 * bits_n // ((256 + gap_n * 2 + 10) * 26)
            elif payload_version >= 0x20:
                nper = 3900 * bits_n // ((512 + (gap_n + 10) * 2) * 46)
            else:
                nper = 1200 * bits_n // ((256 + gap_n * 2 + 10) * 26)
            if source != target:
                matrix[source, target] = (nper, vlper)
    return matrix


def decode_status(host: str, responses: dict, net: dict, fmr: dict) -> AdapterStatus:
    local = words(responses["local"], 13)
    node, controller, active = local_nodes(responses["local"])
    address = mac_address(responses["mac"])
    node_data = {n: words(data, 5) for n, data in net.items()}
    matrix = phy_matrix(net, fmr, controller)
    peers, rates = [], []
    for peer in sorted(active):
        if peer == node or peer not in node_data:
            continue
        peer_mac = mac_address(net[peer])
        tx, rx = matrix.get((node, peer)), matrix.get((peer, node))
        # MoCA 2.5 reports either NPER or VLPER depending on its boot configuration.
        tx_value = (tx[0] or tx[1]) if tx is not None else None
        rx_value = (rx[0] or rx[1]) if rx is not None else None
        peers.append(
            NetworkPeer(
                peer, peer_mac, version(node_data[peer][4] & 255), tx_value, rx_value
            )
        )
        rates.append(PhyRate(address, peer_mac, tx_value, rx_value))
    status = AdapterStatus(
        mac_address=address,
        ip_address=host,
        moca_version=version(local[11]),
        link_status=bool(local[5]),
        packets=packet_stats(responses["frames"]),
        node_id=node,
        nc_node_id=controller,
        network_controller=node == controller,
        network_peers=peers,
        phy_rates=rates,
    )
    if data := responses.get("moca25"):
        parsed = words(data, 4)
        status.channel_count = parsed[3] or None
    if data := responses.get("frequency"):
        value = words(data)[0]
        status.lof = value if 400 <= value <= 2000 else None
    band = words(responses["band"])[0] if responses.get("band") else None
    privacy = words(responses["privacy"])[0] if responses.get("privacy") else None
    enhanced = (
        words(responses["enhanced_privacy"])[0]
        if responses.get("enhanced_privacy")
        else None
    )
    if band is not None and band and not band & ~255:
        labels = ("Extended-D", "D-Low", "D-High", "E", "F-SAT", "F-CBL", "H", "Custom")
        status.frequency_band = ", ".join(
            label for bit, label in enumerate(labels) if band & (1 << bit)
        )
        protected = (privacy & band) if privacy is not None else None
        if protected == band or (enhanced is not None and enhanced & 4):
            status.encryption_enabled = True
        elif protected == 0 and enhanced is not None:
            status.encryption_enabled = False
        # Partial band protection or missing flags are deliberately unknown.
    return status
