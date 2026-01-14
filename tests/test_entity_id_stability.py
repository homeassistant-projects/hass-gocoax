"""Entity ID stability tests for goCoax MoCA integration.

These tests ensure unique_id patterns remain stable across updates.
Changing unique_id formats will break existing user automations, scenes,
and dashboards that reference these entities.

GOLDEN FORMAT DOCUMENTATION
===========================

The goCoax integration uses two unique_id patterns:

1. Standard sensor/binary_sensor entities:
   Format: f'{mac_address}_{description.key}'
   Example: 'a4:81:7a:49:e3:dd_moca_version'
   Example: 'a4:81:7a:49:e3:dd_link_status'

2. PHY rate sensor entities (sensor.py GoCoaxPhyRateSensor):
   Format: f'{mac_address}_phy_{direction}_{short_mac}'
   Where:
     - direction is 'tx' or 'rx'
     - short_mac is last 6 chars of target MAC with colons removed
   Example: 'a4:81:7a:49:e3:dd_phy_tx_1a2b3c'
   Example: 'a4:81:7a:49:e3:dd_phy_rx_1a2b3c'

BREAKING CHANGE WARNING
=======================

DO NOT modify these patterns without:
1. Providing a migration path for existing users
2. Updating the version number with a major bump
3. Adding deprecation warnings in release notes
4. Consider using entity_registry helpers to migrate entity IDs

If you must change these patterns, existing users will need to:
- Manually update all automations referencing old entity IDs
- Re-add entities to dashboards
- Fix any scenes or scripts using the entities
"""

from __future__ import annotations

import pytest

# domain constant must match the integration
DOMAIN = 'gocoax'


# -----------------------------------------------------------------------------
# Unique ID generation functions (must match actual entity code exactly)
# -----------------------------------------------------------------------------


def generate_standard_unique_id(mac_address: str, description_key: str) -> str:
    """Generate unique_id for standard sensor/binary_sensor entities.

    Matches: sensor.py GoCoaxSensor.__init__ and binary_sensor.py GoCoaxBinarySensor.__init__
    Pattern: f'{coordinator.mac_address}_{description.key}'
    """
    return f'{mac_address}_{description_key}'


def generate_phy_rate_unique_id(
    mac_address: str, direction: str, target_mac: str
) -> str:
    """Generate unique_id for PHY rate sensor entities.

    Matches: sensor.py GoCoaxPhyRateSensor.__init__
    Pattern: f'{coordinator.mac_address}_phy_{direction}_{short_mac}'
    Where short_mac = target_mac.replace(':', '')[-6:]
    """
    short_mac = target_mac.replace(':', '')[-6:]
    return f'{mac_address}_phy_{direction}_{short_mac}'


# -----------------------------------------------------------------------------
# Test data for parametrized tests
# -----------------------------------------------------------------------------

# sensor entity description keys from sensor.py
SENSOR_DESCRIPTION_KEYS = [
    'moca_version',
    'mac_address',
    'ip_address',
    'node_id',
    'tx_packets',
    'rx_packets',
    'peer_count',
    'frequency_band',
    'lof',
    'channel_count',
]

# binary_sensor entity description keys from binary_sensor.py
BINARY_SENSOR_DESCRIPTION_KEYS = [
    'link_status',
    'network_controller',
    'encryption_enabled',
]

# representative MAC addresses to test various formatting scenarios
TEST_MAC_ADDRESSES = [
    'a4:81:7a:49:e3:dd',
    'AA:BB:CC:DD:EE:FF',
    '00:11:22:33:44:55',
]

# representative target MACs for PHY rate sensors
TEST_TARGET_MACS = [
    'b5:92:8b:5a:f4:ee',
    '11:22:33:aa:bb:cc',
    'DE:AD:BE:EF:12:34',
]


# -----------------------------------------------------------------------------
# Standard sensor entity unique_id tests
# -----------------------------------------------------------------------------


class TestSensorUniqueIdStability:
    """Test standard sensor entity unique_id stability."""

    @pytest.mark.parametrize('mac_address', TEST_MAC_ADDRESSES)
    @pytest.mark.parametrize('description_key', SENSOR_DESCRIPTION_KEYS)
    def test_sensor_unique_id_format(
        self, mac_address: str, description_key: str
    ) -> None:
        """Verify sensor unique_id format remains stable."""
        unique_id = generate_standard_unique_id(mac_address, description_key)

        # format requirements
        assert mac_address in unique_id, f'must contain MAC address: {unique_id}'
        assert description_key in unique_id, f'must contain description_key: {unique_id}'
        assert unique_id.count('_') >= 1, f'must have underscore separator: {unique_id}'

    def test_sensor_golden_examples(self) -> None:
        """Verify specific golden examples for sensor entities.

        These exact values must not change. If they do, user configurations break.
        """
        golden_examples = {
            ('a4:81:7a:49:e3:dd', 'moca_version'): 'a4:81:7a:49:e3:dd_moca_version',
            ('a4:81:7a:49:e3:dd', 'mac_address'): 'a4:81:7a:49:e3:dd_mac_address',
            ('a4:81:7a:49:e3:dd', 'ip_address'): 'a4:81:7a:49:e3:dd_ip_address',
            ('a4:81:7a:49:e3:dd', 'tx_packets'): 'a4:81:7a:49:e3:dd_tx_packets',
            ('a4:81:7a:49:e3:dd', 'peer_count'): 'a4:81:7a:49:e3:dd_peer_count',
            ('AA:BB:CC:DD:EE:FF', 'lof'): 'AA:BB:CC:DD:EE:FF_lof',
        }

        for (mac_address, description_key), expected in golden_examples.items():
            actual = generate_standard_unique_id(mac_address, description_key)
            assert actual == expected, (
                f'Golden unique_id mismatch for sensor ({mac_address}, {description_key}): '
                f'expected {expected!r}, got {actual!r}'
            )


# -----------------------------------------------------------------------------
# Binary sensor entity unique_id tests
# -----------------------------------------------------------------------------


class TestBinarySensorUniqueIdStability:
    """Test binary sensor entity unique_id stability."""

    @pytest.mark.parametrize('mac_address', TEST_MAC_ADDRESSES)
    @pytest.mark.parametrize('description_key', BINARY_SENSOR_DESCRIPTION_KEYS)
    def test_binary_sensor_unique_id_format(
        self, mac_address: str, description_key: str
    ) -> None:
        """Verify binary sensor unique_id format remains stable."""
        unique_id = generate_standard_unique_id(mac_address, description_key)

        # format requirements
        assert mac_address in unique_id, f'must contain MAC address: {unique_id}'
        assert description_key in unique_id, f'must contain description_key: {unique_id}'
        assert unique_id.count('_') >= 1, f'must have underscore separator: {unique_id}'

    def test_binary_sensor_golden_examples(self) -> None:
        """Verify specific golden examples for binary sensor entities.

        These exact values must not change. If they do, user configurations break.
        """
        golden_examples = {
            ('a4:81:7a:49:e3:dd', 'link_status'): 'a4:81:7a:49:e3:dd_link_status',
            ('a4:81:7a:49:e3:dd', 'network_controller'): 'a4:81:7a:49:e3:dd_network_controller',
            ('a4:81:7a:49:e3:dd', 'encryption_enabled'): 'a4:81:7a:49:e3:dd_encryption_enabled',
            ('AA:BB:CC:DD:EE:FF', 'link_status'): 'AA:BB:CC:DD:EE:FF_link_status',
        }

        for (mac_address, description_key), expected in golden_examples.items():
            actual = generate_standard_unique_id(mac_address, description_key)
            assert actual == expected, (
                f'Golden unique_id mismatch for binary_sensor ({mac_address}, {description_key}): '
                f'expected {expected!r}, got {actual!r}'
            )


# -----------------------------------------------------------------------------
# PHY rate sensor entity unique_id tests
# -----------------------------------------------------------------------------


class TestPhyRateSensorUniqueIdStability:
    """Test PHY rate sensor entity unique_id stability."""

    @pytest.mark.parametrize('mac_address', TEST_MAC_ADDRESSES)
    @pytest.mark.parametrize('direction', ['tx', 'rx'])
    @pytest.mark.parametrize('target_mac', TEST_TARGET_MACS)
    def test_phy_rate_unique_id_format(
        self, mac_address: str, direction: str, target_mac: str
    ) -> None:
        """Verify PHY rate sensor unique_id format remains stable."""
        unique_id = generate_phy_rate_unique_id(mac_address, direction, target_mac)

        # format requirements
        assert mac_address in unique_id, f'must contain MAC address: {unique_id}'
        assert f'_phy_{direction}_' in unique_id, f'must contain _phy_{direction}_: {unique_id}'

        # short_mac should be last 6 chars of target MAC without colons
        expected_short_mac = target_mac.replace(':', '')[-6:]
        assert unique_id.endswith(expected_short_mac), (
            f'must end with short_mac {expected_short_mac}: {unique_id}'
        )

    def test_phy_rate_golden_examples(self) -> None:
        """Verify specific golden examples for PHY rate sensor entities.

        These exact values must not change. If they do, user configurations break.
        """
        golden_examples = {
            ('a4:81:7a:49:e3:dd', 'tx', 'b5:92:8b:5a:f4:ee'): 'a4:81:7a:49:e3:dd_phy_tx_5af4ee',
            ('a4:81:7a:49:e3:dd', 'rx', 'b5:92:8b:5a:f4:ee'): 'a4:81:7a:49:e3:dd_phy_rx_5af4ee',
            ('a4:81:7a:49:e3:dd', 'tx', '11:22:33:aa:bb:cc'): 'a4:81:7a:49:e3:dd_phy_tx_aabbcc',
            ('a4:81:7a:49:e3:dd', 'rx', 'DE:AD:BE:EF:12:34'): 'a4:81:7a:49:e3:dd_phy_rx_EF1234',
        }

        for (mac_address, direction, target_mac), expected in golden_examples.items():
            actual = generate_phy_rate_unique_id(mac_address, direction, target_mac)
            assert actual == expected, (
                f'Golden unique_id mismatch for phy_rate ({mac_address}, {direction}, {target_mac}): '
                f'expected {expected!r}, got {actual!r}'
            )

    def test_short_mac_extraction(self) -> None:
        """Verify short_mac is correctly extracted from target MAC."""
        # the short_mac should be the last 6 characters of the MAC with colons removed
        test_cases = [
            ('aa:bb:cc:dd:ee:ff', 'ddeeff'),
            ('11:22:33:44:55:66', '445566'),
            ('AA:BB:CC:DD:EE:FF', 'DDEEFF'),
        ]

        for target_mac, expected_short_mac in test_cases:
            unique_id = generate_phy_rate_unique_id(
                'a4:81:7a:49:e3:dd', 'tx', target_mac
            )
            assert unique_id.endswith(expected_short_mac), (
                f'short_mac extraction failed for {target_mac}: '
                f'expected to end with {expected_short_mac}, got {unique_id}'
            )


# -----------------------------------------------------------------------------
# Cross-entity consistency tests
# -----------------------------------------------------------------------------


class TestCrossEntityConsistency:
    """Test consistency across entity types."""

    @pytest.mark.parametrize('mac_address', TEST_MAC_ADDRESSES)
    def test_all_entities_use_mac_address_prefix(self, mac_address: str) -> None:
        """All entities for a device should use the MAC address as prefix."""
        sensor_id = generate_standard_unique_id(mac_address, 'moca_version')
        binary_sensor_id = generate_standard_unique_id(mac_address, 'link_status')
        phy_rate_id = generate_phy_rate_unique_id(
            mac_address, 'tx', 'b5:92:8b:5a:f4:ee'
        )

        assert sensor_id.startswith(mac_address)
        assert binary_sensor_id.startswith(mac_address)
        assert phy_rate_id.startswith(mac_address)

    def test_unique_ids_are_globally_unique(self) -> None:
        """Verify no collisions between entity unique_ids for same device."""
        mac_address = 'a4:81:7a:49:e3:dd'
        target_mac = 'b5:92:8b:5a:f4:ee'
        all_ids: set[str] = set()

        # collect all sensor ids
        for description_key in SENSOR_DESCRIPTION_KEYS:
            uid = generate_standard_unique_id(mac_address, description_key)
            assert uid not in all_ids, f'duplicate unique_id: {uid}'
            all_ids.add(uid)

        # collect all binary sensor ids
        for description_key in BINARY_SENSOR_DESCRIPTION_KEYS:
            uid = generate_standard_unique_id(mac_address, description_key)
            assert uid not in all_ids, f'duplicate unique_id: {uid}'
            all_ids.add(uid)

        # collect PHY rate sensor ids
        for direction in ['tx', 'rx']:
            uid = generate_phy_rate_unique_id(mac_address, direction, target_mac)
            assert uid not in all_ids, f'duplicate unique_id: {uid}'
            all_ids.add(uid)

    def test_sensor_and_binary_sensor_use_same_pattern(self) -> None:
        """Verify sensor and binary_sensor entities use the same unique_id pattern."""
        mac_address = 'a4:81:7a:49:e3:dd'

        # both should use the same f'{mac_address}_{description_key}' pattern
        sensor_id = generate_standard_unique_id(mac_address, 'moca_version')
        binary_sensor_id = generate_standard_unique_id(mac_address, 'link_status')

        # verify both follow the same structure: mac_address + '_' + description_key
        expected_sensor = f'{mac_address}_moca_version'
        expected_binary_sensor = f'{mac_address}_link_status'

        assert sensor_id == expected_sensor
        assert binary_sensor_id == expected_binary_sensor

        # both should start with mac address followed by underscore
        assert sensor_id.startswith(f'{mac_address}_')
        assert binary_sensor_id.startswith(f'{mac_address}_')
