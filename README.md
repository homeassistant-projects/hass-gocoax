11;rgb:2222/2222/2222># goCoax MoCA for Home Assistant (COMING SOON)

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

| Manufacturer | Model   | MoCA Speed | Ethernet Port | Supported |
|--------------|---------|:----------:|:-------------:|:---------:|
| goCoax       | WF-803M | 2.5        | 1.0 GbE       | YES       |
| goCoax       | MA2500C | 2.5        | 2.5 GbE       | YES       |
| goCoax       | MA2500D | 2.5        | 2.5 GbE       | YES       |
| Frontier     | FCA252  | 2.5        | 1.0 GbE       | YES       |
| Frontier     | WF-803T / FCA251 | 2.5        | 1.0 GbE       | YES       |


## Installation

Make sure [Home Assistant Community Store (HACS)](https://github.com/custom-components/hacs) is installed. This integration is part of the default HACS store (though can also be added manually using repository: `rsnodgrass/hass-gocoax`)

### Configuration

The goCoax MoCA unit IP address must be accessible from the Home Assistant host. Either set a static IP
on the goCoax admin panel or using static DHCP assignment.

```yaml
sensor:
  - platform: gocoax
    username: admin
    password: gocoax
    host: 192.168.1.12
```

### Example Lovelace UI


## Contributions Wanted

* config_flow for adding host IPs + username/password

## See Also

* [Home Assistant LUNOS support discussion](https://community.home-assistant.io/t/gocoax-moca-sensor/xxxx)
* [Official goCoax Support Forum](https://www.gocoax.com/forum)
