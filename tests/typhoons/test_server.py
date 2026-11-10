import sys

import pytest
from fastmcp import Client
from fastmcp.client.transports import StdioTransport

from jma_data_mcp.server import mcp
from jma_typhoon_mcp import create_server

NAMES = {"list_typhoons", "get_typhoon_track", "list_best_track_typhoons", "get_best_track"}


@pytest.mark.asyncio
async def test_typhoon_source_schema_is_preserved() -> None:
    expected = {tool.name: tool.model_dump() for tool in await create_server().list_tools()}
    actual = {tool.name: tool.model_dump() for tool in await mcp.list_tools() if tool.name in NAMES}
    assert expected == actual


@pytest.mark.asyncio
async def test_typhoon_command_stdio() -> None:
    transport = StdioTransport(command=sys.executable, args=["-m", "jma_typhoon_mcp"])
    async with Client(transport, mode="legacy", timeout=10) as client:
        tools = await client.list_tools()
    assert {tool.name for tool in tools} == NAMES
    assert all(tool.annotations and tool.annotations.read_only_hint for tool in tools)
