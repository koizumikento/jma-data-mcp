"""Tests for CLI and entrypoint behavior."""

from __future__ import annotations

import json

from jma_data_mcp import cli, entrypoint


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
