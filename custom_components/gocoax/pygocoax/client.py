"""Async client for goCoax MoCA adapters."""

from __future__ import annotations

import asyncio
import logging
import re
from typing import TYPE_CHECKING

import aiohttp
from aiohttp import BasicAuth

from .exceptions import (
    GoCoaxAuthError,
    GoCoaxConnectionError,
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

if TYPE_CHECKING:
    from aiohttp import ClientSession

LOG = logging.getLogger(__name__)

# API endpoints - JSON data
ENDPOINT_MAC = "/ms/1/0x103/GET"
ENDPOINT_LOCAL_INFO = "/ms/0/0x15"
ENDPOINT_STATUS = "/ms/0/0x16"
ENDPOINT_FRAME_INFO = "/ms/0/0x14"
ENDPOINT_FMR_INFO = "/ms/0/0x1D"
ENDPOINT_NODE_INFO = "/ms/0/0x19"
ENDPOINT_PRIVACY = "/ms/0/0x17"  # MoCA privacy/encryption settings
ENDPOINT_MPS = "/ms/0/0x18"  # MoCA Protected Setup
ENDPOINT_CONFIG = "/ms/0/0x1A"  # configuration parameters

# HTML page endpoints
ENDPOINT_PHY_RATES = "/phyRates.html"
ENDPOINT_SECURITY_HTML = "/security.html"
ENDPOINT_STATUS_HTML = "/index.html"

# data indices from decoded format
LOCAL_INFO_LINK_STATUS_IDX = 5
LOCAL_INFO_MOCA_VER_IDX = 11
LOCAL_INFO_NODE_ID_IDX = 3
LOCAL_INFO_NC_NODE_IDX = 4

FRAME_TX_GOOD_IDX = 12
FRAME_TX_BAD_IDX = 30
FRAME_TX_DROP_IDX = 48
FRAME_RX_GOOD_IDX = 66
FRAME_RX_BAD_IDX = 84
FRAME_RX_DROP_IDX = 102

DEFAULT_TIMEOUT = 15


class GoCoaxClient:
    """Async client for communicating with goCoax MoCA adapters."""

    def __init__(
        self,
        host: str,
        username: str = "admin",
        password: str = "gocoax",
        session: ClientSession | None = None,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialize the goCoax client."""
        self._host = host
        self._username = username
        self._password = password
        self._session = session
        self._owns_session = session is None
        self._timeout = timeout
        self._base_url = f"http://{host}"

    async def _get_session(self) -> ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
            self._owns_session = True
        return self._session

    async def close(self) -> None:
        """Close the client session if we own it."""
        if self._owns_session and self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def _request(self, endpoint: str, method: str = "GET") -> dict | str:
        """Make an authenticated request to the adapter."""
        session = await self._get_session()
        url = f"{self._base_url}{endpoint}"
        auth = BasicAuth(self._username, self._password)

        try:
            async with asyncio.timeout(self._timeout):
                if method == "POST":
                    # goCoax uses funky POST with form data
                    headers = {"content-type": "application/x-www-form-urlencoded"}
                    async with session.post(
                        url, data='{"data":[2]}', auth=auth, headers=headers
                    ) as resp:
                        return await self._handle_response(resp, url)
                else:
                    async with session.get(url, auth=auth) as resp:
                        return await self._handle_response(resp, url)

        except TimeoutError as err:
            raise GoCoaxTimeoutError(
                f"Timeout connecting to goCoax adapter at {self._host}"
            ) from err
        except aiohttp.ClientError as err:
            raise GoCoaxConnectionError(
                f"Error connecting to goCoax adapter at {self._host}: {err}"
            ) from err

    async def _handle_response(
        self, resp: aiohttp.ClientResponse, url: str
    ) -> dict | str:
        """Handle HTTP response."""
        if resp.status == 401:
            raise GoCoaxAuthError(
                f"Authentication failed for goCoax adapter at {self._host}"
            )
        if resp.status != 200:
            raise GoCoaxConnectionError(
                f"HTTP {resp.status} from goCoax adapter: {url}"
            )

        content_type = resp.content_type or ""
        if "json" in content_type or url.endswith("/GET"):
            return await resp.json()
        return await resp.text()

    def _parse_hex_value(self, hex_str: str) -> int:
        """Parse hex string to integer."""
        try:
            return int(hex_str, 16)
        except (ValueError, TypeError):
            return 0

    def _parse_64bit_value(self, data: list[str], high_idx: int) -> int:
        """Parse 64-bit value from two consecutive hex strings."""
        if high_idx + 1 >= len(data):
            return 0
        high = self._parse_hex_value(data[high_idx]) & 0xFFFFFFFF
        low = self._parse_hex_value(data[high_idx + 1])
        return (high * 4294967296) + low

    def _hex_to_mac(self, hi: int, lo: int) -> str:
        """Convert two integers to MAC address string."""
        # extract bytes: hi contains first 4 bytes, lo contains last 2
        b1 = (hi >> 24) & 0xFF
        b2 = (hi >> 16) & 0xFF
        b3 = (hi >> 8) & 0xFF
        b4 = hi & 0xFF
        b5 = (lo >> 24) & 0xFF
        b6 = (lo >> 16) & 0xFF
        return f"{b1:02x}:{b2:02x}:{b3:02x}:{b4:02x}:{b5:02x}:{b6:02x}"

    def _parse_moca_version(self, ver_int: int) -> str:
        """Parse MoCA version from integer value."""
        # version is encoded as major * 16 + minor
        if ver_int == 0x20:
            return "2.0"
        if ver_int == 0x25:
            return "2.5"
        if ver_int >= 0x20:
            major = ver_int >> 4
            minor = ver_int & 0x0F
            return f"{major}.{minor}"
        return "unknown"

    async def get_mac_address(self) -> str:
        """Get the MAC address of the adapter."""
        try:
            resp = await self._request(ENDPOINT_MAC)
            if isinstance(resp, dict) and "data" in resp:
                data = resp["data"]
                if len(data) >= 2:
                    hi = self._parse_hex_value(data[0])
                    lo = self._parse_hex_value(data[1])
                    return self._hex_to_mac(hi, lo)
        except GoCoaxParseError:
            LOG.debug("Failed to parse MAC address")
        return ""

    async def get_local_info(self) -> dict:
        """Get local adapter info (link status, MoCA version, etc.)."""
        resp = await self._request(ENDPOINT_LOCAL_INFO)
        if isinstance(resp, dict) and "data" in resp:
            data = resp["data"]
            return {
                "link_status": self._parse_hex_value(data[LOCAL_INFO_LINK_STATUS_IDX])
                if len(data) > LOCAL_INFO_LINK_STATUS_IDX
                else 0,
                "moca_version": self._parse_hex_value(data[LOCAL_INFO_MOCA_VER_IDX])
                if len(data) > LOCAL_INFO_MOCA_VER_IDX
                else 0,
                "node_id": self._parse_hex_value(data[LOCAL_INFO_NODE_ID_IDX])
                if len(data) > LOCAL_INFO_NODE_ID_IDX
                else 0,
                "nc_node_id": self._parse_hex_value(data[LOCAL_INFO_NC_NODE_IDX])
                if len(data) > LOCAL_INFO_NC_NODE_IDX
                else 0,
                "raw_data": data,
            }
        raise GoCoaxParseError("Invalid local info response")

    async def get_frame_info(self) -> EthernetPackets:
        """Get ethernet tx/rx packet statistics."""
        resp = await self._request(ENDPOINT_FRAME_INFO)
        if isinstance(resp, dict) and "data" in resp:
            data = resp["data"]
            tx_good = self._parse_64bit_value(data, FRAME_TX_GOOD_IDX)
            tx_bad = self._parse_64bit_value(data, FRAME_TX_BAD_IDX)
            tx_drop = self._parse_64bit_value(data, FRAME_TX_DROP_IDX)
            rx_good = self._parse_64bit_value(data, FRAME_RX_GOOD_IDX)
            rx_bad = self._parse_64bit_value(data, FRAME_RX_BAD_IDX)
            rx_drop = self._parse_64bit_value(data, FRAME_RX_DROP_IDX)

            return EthernetPackets(
                tx=PacketStats(ok=tx_good, bad=tx_bad, dropped=tx_drop),
                rx=PacketStats(ok=rx_good, bad=rx_bad, dropped=rx_drop),
            )
        raise GoCoaxParseError("Invalid frame info response")

    async def get_node_info(self, local_node_id: int = -1) -> list[NetworkPeer]:
        """Get information about other nodes on the MoCA network.

        The node info endpoint returns data for all nodes. Each node entry
        contains: node_id, mac_address (2 hex values), moca_version, etc.
        Format varies by firmware but typically uses 16 values per node.
        """
        peers: list[NetworkPeer] = []
        try:
            resp = await self._request(ENDPOINT_NODE_INFO)
            if isinstance(resp, dict) and "data" in resp:
                data = resp["data"]
                LOG.debug("Node info response (raw): %s", data)

                # typical format: 16 values per node
                # [0]=node_id, [1]=mac_hi, [2]=mac_lo, [3]=moca_ver, ...
                node_size = 16
                if len(data) >= node_size:
                    num_nodes = len(data) // node_size
                    for i in range(num_nodes):
                        offset = i * node_size
                        node_id = self._parse_hex_value(data[offset])

                        # skip local node and empty entries
                        if node_id == local_node_id or node_id == 0:
                            continue

                        mac_hi = self._parse_hex_value(data[offset + 1])
                        mac_lo = self._parse_hex_value(data[offset + 2])
                        mac_addr = self._hex_to_mac(mac_hi, mac_lo)

                        # skip if MAC is all zeros (empty slot)
                        if mac_addr == "00:00:00:00:00:00":
                            continue

                        moca_ver_int = self._parse_hex_value(data[offset + 3])
                        moca_ver = self._parse_moca_version(moca_ver_int)

                        peers.append(
                            NetworkPeer(
                                node_id=node_id,
                                mac_address=mac_addr,
                                moca_version=moca_ver,
                            )
                        )
                        LOG.debug(
                            "Parsed peer: node_id=%d, mac=%s, version=%s",
                            node_id,
                            mac_addr,
                            moca_ver,
                        )

        except (GoCoaxConnectionError, GoCoaxParseError) as err:
            LOG.debug("Failed to get node info: %s", err)
        return peers

    async def get_phy_rates(self) -> list[PhyRate]:
        """Parse PHY rates from the phyRates.html page."""
        rates: list[PhyRate] = []
        try:
            html = await self._request(ENDPOINT_PHY_RATES)
            if isinstance(html, str):
                rates = self._parse_phy_rates_html(html)
        except (GoCoaxConnectionError, GoCoaxParseError) as err:
            LOG.debug(f"Failed to get PHY rates: {err}")
        return rates

    def _parse_phy_rates_html(self, html: str) -> list[PhyRate]:
        """Parse PHY rates table from HTML."""
        rates: list[PhyRate] = []
        # look for table with PHY rates
        # format varies by firmware, typical pattern:
        # MAC addr | TX rate | RX rate
        table_match = re.search(
            r"<table[^>]*>(.*?)</table>", html, re.IGNORECASE | re.DOTALL
        )
        if not table_match:
            return rates

        table_html = table_match.group(1)
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", table_html, re.IGNORECASE | re.DOTALL)

        for row in rows[1:]:  # skip header row
            cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.IGNORECASE | re.DOTALL)
            if len(cells) >= 3:
                mac_match = re.search(r"([0-9a-fA-F:]{17})", cells[0].strip())
                if mac_match:
                    mac = mac_match.group(1).lower()
                    try:
                        tx_rate = int(re.sub(r"[^\d]", "", cells[1]) or "0")
                        rx_rate = int(re.sub(r"[^\d]", "", cells[2]) or "0")
                        rates.append(
                            PhyRate(
                                source_mac="",  # filled by caller
                                target_mac=mac,
                                tx_rate=tx_rate,
                                rx_rate=rx_rate,
                            )
                        )
                    except ValueError:
                        continue
        return rates

    async def get_privacy_info(self) -> dict:
        """Get MoCA privacy/encryption settings.

        Returns dict with encryption_enabled and potentially password hash.
        """
        result: dict = {"encryption_enabled": None}
        try:
            resp = await self._request(ENDPOINT_PRIVACY)
            if isinstance(resp, dict) and "data" in resp:
                data = resp["data"]
                LOG.debug("Privacy info response (raw): %s", data)
                # typical format: [0]=privacy_enabled (0=off, 1=on)
                if len(data) >= 1:
                    privacy_val = self._parse_hex_value(data[0])
                    result["encryption_enabled"] = privacy_val == 1
        except (GoCoaxConnectionError, GoCoaxParseError) as err:
            LOG.debug("Failed to get privacy info: %s", err)
        return result

    async def get_fmr_info(self) -> dict:
        """Get FMR (Frequency/Modulation/Rate) information.

        May contain signal quality data like SNR, power levels.
        """
        result: dict = {
            "snr": None,
            "tx_power": None,
            "rx_power": None,
            "bit_loading": None,
        }
        try:
            resp = await self._request(ENDPOINT_FMR_INFO)
            if isinstance(resp, dict) and "data" in resp:
                data = resp["data"]
                LOG.debug("FMR info response (raw): %s", data)
                # format varies; log for analysis and attempt parsing
                # commonly: SNR, power levels, modulation info
                # will need real device data to finalize parsing
        except (GoCoaxConnectionError, GoCoaxParseError) as err:
            LOG.debug("Failed to get FMR info: %s", err)
        return result

    async def get_config_info(self) -> dict:
        """Get configuration parameters including frequency band.

        Returns LOF (lowest operating frequency), band settings, etc.
        """
        result: dict = {
            "frequency_band": None,
            "lof": None,
            "channel_count": None,
        }
        try:
            resp = await self._request(ENDPOINT_CONFIG)
            if isinstance(resp, dict) and "data" in resp:
                data = resp["data"]
                LOG.debug("Config info response (raw): %s", data)
                # attempt to parse LOF and band configuration
                # LOF is typically in MHz (e.g., 1125, 1400)
                if len(data) >= 1:
                    lof = self._parse_hex_value(data[0])
                    if 1000 <= lof <= 1700:  # sanity check for MHz range
                        result["lof"] = lof
                        result["frequency_band"] = self._lof_to_band(lof)
        except (GoCoaxConnectionError, GoCoaxParseError) as err:
            LOG.debug("Failed to get config info: %s", err)
        return result

    def _lof_to_band(self, lof: int) -> str:
        """Convert LOF (lowest operating frequency) to band name."""
        # MoCA 2.5 band definitions (approximate)
        if lof >= 1400:
            return "D-High"
        if lof >= 1225:
            return "D-Mid"
        if lof >= 1125:
            return "Extended-D"
        if lof >= 1000:
            return "D-Low"
        return f"Unknown ({lof} MHz)"

    async def get_status_page(self) -> dict:
        """Parse main status HTML page for additional info."""
        result: dict = {}
        try:
            html = await self._request(ENDPOINT_STATUS_HTML)
            if isinstance(html, str):
                # look for common status values in HTML
                # firmware version
                fw_match = re.search(
                    r"firmware[:\s]+([0-9.]+)",
                    html,
                    re.IGNORECASE,
                )
                if fw_match:
                    result["firmware_version"] = fw_match.group(1)

                # model name
                model_match = re.search(
                    r"model[:\s]+(MA\d+\w*|WF-\d+\w*|FCA\d+)",
                    html,
                    re.IGNORECASE,
                )
                if model_match:
                    result["model"] = model_match.group(1).upper()

                # channel count (sometimes shown)
                channel_match = re.search(
                    r"(\d+)\s*channels?",
                    html,
                    re.IGNORECASE,
                )
                if channel_match:
                    result["channel_count"] = int(channel_match.group(1))

                LOG.debug("Status page parsed values: %s", result)
        except (GoCoaxConnectionError, GoCoaxParseError) as err:
            LOG.debug("Failed to get status page: %s", err)
        return result

    async def get_status(self) -> AdapterStatus:
        """Get complete adapter status."""
        mac_address = await self.get_mac_address()
        local_info = await self.get_local_info()

        link_status = local_info.get("link_status", 0) == 1
        moca_ver_int = local_info.get("moca_version", 0)
        moca_version = self._parse_moca_version(moca_ver_int)
        node_id = local_info.get("node_id", 0)
        nc_node_id = local_info.get("nc_node_id", 0)
        is_nc = node_id == nc_node_id

        packets = await self.get_frame_info()
        peers = await self.get_node_info(local_node_id=node_id)
        phy_rates = await self.get_phy_rates()

        # fetch additional data for enhanced monitoring
        privacy_info = await self.get_privacy_info()
        config_info = await self.get_config_info()
        fmr_info = await self.get_fmr_info()
        status_page = await self.get_status_page()

        # fill in source mac for phy rates
        for rate in phy_rates:
            rate.source_mac = mac_address

        # build signal quality from FMR data
        signal_quality = SignalQuality(
            snr=fmr_info.get("snr"),
            tx_power=fmr_info.get("tx_power"),
            rx_power=fmr_info.get("rx_power"),
            bit_loading=fmr_info.get("bit_loading"),
        )

        # determine channel count (prefer config, fallback to status page)
        channel_count = config_info.get("channel_count") or status_page.get(
            "channel_count"
        )

        return AdapterStatus(
            mac_address=mac_address,
            ip_address=self._host,
            moca_version=moca_version,
            link_status=link_status,
            packets=packets,
            network_peers=peers,
            phy_rates=phy_rates,
            node_id=node_id,
            nc_node_id=nc_node_id,
            network_controller=is_nc,
            firmware_version=status_page.get("firmware_version"),
            model=status_page.get("model"),
            frequency_band=config_info.get("frequency_band"),
            lof=config_info.get("lof"),
            encryption_enabled=privacy_info.get("encryption_enabled"),
            signal_quality=signal_quality,
            channel_count=channel_count,
        )

    async def test_connection(self) -> bool:
        """Test connection to the adapter."""
        try:
            mac = await self.get_mac_address()
            return bool(mac)
        except GoCoaxAuthError:
            raise
        except GoCoaxConnectionError:
            raise
        except Exception as err:
            LOG.debug(f"Connection test failed: {err}")
            return False
