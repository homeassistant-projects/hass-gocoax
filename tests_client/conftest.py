"""Client tests run without importing Home Assistant or using real credentials."""

import json
import sys
from pathlib import Path

import pytest
from aiohttp import web

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "custom_components" / "gocoax"))


def load_fixture(label="adapter-a"):
    data = json.loads(
        (ROOT / "tests_client" / "fixtures" / f"{label}.json").read_text()
    )
    data["net"] = {int(k): v for k, v in data["net"].items()}
    data["fmr"] = {int(k): v for k, v in data["fmr"].items()}
    return data


@pytest.fixture
async def adapter_server():
    from pygocoax.client import READ_OPERATIONS

    fixture = load_fixture()
    fixture["responses"].update(
        band=["0x00000001"], privacy=["0x00000000"], enhanced_privacy=["0x00000003"]
    )
    state = {
        "requests": [],
        "initializations": 0,
        "failures": [],
        "invalid_json": False,
        "redirect": False,
        "oversized": False,
        "no_csrf": False,
    }
    path_to_key = {path: key for key, (path, _shape) in READ_OPERATIONS.items()}

    async def handler(request):
        state["requests"].append((request.method, request.path))
        if request.path == "/devStatus.html":
            state["initializations"] += 1
            response = web.Response(text="<html>Status</html>")
            if not state["no_csrf"]:
                response.set_cookie("csrf_token", f"session-{state['initializations']}")
            return response
        assert request.method == "POST" and request.path in path_to_key
        assert request.headers["Content-Type"] == "application/x-www-form-urlencoded"
        assert request.headers["X-CSRF-TOKEN"] == request.cookies["csrf_token"]
        assert request.headers["Authorization"].startswith("Basic ")
        if state["failures"]:
            return web.Response(
                status=state["failures"].pop(0),
                text="private body must never enter exceptions",
            )
        if state["redirect"]:
            return web.Response(status=302, headers={"Location": "/evil"})
        if state["invalid_json"]:
            return web.Response(text="invalid private body")
        if state["oversized"]:
            return web.Response(body=b"x" * 10000)
        data = json.loads(await request.text())["data"]
        operation = path_to_key[request.path]
        if operation == "node":
            result = fixture["net"][data[0]]
        elif operation == "phy":
            result = fixture["fmr"][data[0].bit_length() - 1]
        else:
            result = fixture["responses"][operation]
        # Deliberately wrong content type: firmware JSON is decoded as data.
        return web.Response(
            text=json.dumps({"data": result}), content_type="text/plain"
        )

    app = web.Application()
    app.router.add_route("*", "/{tail:.*}", handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]
    try:
        yield f"127.0.0.1:{port}", state
    finally:
        await runner.cleanup()
