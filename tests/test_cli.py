"""Tests for CLI and entrypoint behavior."""

from __future__ import annotations

import json
import sys

import httpx
import pytest
from fastmcp import Client
from fastmcp.client.transports import StdioTransport

from jma_data_mcp import cli, entrypoint, server, weather


def test_entrypoint_no_args_calls_server(monkeypatch):
    called = {"count": 0}

    def fake_server_main() -> None:
        called["count"] += 1

    monkeypatch.setattr(entrypoint.server, "main", fake_server_main)

    exit_code = entrypoint.main([])

    assert exit_code == 0
    assert called["count"] == 1


def test_entrypoint_serve_calls_server(monkeypatch):
    called = {"count": 0}

    def fake_server_main() -> None:
        called["count"] += 1

    monkeypatch.setattr(entrypoint.server, "main", fake_server_main)

    exit_code = entrypoint.main(["serve"])

    assert exit_code == 0
    assert called["count"] == 1


def test_station_get_outputs_json(capsys):
    exit_code = cli.main(["station", "get", "--code", "44132"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["name"]["ja"] == "東京"
    assert payload["name"]["en"] == "Tokyo"
    assert payload["type"] == "A"


def test_cli_invalid_args_returns_2_and_json_error(capsys):
    exit_code = cli.main(["station", "get"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 2
    assert "error" in payload


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["auto", "legacy"])
async def test_mcp_weather_validation_and_response(monkeypatch, mode):
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json={"44132": {"temp": [21.5, 0]}})
    )
    client_factory = httpx.AsyncClient
    monkeypatch.setattr(weather.httpx, "AsyncClient", lambda: client_factory(transport=transport))
    async with Client(server.mcp, mode=mode) as client:
        assert len(await client.list_tools()) == 11
        result = await client.call_tool("get_current_weather", {"station_code": "44132"})
        assert result.data["weather"]["temperature"] == {"value": 21.5, "unit": "℃"}
        assert result.data["station_info"]["name"]["ja"] == "東京"
        invalid = await client.call_tool("get_station_info", {}, raise_on_error=False)
        assert invalid.is_error


@pytest.mark.asyncio
async def test_cli_stdio_initialization():
    transport = StdioTransport(
        command=sys.executable,
        args=["-m", "jma_data_mcp", "serve"],
        env={"PYTHONUTF8": "1"},
    )
    async with Client(transport, mode="legacy", timeout=10) as client:
        assert len(await client.list_tools()) == 11
        result = await client.call_tool("get_station_info", {"code": "44132"})
        assert result.data["name"]["ja"] == "東京"
