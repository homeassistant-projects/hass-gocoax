"""Constants for the goCoax MoCA integration."""

from typing import Final

DOMAIN: Final = "gocoax"

# configuration keys
CONF_HOST: Final = "host"
CONF_USERNAME: Final = "username"
CONF_PASSWORD: Final = "password"
CONF_SCAN_INTERVAL: Final = "scan_interval"

# defaults
DEFAULT_USERNAME: Final = "admin"
DEFAULT_PASSWORD: Final = "gocoax"
DEFAULT_SCAN_INTERVAL: Final = 30  # seconds
DEFAULT_TIMEOUT: Final = 15  # seconds
MIN_SCAN_INTERVAL: Final = 10
MAX_SCAN_INTERVAL: Final = 300

# manufacturers
MANUFACTURER_GOCOAX: Final = "goCoax"
MANUFACTURER_FRONTIER: Final = "Frontier"

# known models
MODELS: Final = {
    "MA2500D": {
        "manufacturer": MANUFACTURER_GOCOAX,
        "moca": "2.5",
        "ethernet": "2.5 GbE",
    },
    "MA2500C": {
        "manufacturer": MANUFACTURER_GOCOAX,
        "moca": "2.5",
        "ethernet": "2.5 GbE",
    },
    "WF-803M": {
        "manufacturer": MANUFACTURER_GOCOAX,
        "moca": "2.5",
        "ethernet": "1.0 GbE",
    },
    "FCA252": {
        "manufacturer": MANUFACTURER_FRONTIER,
        "moca": "2.5",
        "ethernet": "1.0 GbE",
    },
    "WF-803T": {
        "manufacturer": MANUFACTURER_FRONTIER,
        "moca": "2.5",
        "ethernet": "1.0 GbE",
    },
    "FCA251": {
        "manufacturer": MANUFACTURER_FRONTIER,
        "moca": "2.5",
        "ethernet": "1.0 GbE",
    },
}

# platforms
PLATFORMS: Final = ["sensor", "binary_sensor"]

# entity categories
ATTR_MAC_ADDRESS: Final = "mac_address"
ATTR_IP_ADDRESS: Final = "ip_address"
ATTR_MOCA_VERSION: Final = "moca_version"
ATTR_LINK_STATUS: Final = "link_status"
ATTR_FIRMWARE_VERSION: Final = "firmware_version"
ATTR_NODE_ID: Final = "node_id"
ATTR_NETWORK_CONTROLLER: Final = "network_controller"
ATTR_TX_OK: Final = "tx_ok"
ATTR_TX_BAD: Final = "tx_bad"
ATTR_TX_DROPPED: Final = "tx_dropped"
ATTR_RX_OK: Final = "rx_ok"
ATTR_RX_BAD: Final = "rx_bad"
ATTR_RX_DROPPED: Final = "rx_dropped"
ATTR_PEER_COUNT: Final = "peer_count"
ATTR_PHY_TX_RATE: Final = "phy_tx_rate"
ATTR_PHY_RX_RATE: Final = "phy_rx_rate"
