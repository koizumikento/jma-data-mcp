"""MCP server for JMA data using FastMCP."""

from datetime import datetime
from typing import Optional

from fastmcp import FastMCP

from .stations import (
    get_all_stations,
    get_station,
    get_stations_by_type,
    search_stations_by_location,
    search_stations_by_name,
)
from .weather import (
    AREA_CODES,
    JST,
    fetch_amedas_data,
    fetch_forecast,
    fetch_historical_amedas_data,
    fetch_time_series_data,
)

mcp = FastMCP("jma-data-mcp")


# Station tools
@mcp.tool()
async def get_station_info(code: str) -> dict:
    """Get AMeDAS station information by station code.

    Args:
        code: Station code (e.g., '44132' for Tokyo)

    Returns:
        Station information including name, location, and type
    """
    station = get_station(code)
    if station:
        return station
    return {"error": f"Station with code '{code}' not found."}


@mcp.tool()
async def search_stations(name: str) -> dict:
    """Search AMeDAS stations by name (Japanese, Kana, or English).

    Args:
        name: Station name to search

    Returns:
        List of matching stations
    """
    stations = search_stations_by_name(name)
    return {"count": len(stations), "stations": stations}


@mcp.tool()
async def search_nearby_stations(
    lat: float,
    lon: float,
    radius_km: float = 50.0,
) -> dict:
    """Search AMeDAS stations within a radius from given coordinates.

    Args:
        lat: Latitude in decimal degrees
        lon: Longitude in decimal degrees
        radius_km: Search radius in kilometers (default: 50)

    Returns:
        List of nearby stations sorted by distance
    """
    stations = search_stations_by_location(lat, lon, radius_km)
    return {
        "count": len(stations),
        "search_center": {"lat": lat, "lon": lon},
        "radius_km": radius_km,
        "stations": stations,
    }


@mcp.tool()
async def get_stations_of_type(
    station_type: str,
) -> dict:
    """Get all AMeDAS stations of a specific type.

    Args:
        station_type: Station type - A (Staffed), B (Special Regional),
                      C (AMeDAS), D (Rain Gauge), E (Snow Depth), F (Regional Rain)

    Returns:
        List of stations of the specified type
    """
    if station_type not in ["A", "B", "C", "D", "E", "F"]:
        return {"error": f"Invalid station type: {station_type}. Must be A, B, C, D, E, or F."}
    stations = get_stations_by_type(station_type)
    return {"count": len(stations), "type": station_type, "stations": stations}


@mcp.tool()
async def list_stations(
    limit: int = 100,
    offset: int = 0,
) -> dict:
    """List all AMeDAS stations (1286 stations) with pagination.

    Args:
        limit: Maximum number of stations to return (default: 100)
        offset: Number of stations to skip (default: 0)

    Returns:
        Paginated list of stations
    """
    all_stations = get_all_stations()
    paginated = all_stations[offset : offset + limit]
    return {
        "total": len(all_stations),
        "offset": offset,
        "limit": limit,
        "count": len(paginated),
        "stations": paginated,
    }


# Weather tools
@mcp.tool()
async def get_current_weather(
    station_code: Optional[str] = None,
) -> dict:
    """Get current weather observation data from AMeDAS stations.

    Args:
        station_code: Station code (e.g., '44132' for Tokyo).
                      If not specified, returns data for all stations.

    Returns:
        Weather data including temperature, humidity, pressure, wind, precipitation, etc.
    """
    weather_data = await fetch_amedas_data(station_code)

    if station_code:
        station_info = get_station(station_code)
        if station_info and station_code in weather_data["stations"]:
            weather_data["station_info"] = station_info
            weather_data["weather"] = weather_data["stations"][station_code]
            del weather_data["stations"]

    return weather_data


@mcp.tool()
async def get_weather_by_location(
    lat: float,
    lon: float,
) -> dict:
    """Get current weather from the nearest AMeDAS station to given coordinates.

    Args:
        lat: Latitude in decimal degrees
        lon: Longitude in decimal degrees

    Returns:
        Weather data from the nearest station
    """
    nearby = search_stations_by_location(lat, lon, radius_km=100)
    if not nearby:
        return {"error": "No stations found within 100km of the specified location"}

    nearest = nearby[0]
    station_code = nearest["code"]
    weather_data = await fetch_amedas_data(station_code)

    return {
        "observation_time": weather_data["observation_time"],
        "observation_time_jst": weather_data["observation_time_jst"],
        "station": nearest,
        "weather": weather_data["stations"].get(station_code, {}),
    }


@mcp.tool()
async def get_forecast(prefecture: str) -> dict:
    """Get weather forecast for a prefecture.

    Args:
        prefecture: Prefecture name in English (e.g., 'tokyo', 'osaka', 'hokkaido_sapporo')

    Returns:
        Weather forecast data
    """
    area_code = AREA_CODES.get(prefecture)
    if not area_code:
        return {
            "error": f"Unknown prefecture: {prefecture}",
            "available": list(AREA_CODES.keys()),
        }

    forecast_data = await fetch_forecast(area_code)
    return {
        "prefecture": prefecture,
        "area_code": area_code,
        "forecast": forecast_data,
    }


@mcp.tool()
async def list_prefectures() -> dict:
    """List all available prefecture codes for weather forecast.

    Returns:
        Dictionary of prefecture names and their codes
    """
    return {"prefectures": AREA_CODES}


# Historical data tools
@mcp.tool()
async def get_historical_weather(
    station_code: str,
    target_datetime: str,
) -> dict:
    """Get historical weather data for a specific date and time.

    Data is available for approximately the past 1-2 weeks.

    Args:
        station_code: Station code (e.g., '44132' for Tokyo)
        target_datetime: Target datetime in ISO format (e.g., '2025-12-01T12:00:00')
                         or 'YYYY-MM-DD HH:MM' format. Time is in JST.

    Returns:
        Weather data for the specified time
    """
    try:
        if "T" in target_datetime:
            target_time = datetime.fromisoformat(target_datetime.replace("Z", "+00:00"))
        else:
            for fmt in ["%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M"]:
                try:
                    target_time = datetime.strptime(target_datetime, fmt)
                    break
                except ValueError:
                    continue
            else:
                raise ValueError(f"Could not parse datetime: {target_datetime}")

        if target_time.tzinfo is None:
            target_time = target_time.replace(tzinfo=JST)

    except Exception as e:
        return {
            "error": f"Invalid datetime format: {e}",
            "hint": "Use ISO format (e.g., '2025-12-01T12:00:00') or 'YYYY-MM-DD HH:MM'",
        }

    historical_data = await fetch_historical_amedas_data(station_code, target_time)

    station_info = get_station(station_code)
    if station_info:
        historical_data["station_info"] = station_info

    return historical_data


@mcp.tool()
async def get_weather_time_series(
    station_code: str,
    hours: int = 24,
    interval_minutes: int = 60,
) -> dict:
    """Get time series weather data for a station.

    Useful for analyzing weather trends over hours or days.

    Args:
        station_code: Station code (e.g., '44132' for Tokyo)
        hours: Number of hours to fetch (default: 24, max: 168 for ~1 week)
        interval_minutes: Interval between data points in minutes (10, 30, or 60)

    Returns:
        Time series weather data
    """
    if interval_minutes not in [10, 30, 60]:
        return {"error": f"Invalid interval: {interval_minutes}. Must be 10, 30, or 60."}

    time_series_data = await fetch_time_series_data(
        station_code,
        hours=hours,
        interval_minutes=interval_minutes,
    )

    station_info = get_station(station_code)
    if station_info:
        time_series_data["station_info"] = station_info

    return time_series_data


def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
