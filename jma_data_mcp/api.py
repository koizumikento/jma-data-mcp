"""Async functions for querying JMA data directly from Python."""

from .server import (
    get_current_weather,
    get_forecast,
    get_historical_weather,
    get_station_info,
    get_stations_of_type,
    get_weather_by_location,
    get_weather_time_series,
    list_prefectures,
    list_stations,
    search_nearby_stations,
    search_stations,
)

__all__ = [
    "get_current_weather",
    "get_forecast",
    "get_historical_weather",
    "get_station_info",
    "get_stations_of_type",
    "get_weather_by_location",
    "get_weather_time_series",
    "list_prefectures",
    "list_stations",
    "search_nearby_stations",
    "search_stations",
]
