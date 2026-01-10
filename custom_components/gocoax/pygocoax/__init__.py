"""pygocoax - Async Python client library for goCoax MoCA adapters."""

from .client import GoCoaxClient
from .exceptions import (
    GoCoaxAuthError,
    GoCoaxConnectionError,
    GoCoaxError,
    GoCoaxParseError,
    GoCoaxTimeoutError,
)
from .models import (
    AdapterStatus,
    EthernetPackets,
    NetworkPeer,
    PacketStats,
    PhyRate,
    SignalQuality,
)

__all__ = [
    "GoCoaxClient",
    "AdapterStatus",
    "EthernetPackets",
    "NetworkPeer",
    "PacketStats",
    "PhyRate",
    "SignalQuality",
    "GoCoaxError",
    "GoCoaxAuthError",
    "GoCoaxConnectionError",
    "GoCoaxParseError",
    "GoCoaxTimeoutError",
]
