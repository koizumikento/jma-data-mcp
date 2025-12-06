"""MCP server for JMA data."""

import asyncio
import json
from datetime import datetime
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
from .weather import (
    fetch_amedas_data,
    fetch_forecast,
    fetch_historical_amedas_data,
    fetch_time_series_data,
    AREA_CODES,
    JST,
)


server = Server("jma-data-mcp")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        # Station tools
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
        # Weather data tools
        Tool(
            name="get_current_weather",
            description="Get current weather observation data from AMeDAS stations. Returns temperature, humidity, pressure, wind, precipitation, etc.",
            inputSchema={
                "type": "object",
                "properties": {
                    "station_code": {
                        "type": "string",
                        "description": "Station code (e.g., '44132' for Tokyo). If not specified, returns data for all stations."
                    }
                }
            }
        ),
        Tool(
            name="get_weather_by_location",
            description="Get current weather from the nearest AMeDAS station to given coordinates",
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
                    }
                },
                "required": ["lat", "lon"]
            }
        ),
        Tool(
            name="get_forecast",
            description="Get weather forecast for a prefecture",
            inputSchema={
                "type": "object",
                "properties": {
                    "prefecture": {
                        "type": "string",
                        "description": "Prefecture name in English (e.g., 'tokyo', 'osaka', 'hokkaido_sapporo')",
                        "enum": list(AREA_CODES.keys())
                    }
                },
                "required": ["prefecture"]
            }
        ),
        Tool(
            name="list_prefectures",
            description="List all available prefecture codes for weather forecast",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        # Historical data tools
        Tool(
            name="get_historical_weather",
            description="Get historical weather data for a specific date and time. Data is available for approximately the past 1-2 weeks.",
            inputSchema={
                "type": "object",
                "properties": {
                    "station_code": {
                        "type": "string",
                        "description": "Station code (e.g., '44132' for Tokyo)"
                    },
                    "datetime": {
                        "type": "string",
                        "description": "Target datetime in ISO format (e.g., '2025-12-01T12:00:00') or 'YYYY-MM-DD HH:MM' format. Time is in JST."
                    }
                },
                "required": ["station_code", "datetime"]
            }
        ),
        Tool(
            name="get_weather_time_series",
            description="Get time series weather data for a station. Useful for analyzing weather trends over hours or days.",
            inputSchema={
                "type": "object",
                "properties": {
                    "station_code": {
                        "type": "string",
                        "description": "Station code (e.g., '44132' for Tokyo)"
                    },
                    "hours": {
                        "type": "integer",
                        "description": "Number of hours to fetch (default: 24, max: 168 for ~1 week)",
                        "default": 24
                    },
                    "interval_minutes": {
                        "type": "integer",
                        "description": "Interval between data points in minutes (10, 30, or 60)",
                        "default": 60,
                        "enum": [10, 30, 60]
                    }
                },
                "required": ["station_code"]
            }
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""
    result = ""

    try:
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

        elif name == "get_current_weather":
            station_code = arguments.get("station_code")
            weather_data = await fetch_amedas_data(station_code)

            if station_code:
                # Single station - include station info
                station_info = get_station(station_code)
                if station_info and station_code in weather_data["stations"]:
                    weather_data["station_info"] = station_info
                    weather_data["weather"] = weather_data["stations"][station_code]
                    del weather_data["stations"]

            result = json.dumps(weather_data, ensure_ascii=False, indent=2)

        elif name == "get_weather_by_location":
            lat = arguments["lat"]
            lon = arguments["lon"]

            # Find nearest station
            nearby = search_stations_by_location(lat, lon, radius_km=100)
            if not nearby:
                result = json.dumps({
                    "error": "No stations found within 100km of the specified location"
                }, ensure_ascii=False, indent=2)
            else:
                nearest = nearby[0]
                station_code = nearest["code"]

                # Get weather data
                weather_data = await fetch_amedas_data(station_code)

                response = {
                    "observation_time": weather_data["observation_time"],
                    "observation_time_jst": weather_data["observation_time_jst"],
                    "station": nearest,
                    "weather": weather_data["stations"].get(station_code, {})
                }
                result = json.dumps(response, ensure_ascii=False, indent=2)

        elif name == "get_forecast":
            prefecture = arguments["prefecture"]
            area_code = AREA_CODES.get(prefecture)
            if not area_code:
                result = json.dumps({
                    "error": f"Unknown prefecture: {prefecture}",
                    "available": list(AREA_CODES.keys())
                }, ensure_ascii=False, indent=2)
            else:
                forecast_data = await fetch_forecast(area_code)
                result = json.dumps({
                    "prefecture": prefecture,
                    "area_code": area_code,
                    "forecast": forecast_data
                }, ensure_ascii=False, indent=2)

        elif name == "list_prefectures":
            result = json.dumps({
                "prefectures": AREA_CODES
            }, ensure_ascii=False, indent=2)

        elif name == "get_historical_weather":
            station_code = arguments["station_code"]
            datetime_str = arguments["datetime"]

            # Parse datetime string
            try:
                # Try ISO format first
                if "T" in datetime_str:
                    target_time = datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
                else:
                    # Try common formats
                    for fmt in ["%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M"]:
                        try:
                            target_time = datetime.strptime(datetime_str, fmt)
                            break
                        except ValueError:
                            continue
                    else:
                        raise ValueError(f"Could not parse datetime: {datetime_str}")

                # Add JST timezone if naive
                if target_time.tzinfo is None:
                    target_time = target_time.replace(tzinfo=JST)

            except Exception as e:
                result = json.dumps({
                    "error": f"Invalid datetime format: {e}",
                    "hint": "Use ISO format (e.g., '2025-12-01T12:00:00') or 'YYYY-MM-DD HH:MM'"
                }, ensure_ascii=False, indent=2)
            else:
                historical_data = await fetch_historical_amedas_data(station_code, target_time)

                # Add station info
                station_info = get_station(station_code)
                if station_info:
                    historical_data["station_info"] = station_info

                result = json.dumps(historical_data, ensure_ascii=False, indent=2)

        elif name == "get_weather_time_series":
            station_code = arguments["station_code"]
            hours = arguments.get("hours", 24)
            interval_minutes = arguments.get("interval_minutes", 60)

            time_series_data = await fetch_time_series_data(
                station_code,
                hours=hours,
                interval_minutes=interval_minutes
            )

            # Add station info
            station_info = get_station(station_code)
            if station_info:
                time_series_data["station_info"] = station_info

            result = json.dumps(time_series_data, ensure_ascii=False, indent=2)

        else:
            result = f"Unknown tool: {name}"

    except Exception as e:
        result = json.dumps({
            "error": str(e),
            "tool": name
        }, ensure_ascii=False, indent=2)

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
