"""Offline contract checks: SDK client -> Worker -> real ASGI -> mocked JMA."""

import asyncio
import json
import os
import secrets
import shutil
import socket
from datetime import datetime
from pathlib import Path

import httpx
import pytest
import uvicorn
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport
from mcp_types import DiscoverResult

from jma_data_mcp import server, sites_backend, weather

ROOT = Path(__file__).resolve().parents[1]
JMA_NETWORK_TOOLS = {
    "get_current_weather", "get_weather_by_location", "get_forecast",
    "get_historical_weather", "get_weather_time_series",
}


def test_backend_requires_runtime_secret(monkeypatch):
    for token in ["", "short", "x" * 32 + "\n", "x" * 32 + "\x01", "あ" * 32]:
        monkeypatch.setenv("JMA_BACKEND_TOKEN", token)
        with pytest.raises(ValueError, match="JMA_BACKEND_TOKEN"):
            sites_backend.create_app()


async def test_backend_service_authentication(monkeypatch):
    token = secrets.token_urlsafe(32)
    monkeypatch.setenv("JMA_BACKEND_TOKEN", token)
    app = sites_backend.create_app()
    async with app.lifespan(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as client:
            for headers in [{}, {"Authorization": "Bearer wrong"}, {"oai-authenticated-user-id": "forged"}]:
                assert (await client.post("/mcp", headers=headers, json={})).status_code == 401
            headers = {"Authorization": f"Bearer {token}", "Origin": "http://test"}
            assert (await client.post("/mcp", headers=headers, json={})).status_code == 403
            response = await client.post("/mcp", headers={"Authorization": f"Bearer {token}"}, json={})
            assert response.status_code != 401


@pytest.mark.parametrize("mode", ["auto", "legacy"])
async def test_worker_backend_contract(monkeypatch, mode):
    assert shutil.which("node"), "Node 22+ is required for the Sites contract test"
    token = secrets.token_urlsafe(32)
    monkeypatch.setenv("JMA_BACKEND_TOKEN", token)
    raw_weather = json.loads((ROOT / "tests/fixtures/sites-weather.json").read_text())
    fixed_time = datetime(2026, 10, 10, 12, 20, tzinfo=weather.JST)
    monkeypatch.setattr(weather, "get_latest_data_time", lambda: fixed_time)
    fetched_urls = []
    retention_enabled = True

    def upstream(request):
        fetched_urls.append(str(request.url))
        assert request.url.host == "www.jma.go.jp"
        assert "authorization" not in request.headers
        if "/forecast/" in request.url.path:
            return httpx.Response(200, json=[{"publishingOffice": "気象庁", "reportDatetime": fixed_time.isoformat(), "timeSeries": []}])
        if retention_enabled and "20261010100000" in request.url.path:
            return httpx.Response(404, json={})
        if retention_enabled and "20261010090000" in request.url.path:
            return httpx.Response(503, json={})
        return httpx.Response(200, json=raw_weather)

    client_factory = httpx.AsyncClient
    monkeypatch.setattr(weather.httpx, "AsyncClient", lambda: client_factory(transport=httpx.MockTransport(upstream)))
    app = sites_backend.create_app()
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    backend_port = listener.getsockname()[1]
    http_server = uvicorn.Server(uvicorn.Config(app, log_level="critical", access_log=False))
    http_task = asyncio.create_task(http_server.serve(sockets=[listener]))
    process = None
    try:
        async def wait_started():
            while not http_server.started:
                if http_task.done():
                    await http_task
                    raise AssertionError("Backend exited before startup")
                await asyncio.sleep(0.01)

        await asyncio.wait_for(wait_started(), 10)
        process = await asyncio.create_subprocess_exec(
            "node", str(ROOT / "sites/tests/serve-worker.mjs"), str(backend_port),
            stdout=asyncio.subprocess.PIPE, env={**os.environ, "JMA_BACKEND_TOKEN": token},
        )
        port_line = await asyncio.wait_for(process.stdout.readline(), 10)
        worker_url = f"http://127.0.0.1:{int(port_line)}/mcp"
        transport = StreamableHttpTransport(worker_url, headers={"oai-authenticated-user-id": "fixture-owner"})
        cases = [
            ("get_station_info", {"code": "44132"}),
            ("get_station_info", {"code": "unknown"}),
            ("search_stations", {"name": "Tokyo"}),
            ("search_stations", {"name": "トウキョウ"}),
            ("search_nearby_stations", {"lat": 35.68, "lon": 139.75, "radius_km": 50}),
            ("get_stations_of_type", {"station_type": "A"}),
            ("get_stations_of_type", {"station_type": "invalid"}),
            ("list_stations", {"limit": 10, "offset": 100}),
            ("list_stations", {"limit": 100, "offset": 1280}),
            ("get_current_weather", {"station_code": "44132"}),
            ("get_current_weather", {}),
            ("get_weather_by_location", {"lat": 35.68, "lon": 139.75}),
            ("get_weather_by_location", {"lat": 0, "lon": 0}),
            ("get_forecast", {"prefecture": "tokyo"}),
            ("get_forecast", {"prefecture": "unknown"}),
            ("list_prefectures", {}),
            ("get_historical_weather", {"station_code": "44132", "target_datetime": "2026-10-10 12:29"}),
            ("get_historical_weather", {"station_code": "44132", "target_datetime": "2026-10-10T12:29:00+09:00"}),
            ("get_historical_weather", {"station_code": "unknown", "target_datetime": "2026/10/10 12:29"}),
            ("get_historical_weather", {"station_code": "44132", "target_datetime": "invalid"}),
            ("get_weather_time_series", {"station_code": "44132", "hours": 3, "interval_minutes": 60}),
            ("get_weather_time_series", {"station_code": "44132", "hours": 2, "interval_minutes": 30}),
            ("get_weather_time_series", {"station_code": "44132", "hours": 2, "interval_minutes": 10}),
            ("get_weather_time_series", {"station_code": "44132", "hours": 168, "interval_minutes": 10}),
            ("get_weather_time_series", {"station_code": "44132", "interval_minutes": 15}),
            ("get_station_info", {}),
            ("get_station_info", {"code": {"unexpected": "object"}}),
            ("get_historical_weather", {"station_code": "44132", "target_datetime": "2026-10-10 09:00"}),
        ]
        async with Client(server.mcp, mode=mode) as local, Client(transport, mode=mode, timeout=30) as remote:
            if mode == "auto":
                assert remote.protocol_version == "2026-07-28"
            local_tools, remote_tools = await local.list_tools(), await remote.list_tools()
            assert len(remote_tools) == 11
            assert [t.model_dump() for t in remote_tools] == [t.model_dump() for t in local_tools]
            assert JMA_NETWORK_TOOLS <= {tool.name for tool in remote_tools}
            for tool in remote_tools:
                assert tool.annotations is not None
                assert tool.annotations.read_only_hint is True
                assert tool.annotations.destructive_hint is False
                assert tool.annotations.idempotent_hint is True
                assert tool.annotations.open_world_hint is (tool.name in JMA_NETWORK_TOOLS)
            for name, arguments in cases:
                retention_enabled = arguments.get("hours") != 168
                expected = await local.call_tool(name, arguments, raise_on_error=False)
                actual = await remote.call_tool(name, arguments, raise_on_error=False)
                assert actual.is_error == expected.is_error, name
                assert actual.structured_content == expected.structured_content, name
                assert actual.content == expected.content, name
                if arguments.get("hours") == 168:
                    assert actual.data["data_points"] == 1008
                    assert actual.data["requested_hours"] == 168
            current = await remote.call_tool("get_current_weather", {"station_code": "44132"})
            assert current.data["weather"]["temperature"] == {"value": 0.0, "unit": "℃"}
            assert current.data["weather"]["humidity"]["value"] is None
            assert current.data["observation_time"] == fixed_time.isoformat()
            assert current.data["station_info"]["name"]["ja"] == "東京"
        async with client_factory() as http_client:
            modern = {
                "jsonrpc": "2.0", "id": 999, "method": "tools/call",
                "params": {"name": "get_station_info", "arguments": {"code": "44132"}, "_meta": {
                    "io.modelcontextprotocol/protocolVersion": "2026-07-28",
                    "io.modelcontextprotocol/clientInfo": {"name": "fixture", "version": "1"},
                    "io.modelcontextprotocol/clientCapabilities": {},
                }},
            }
            headers = {
                "accept": "application/json, text/event-stream", "mcp-protocol-version": "2026-07-28",
                "mcp-method": "tools/list", "mcp-name": "get_station_info",
                "oai-authenticated-user-id": "fixture-owner",
            }
            anonymous_headers = {k: v for k, v in headers.items() if k not in {"oai-authenticated-user-id", "mcp-name"}}
            anonymous_headers["mcp-method"] = "server/discover"
            discovery = {"jsonrpc": "2.0", "id": 998, "method": "server/discover", "params": {"_meta": modern["params"]["_meta"]}}
            discovered = await http_client.post(worker_url, headers=anonymous_headers, json=discovery)
            assert discovered.status_code == 200
            wire_result = discovered.json()["result"]
            assert wire_result["supportedVersions"] == ["2026-07-28"]
            assert wire_result["resultType"] == "complete"
            assert wire_result["_meta"]["io.modelcontextprotocol/serverInfo"]["name"] == "jma-data-mcp"
            discovery_result = DiscoverResult.model_validate(discovered.json()["result"])
            assert "2026-07-28" in discovery_result.supported_versions
            assert discovery_result.capabilities.tools is not None
            list_headers = {
                "accept": "application/json, text/event-stream", "mcp-method": "tools/list",
                "mcp-protocol-version": "2026-07-28" if mode == "auto" else "2025-11-25",
            }
            list_params = {"_meta": modern["params"]["_meta"]} if mode == "auto" else {}
            listed = await http_client.post(worker_url, headers=list_headers, json={
                "jsonrpc": "2.0", "id": 997, "method": "tools/list", "params": list_params,
            })
            assert listed.status_code == 200
            listed_result = listed.json()["result"]
            if mode == "auto":
                assert listed_result["resultType"] == "complete"
            assert len(listed_result["tools"]) == 11
            for tool in listed_result["tools"]:
                assert tool["annotations"] == {
                    "readOnlyHint": True, "destructiveHint": False, "idempotentHint": True,
                    "openWorldHint": tool["name"] in JMA_NETWORK_TOOLS,
                }
            call_headers = {**headers, "mcp-method": "tools/call"}
            called = await http_client.post(worker_url, headers=call_headers, json=modern)
            assert called.status_code == 200
            assert called.json()["result"]["resultType"] == "complete"
            assert called.json()["result"]["structuredContent"]["code"] == "44132"
            anonymous_headers.update({"mcp-method": "tools/call", "mcp-name": "get_station_info"})
            denied = await http_client.post(worker_url, headers=anonymous_headers, json=modern)
            assert denied.status_code == 401
            mismatch = await http_client.post(worker_url, headers=headers, json=modern)
            assert mismatch.status_code == 400
            assert mismatch.json()["error"]["code"] == -32020
            headers["mcp-method"] = "tools/call"
            headers["mcp-protocol-version"] = "2099-01-01"
            unsupported = await http_client.post(worker_url, headers=headers, json=modern)
            assert unsupported.status_code == 400
            assert "error" in unsupported.json()
        assert fetched_urls
    finally:
        if process is not None and process.returncode is None:
            process.terminate()
            await asyncio.wait_for(process.wait(), 10)
        http_server.should_exit = True
        try:
            await asyncio.wait_for(http_task, 10)
        finally:
            listener.close()
