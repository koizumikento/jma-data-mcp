import json
from unittest.mock import AsyncMock

import pytest

from jma_data_mcp import api, cli, server
from jma_typhoon_mcp import client


@pytest.mark.parametrize(
    "command, function, arguments",
    [
        ("list", "list_typhoons", {"year": 2001}),
        ("track", "get_typhoon_track", {"year": 2001, "number": 1}),
        ("best-track-list", "list_best_track_typhoons", {"year": 1951}),
        ("best-track", "get_best_track", {"year": 1951, "number": 1}),
        ("refresh", "refresh_cache", {"year": 2001}),
    ],
)
def test_main_cli_uses_typhoon_functions(monkeypatch, capsys, command, function, arguments):
    handler = AsyncMock(return_value={"fixture": "台風"})
    module = cli if function == "refresh_cache" else server
    monkeypatch.setattr(module, function, handler)
    argv = ["typhoon", command, "--year", str(arguments["year"])]
    if "number" in arguments:
        argv += ["--number", str(arguments["number"])]
    assert cli.main(argv) == 0
    assert json.loads(capsys.readouterr().out) == {"fixture": "台風"}
    handler.assert_awaited_once_with(**arguments)


def test_public_api_reuses_typhoon_client():
    for name in (
        "list_typhoons", "get_typhoon_track", "list_best_track_typhoons", "get_best_track",
    ):
        assert getattr(api, name) is getattr(client, name)
    assert api.refresh_typhoon_cache is client.refresh_cache
