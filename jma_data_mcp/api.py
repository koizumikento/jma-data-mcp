"""Async functions for querying JMA data directly from Python."""

from .server import (
    get_climate_normals,
    get_current_weather,
    get_forecast,
    get_historical_weather,
    get_japan_climate_anomalies,
    get_station_info,
    get_stations_of_type,
    get_weather_by_location,
    get_weather_time_series,
    list_prefectures,
    list_stations,
    list_weather_warning_reports,
    search_nearby_stations,
    search_stations,
)

__all__ = [
    "get_climate_normals",
    "get_current_weather",
    "get_forecast",
    "get_historical_weather",
    "get_japan_climate_anomalies",
    "get_station_info",
    "get_stations_of_type",
    "get_weather_by_location",
    "get_weather_time_series",
    "list_prefectures",
    "list_stations",
    "list_weather_warning_reports",
    "search_nearby_stations",
    "search_stations",
]
