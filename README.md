# goCoax MoCA for Home Assistant

![goCoax Logo](https://raw.githubusercontent.com/rsnodgrass/hass-gocoax/main/img/logo.png)

Sensors for monitoring [goCoax](https://gocoax.com/) MoCA adapters and the associated mesh networks.

![beta_badge](https://img.shields.io/badge/maturity-Beta-yellow.png)
![release_badge](https://img.shields.io/github/release/rsnodgrass/hass-gocoax.svg)
![release_date](https://img.shields.io/github/release-date/rsnodgrass/hass-gocoax.svg)
[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/custom-components/hacs)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

[![Buy Me A Coffee](https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg)](https://buymeacoffee.com/DYks67r)
[![Donate](https://img.shields.io/badge/Donate-PayPal-green.svg)](https://www.paypal.com/cgi-bin/webscr?cmd=_donations&business=WREP29UDAMB6G)

## Models Supported

| Manufacturer | Model   | MoCA Speed | Ethernet Port | Supported | Known Working Firmware |
|--------------|---------|:----------:|:-------------:|:---------:|:-------------:|
| goCoax       | MA2500D | 2.5        | 2.5 GbE       | YES       | 2.0.11 |
| goCoax       | MA2500C | 2.5        | 2.5 GbE       | YES       | 3.0.5 |
| goCoax       | WF-803M | 2.5        | 1.0 GbE       | YES       | 1.0.12 |
| Frontier     | FCA252  | 2.5        | 1.0 GbE       | YES       | |
| Frontier     | WF-803T / FCA251 | 2.5 | 1.0 GbE    | YES       | |

**NOTE: To ensure sensor data is properly read from the adapters, it is recommended that you update to the LATEST FIRMWARE offered by [goCoax Support](https://www.gocoax.com/support), or one of the firmwares listed in the above table. However, upgrading firmware MAY reset settings on the adapter.**

## Installation

Make sure [Home Assistant Community Store (HACS)](https://github.com/custom-components/hacs) is installed. This integration is part of the default HACS store (though can also be added manually using repository: `rsnodgrass/hass-gocoax`)

### Configuration

The goCoax MoCA unit IP address must be accessible from the Home Assistant host. Either set a static IP on the goCoax admin panel or use static DHCP assignment.

Add via the Home Assistant UI: **Settings > Devices & Services > Add Integration > goCoax**

- **Host**: IP address of your goCoax adapter
- **Username**: Admin username (default: `admin`)
- **Password**: Admin password (default: `gocoax`)

## Sensors

### Binary Sensors

| Sensor | Description |
|--------|-------------|
| Link Status | MoCA network connectivity (on = connected) |
| Network Controller | Whether this adapter is the MoCA Network Controller |
| Encryption Enabled | MoCA privacy/encryption status |

### Sensors

| Sensor | Description |
|--------|-------------|
| MoCA Version | Protocol version (2.0, 2.5) |
| MAC Address | Adapter's unique MAC address |
| IP Address | Adapter's IP address |
| Node ID | MoCA network node identifier |
| Network Peers | Count of other adapters on the MoCA network |
| TX Packets | Ethernet transmit packet count (with ok/bad/dropped attributes) |
| RX Packets | Ethernet receive packet count (with ok/bad/dropped attributes) |
| PHY TX Rate | Physical layer transmit rate to each peer (Mbps) |
| PHY RX Rate | Physical layer receive rate from each peer (Mbps) |
| Frequency Band | Operating frequency band (D-Low, D-High, Extended-D) |
| Lowest Operating Frequency | LOF in MHz |
| Channel Count | Number of bonded MoCA channels |

### Device Info

The following information is shown in the device details:

- Model name
- Firmware version
- Configuration URL (link to adapter web UI)

## Options

After initial setup, you can configure:

- **Update Interval**: How often to poll the adapter (10-300 seconds, default: 30)

## Future Enhancements

The following features are planned for future releases:

- **Device Tracker**: Track devices on the MoCA network by MAC address
- **Configuration Options**: Band selection, encryption toggle (pending API write support)
- **SNR/Power Level Sensors**: Signal-to-noise ratio and power levels (pending endpoint discovery)

## See Also

- [Official goCoax Support Forum](https://www.gocoax.com/forum)
- [goCoax Product Page](https://www.gocoax.com/products)

## Contributing

Contributions are welcome! If you have a goCoax adapter and want to help improve the integration:

1. Enable debug logging to capture raw API responses
2. Share endpoint data (with MAC addresses redacted) to help improve parsing
3. Report issues or submit pull requests on GitHub

```yaml
logger:
  logs:
    custom_components.gocoax: debug
```
