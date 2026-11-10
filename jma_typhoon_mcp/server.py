from fastmcp import FastMCP

from .client import (
    get_best_track,
    get_typhoon_track,
    list_best_track_typhoons,
    list_typhoons,
)

READ_ONLY = {
    "readOnlyHint": True,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": True,
}


def create_server() -> FastMCP:
    mcp = FastMCP("jma-typhoon-mcp")
    mcp.tool(annotations=READ_ONLY)(list_typhoons)
    mcp.tool(annotations=READ_ONLY)(get_typhoon_track)
    mcp.tool(annotations=READ_ONLY)(list_best_track_typhoons)
    mcp.tool(annotations=READ_ONLY)(get_best_track)
    return mcp
