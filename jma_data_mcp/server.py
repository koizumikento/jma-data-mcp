"""MCP server for JMA data."""

import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .stations import (
    get_station,
    search_stations_by_name,
    search_stations_by_location,
    get_stations_by_type,
    get_all_stations,
)


server = Server("jma-data-mcp")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="get_station",
            description="Get AMeDAS station information by station code",
            inputSchema={
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Station code (e.g., '44132' for Tokyo)"
                    }
                },
                "required": ["code"]
            }
        ),
        Tool(
            name="search_stations_by_name",
            description="Search AMeDAS stations by name (Japanese, Kana, or English)",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Station name to search"
                    }
                },
                "required": ["name"]
            }
        ),
        Tool(
            name="search_stations_by_location",
            description="Search AMeDAS stations within a radius from given coordinates",
            inputSchema={
                "type": "object",
                "properties": {
                    "lat": {
                        "type": "number",
                        "description": "Latitude in decimal degrees"
                    },
                    "lon": {
                        "type": "number",
                        "description": "Longitude in decimal degrees"
                    },
                    "radius_km": {
                        "type": "number",
                        "description": "Search radius in kilometers (default: 50)",
                        "default": 50
                    }
                },
                "required": ["lat", "lon"]
            }
        ),
        Tool(
            name="get_stations_by_type",
            description="Get all AMeDAS stations of a specific type",
            inputSchema={
                "type": "object",
                "properties": {
                    "station_type": {
                        "type": "string",
                        "description": "Station type: A (Staffed), B (Special Regional), C (AMeDAS), D (Rain Gauge), E (Snow Depth), F (Regional Rain)",
                        "enum": ["A", "B", "C", "D", "E", "F"]
                    }
                },
                "required": ["station_type"]
            }
        ),
        Tool(
            name="list_all_stations",
            description="List all AMeDAS stations (1286 stations)",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of stations to return (default: 100)",
                        "default": 100
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Number of stations to skip (default: 0)",
                        "default": 0
                    }
                }
            }
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""
    import json

    if name == "get_station":
        code = arguments["code"]
        station = get_station(code)
        if station:
            result = json.dumps(station, ensure_ascii=False, indent=2)
        else:
            result = f"Station with code '{code}' not found."

    elif name == "search_stations_by_name":
        search_name = arguments["name"]
        stations = search_stations_by_name(search_name)
        result = json.dumps({
            "count": len(stations),
            "stations": stations
        }, ensure_ascii=False, indent=2)

    elif name == "search_stations_by_location":
        lat = arguments["lat"]
        lon = arguments["lon"]
        radius_km = arguments.get("radius_km", 50.0)
        stations = search_stations_by_location(lat, lon, radius_km)
        result = json.dumps({
            "count": len(stations),
            "search_center": {"lat": lat, "lon": lon},
            "radius_km": radius_km,
            "stations": stations
        }, ensure_ascii=False, indent=2)

    elif name == "get_stations_by_type":
        station_type = arguments["station_type"]
        stations = get_stations_by_type(station_type)
        result = json.dumps({
            "count": len(stations),
            "type": station_type,
            "stations": stations
        }, ensure_ascii=False, indent=2)

    elif name == "list_all_stations":
        limit = arguments.get("limit", 100)
        offset = arguments.get("offset", 0)
        all_stations = get_all_stations()
        paginated = all_stations[offset:offset + limit]
        result = json.dumps({
            "total": len(all_stations),
            "offset": offset,
            "limit": limit,
            "count": len(paginated),
            "stations": paginated
        }, ensure_ascii=False, indent=2)

    else:
        result = f"Unknown tool: {name}"

    return [TextContent(type="text", text=result)]


def main():
    """Run the MCP server."""
    asyncio.run(run_server())


async def run_server():
    """Run the MCP server with stdio transport."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    main()
