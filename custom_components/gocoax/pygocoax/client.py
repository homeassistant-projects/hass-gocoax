"""Async goCoax monitoring client with an explicit read-operation allowlist."""

from __future__ import annotations

import asyncio
import base64
import json
from urllib.parse import urlsplit

import aiohttp

from .exceptions import (
    GoCoaxAuthError,
    GoCoaxConnectionError,
    GoCoaxParseError,
    GoCoaxTimeoutError,
)
from .models import AdapterStatus
from .protocol import decode_status, local_nodes, mac_address, word, words

DEFAULT_TIMEOUT = 15
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
READ_OPERATIONS = {
    "local": ("/ms/0/0x15", "empty"),
    "mac": ("/ms/1/0x103/GET", "node"),
    "node": ("/ms/0/0x16", "node"),
    "frames": ("/ms/0/0x14", "zero"),
    "moca25": ("/ms/0/0x7f", "empty"),
    "frequency": ("/ms/0/0x1003/GET", "empty"),
    "phy": ("/ms/0/0x1D", "phy"),
    "band": ("/ms/0/0x1009/GET", "empty"),
    "privacy": ("/ms/0/0x1059/GET", "empty"),
    "enhanced_privacy": ("/ms/0/0x130D/GET", "empty"),
}
READ_PAGES = frozenset(
    {"/devStatus.html", "/phyRates.html", "/index.html", "/security.html"}
)


class _HTTPStatusError(GoCoaxConnectionError):
    def __init__(self, status: int):
        self.status = status
        super().__init__(f"Adapter returned HTTP {status}")


def validate_operation(operation: str, data: list[int]) -> str:
    if (
        operation not in READ_OPERATIONS
        or not isinstance(data, list)
        or any(type(v) is not int for v in data)
    ):
        raise ValueError("Only allowlisted status operations are supported")
    path, shape = READ_OPERATIONS[operation]
    if not (
        (shape == "empty" and not data)
        or (shape == "zero" and data == [0])
        or (shape == "node" and len(data) == 1 and 0 <= data[0] < 16)
        or (
            shape == "phy"
            and len(data) == 2
            and data[0] in [1 << n for n in range(16)]
            and data[1] in (1, 2)
        )
    ):
        raise ValueError("Invalid parameters for a status read")
    return path


class GoCoaxClient:
    """Read adapter state. No setters, arbitrary request API, or raw-response logs."""

    def __init__(
        self,
        host: str,
        username: str = "admin",
        password: str = "gocoax",
        session: aiohttp.ClientSession | None = None,
        timeout: int = DEFAULT_TIMEOUT,
    ):
        if (
            not isinstance(host, str)
            or not host
            or not isinstance(username, str)
            or not isinstance(password, str)
            or ":" in username
        ):
            raise ValueError("Invalid host or credentials")
        parsed = urlsplit(f"http://{host}")
        if (
            not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.path
            or parsed.query
            or parsed.fragment
            or any(c.isspace() for c in host)
        ):
            raise ValueError(
                "Host must be a hostname or IP address, optionally with a port"
            )
        try:
            _port = parsed.port
        except ValueError:
            raise ValueError("Invalid host port") from None
        self._base_url = f"http://{host}"
        self._host = host
        self._authorization = "Basic " + base64.b64encode(
            f"{username}:{password}".encode()
        ).decode("ascii")
        self._session = session
        self._owns_session = session is None
        self._timeout = timeout
        self._cookies: dict[str, str] = {}
        self._csrf: str | None = None
        self._lock = asyncio.Lock()

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None:
            self._session = aiohttp.ClientSession(
                cookie_jar=aiohttp.DummyCookieJar(), trust_env=False
            )
            self._owns_session = True
        if self._session.closed:
            raise GoCoaxConnectionError("HTTP session is closed")
        return self._session

    async def close(self) -> None:
        if self._owns_session and self._session:
            await self._session.close()
            self._session = None
        self._cookies.clear()
        self._csrf = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()

    async def _exchange(
        self,
        method: str,
        path: str,
        data: list[int] | None = None,
        referer: str = "/devStatus.html",
    ):
        if method == "GET":
            if path not in READ_PAGES or data is not None:
                raise ValueError("Only fixed status pages can be fetched")
        elif method == "POST":
            operation = next(
                (key for key, spec in READ_OPERATIONS.items() if spec[0] == path), ""
            )
            validate_operation(operation, data)
        else:
            raise ValueError("Unsupported monitoring method")
        if referer not in READ_PAGES:
            raise ValueError("Invalid status referer")
        headers = {
            "Authorization": self._authorization,
            "Accept": "text/html, */*",
            "Origin": self._base_url,
            "Referer": self._base_url + referer,
        }
        if self._cookies:
            headers["Cookie"] = "; ".join(
                f"{key}={value}" for key, value in self._cookies.items()
            )
        if self._csrf:
            headers["X-CSRF-TOKEN"] = self._csrf
        payload = None
        if data is not None:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
            payload = json.dumps({"data": data}, separators=(",", ":"))
        session = await self._get_session()
        try:
            async with asyncio.timeout(self._timeout):
                async with session.request(
                    method,
                    self._base_url + path,
                    headers=headers,
                    data=payload,
                    allow_redirects=False,
                ) as response:
                    if response.status == 401:
                        raise GoCoaxAuthError(
                            "Adapter rejected the configured credentials"
                        )
                    if response.status != 200:
                        raise _HTTPStatusError(response.status)
                    for name, cookie in response.cookies.items():
                        self._cookies[name] = cookie.value
                        if name.lower() in ("csrf_token", "xsrf-token"):
                            self._csrf = cookie.value
                    chunks, size = [], 0
                    async for chunk in response.content.iter_chunked(65536):
                        size += len(chunk)
                        if size > MAX_RESPONSE_BYTES:
                            raise GoCoaxParseError(
                                "Adapter response exceeds size limit"
                            )
                        chunks.append(chunk)
                    text = b"".join(chunks).decode("utf-8")
                    if method == "GET":
                        return text
                    try:
                        decoded = json.loads(text)
                        values = decoded["data"]
                        words(values)
                    except (ValueError, TypeError, KeyError, RecursionError):
                        raise GoCoaxParseError("Invalid JSON status response") from None
                    return values
        except TimeoutError:
            raise GoCoaxTimeoutError("Adapter request timed out") from None
        except (aiohttp.ClientError, UnicodeError):
            raise GoCoaxConnectionError("Adapter transport failed") from None

    async def _initialize(self):
        self._cookies.clear()
        self._csrf = None
        await self._exchange("GET", "/devStatus.html")
        if not self._csrf:
            raise GoCoaxConnectionError(
                "Adapter did not provide the expected CSRF session cookie"
            )

    async def _read(self, operation: str, data: list[int] | None = None):
        values = [] if data is None else data
        path = validate_operation(operation, values)
        if not self._csrf:
            await self._initialize()
        referer = (
            "/phyRates.html" if operation in ("node", "phy") else "/devStatus.html"
        )
        if operation == "band":
            referer = "/index.html"
        elif operation in ("privacy", "enhanced_privacy"):
            referer = "/security.html"
        try:
            return await self._exchange("POST", path, values, referer)
        except _HTTPStatusError as error:
            if error.status not in (400, 403):
                raise
            await self._initialize()
            return await self._exchange("POST", path, values, referer)

    async def get_mac_address(self) -> str:
        async with self._lock:
            local = await self._read("local")
            node, _, _ = local_nodes(local)
            return mac_address(await self._read("mac", [node]))

    async def get_status(self) -> AdapterStatus:
        async with self._lock:
            responses = {"local": await self._read("local")}
            node, controller, active = local_nodes(responses["local"])
            responses["mac"] = await self._read("mac", [node])
            responses["frames"] = await self._read("frames", [0])
            optional_lengths = {
                "moca25": 4,
                "frequency": 1,
                "band": 1,
                "privacy": 1,
                "enhanced_privacy": 1,
            }
            for operation, minimum in optional_lengths.items():
                try:
                    values = await self._read(operation)
                    words(values, minimum)
                    responses[operation] = values
                except (GoCoaxConnectionError, GoCoaxParseError):
                    continue
            net, fmr = {}, {}
            for n in active:
                net[n] = await self._read("node", [n])
                words(net[n], 5)
            if controller in net:
                nc_version = word(net[controller][4]) & 255
                for n in active:
                    node_version = word(net[n][4]) & 255
                    payload_version = 1 if min(nc_version, node_version) < 0x20 else 2
                    try:
                        values = await self._read("phy", [1 << n, payload_version])
                        words(values, 34)
                        fmr[n] = values
                    except (GoCoaxConnectionError, GoCoaxParseError):
                        continue
            return decode_status(self._host, responses, net, fmr)

    async def test_connection(self) -> bool:
        return bool(await self.get_mac_address())
