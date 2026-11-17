import asyncio
import copy
import struct

import aiohttp
import pytest
from pygocoax.client import GoCoaxClient, validate_operation
from pygocoax.exceptions import GoCoaxAuthError, GoCoaxConnectionError, GoCoaxParseError
from pygocoax.protocol import decode_status, local_nodes, packet_stats, phy_matrix, word

from .conftest import load_fixture


@pytest.mark.parametrize(
    "label,node,peer,tx,rx",
    [
        ("adapter-a", 0, 1, 3485, 3468),
        ("adapter-b", 1, 0, 3462, 3473),
    ],
)
def test_captured_status_decoding(label, node, peer, tx, rx):
    fixture = load_fixture(label)
    result = decode_status("fixture", **fixture)
    assert result.node_id == node and result.nc_node_id == 0
    assert result.network_controller is (node == 0)
    assert result.peer_count == 1 and result.network_peers[0].node_id == peer
    assert (result.phy_rates[0].tx_rate, result.phy_rates[0].rx_rate) == (tx, rx)
    assert result.channel_count == 5
    assert result.packets.tx.ok == 123456 and result.packets.rx.ok == 234567
    assert result.firmware_version is None  # SDK is never mislabeled as image firmware.
    assert result.signal_quality.snr is None and result.frequency_band is None


def test_sparse_mask_preserves_packed_phy_slots():
    fixture = load_fixture()
    net = {0: fixture["net"][0], 4: fixture["net"][1]}
    raw = b"\x00" * 40 + b"".join(
        struct.pack(">BBHH", 10, 0, 20000 + slot * 100, 0) for slot in range(16)
    )
    values = [
        f"0x{int.from_bytes(raw[i : i + 4], 'big'):08x}" for i in range(0, len(raw), 4)
    ]
    matrix = phy_matrix(net, {0: values}, 0)
    assert matrix[0, 4] == (3900 * 20400 // ((512 + 40) * 46), 0)


def test_full_unsigned_counter_and_malformed_words():
    data = ["0x00000000"] * 108
    data[12:14] = ["0x80000000", "0x00000001"]
    assert packet_stats(data).tx.ok == (1 << 63) + 1
    for value in (None, "garbage", True, -1, 1 << 32, "0x123456789"):
        with pytest.raises(GoCoaxParseError):
            word(value)
    with pytest.raises(GoCoaxParseError):
        packet_stats(data[:50])


def test_down_link_zero_mask_and_invalid_active_mask():
    local = copy.deepcopy(load_fixture()["responses"]["local"])
    local[5], local[12] = "0x00000000", "0x00000000"
    assert local_nodes(local) == (0, 0, [])
    local[5] = "0x00000001"
    with pytest.raises(GoCoaxParseError):
        local_nodes(local)


def test_missing_optional_data_does_not_become_zero():
    fixture = load_fixture()
    fixture["responses"] = {
        key: fixture["responses"][key] for key in ("local", "mac", "frames")
    }
    fixture["fmr"] = {}
    result = decode_status("fixture", **fixture)
    assert result.channel_count is None
    assert result.phy_rates[0].tx_rate is None and result.phy_rates[0].rx_rate is None


@pytest.mark.parametrize(
    "band,privacy,enhanced,expected",
    [
        (1, 0, 3, False),
        (1, 1, 3, True),
        (1, 0, 7, True),
        (3, 1, 3, None),
        (3, 3, 3, True),
    ],
)
def test_privacy_uses_band_flags_and_enhanced_mode(band, privacy, enhanced, expected):
    fixture = load_fixture()
    fixture["responses"].update(
        band=[band], privacy=[privacy], enhanced_privacy=[enhanced]
    )
    status = decode_status("fixture", **fixture)
    assert status.encryption_enabled is expected
    assert status.frequency_band == ("Extended-D" if band == 1 else "Extended-D, D-Low")


@pytest.mark.parametrize(
    "operation,data",
    [
        ("reboot", []),
        ("/ms/0/0x15", []),
        ("local", [2]),
        ("node", [16]),
        ("node", [True]),
        ("phy", [3, 2]),
        ("phy", [1, 3]),
        ("frames", [1]),
    ],
)
def test_allowlist_denies_unknown_or_write_shaped_requests(operation, data):
    with pytest.raises(ValueError):
        validate_operation(operation, data)


@pytest.mark.parametrize(
    "host",
    [
        "http://192.0.2.1",
        "user:pass@192.0.2.1",
        "192.0.2.1/evil",
        "192.0.2.1?x=1",
        "192.0.2.1:invalid",
        "192.0.2.1\n",
    ],
)
def test_invalid_host_does_not_receive_credentials(host):
    with pytest.raises(ValueError):
        GoCoaxClient(host)


async def test_real_http_cookie_session_post_json_and_repeated_poll(adapter_server):
    host, state = adapter_server
    async with GoCoaxClient(host, "test-user", "test-password") as client:
        assert await client.get_mac_address() == "02:00:00:00:00:01"
        first, second = await asyncio.gather(client.get_status(), client.get_status())
        assert first.peer_count == second.peer_count == 1
        assert state["initializations"] == 1
        before = len(state["requests"])
        with pytest.raises(ValueError):
            await client._exchange("POST", "/reboot", [])
        assert len(state["requests"]) == before


async def test_expired_csrf_refreshes_once(adapter_server):
    host, state = adapter_server
    state["failures"] = [403]
    async with GoCoaxClient(host) as client:
        assert await client.get_mac_address()
    assert state["initializations"] == 2


async def test_repeated_bad_request_is_not_an_unbounded_retry(adapter_server):
    host, state = adapter_server
    state["failures"] = [400, 400]
    async with GoCoaxClient(host) as client:
        with pytest.raises(GoCoaxConnectionError):
            await client.get_mac_address()
    assert state["initializations"] == 2
    assert len(state["requests"]) == 4


async def test_authentication_failure_has_no_retry_or_body_leak(adapter_server):
    host, state = adapter_server
    state["failures"] = [401]
    async with GoCoaxClient(host) as client:
        with pytest.raises(GoCoaxAuthError) as error:
            await client.get_mac_address()
    assert "private" not in str(error.value)
    assert state["initializations"] == 1


async def test_redirect_is_not_followed(adapter_server):
    host, state = adapter_server
    state["redirect"] = True
    async with GoCoaxClient(host) as client:
        with pytest.raises(GoCoaxConnectionError):
            await client.get_mac_address()
    assert all(path != "/evil" for _, path in state["requests"])


async def test_invalid_json_and_oversized_body_are_safe(adapter_server, monkeypatch):
    host, state = adapter_server
    async with GoCoaxClient(host) as client:
        state["invalid_json"] = True
        with pytest.raises(GoCoaxParseError) as error:
            await client.get_mac_address()
        assert "private" not in str(error.value)
        state["invalid_json"], state["oversized"] = False, True
        monkeypatch.setattr("pygocoax.client.MAX_RESPONSE_BYTES", 1024)
        with pytest.raises(GoCoaxParseError):
            await client.get_mac_address()


async def test_borrowed_session_is_not_closed(adapter_server):
    host, _ = adapter_server
    async with aiohttp.ClientSession(cookie_jar=aiohttp.DummyCookieJar()) as session:
        client = GoCoaxClient(host, session=session)
        assert await client.get_mac_address()
        await client.close()
        assert not session.closed


async def test_missing_csrf_fails_before_any_api_request(adapter_server):
    host, state = adapter_server
    state["no_csrf"] = True
    async with GoCoaxClient(host) as client:
        with pytest.raises(GoCoaxConnectionError):
            await client.get_mac_address()
    assert state["requests"] == [("GET", "/devStatus.html")]


async def test_write_and_password_getters_never_reach_transport(adapter_server):
    host, state = adapter_server
    async with GoCoaxClient(host) as client:
        for path in (
            "/ms/0/0x1059/PUT",
            "/ms/1/0x20e/GET",
            "/ms/0/0x1049/GET",
            "/ms/0/0x1400/GET",
            "/ms/0/0x17",
        ):
            with pytest.raises(ValueError):
                await client._exchange("POST", path, [])
    assert not state["requests"]
